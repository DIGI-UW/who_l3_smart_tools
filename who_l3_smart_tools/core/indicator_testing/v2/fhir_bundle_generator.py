from datetime import datetime, timedelta
import os
import json
import pandas as pd
import requests
import uuid
import copy
from who_l3_smart_tools.core.indicator_testing.v2.fhir_mapping_manager import (
    YamlMappingManager,
)
from who_l3_smart_tools.core.indicator_testing.v2.test_artifact_generator import (
    generate_test_artifacts,
)

from bs4 import BeautifulSoup


class FhirBundleGenerator:

    def __init__(
        self,
        phenotype_file,
        mapping_file,
        output_directory,
        ig_root_url="https://i-tech-uw.github.io/smart-hiv/",
    ):
        self.phenotype_file = phenotype_file
        self.mapping_manager = YamlMappingManager(mapping_file)
        self.output_directory = output_directory
        self.ig_root_url = ig_root_url

        # Read and pre-process the phenotype excel into indicator data:
        # - First row contains column names and second row contains indicator values.
        # - Patient phenotype data starts with headers in row 4 and data from row 5 onwards.
        raw_df = pd.read_excel(self.phenotype_file, header=None)
        self.indicator_df = raw_df.iloc[1:2]
        self.indicator_df.columns = raw_df.iloc[0]  # row 0 as header

        self.phenotype_df = raw_df.iloc[4:]
        self.phenotype_df.columns = raw_df.iloc[3]  # row 4 as header

        # Simple caching for IG requests:
        self.resource_cache = {}

    def get_fhir_resource(self, resource_url):
        """Retrieve a FHIR resource from IG, with caching."""
        if resource_url in self.resource_cache:
            return self.resource_cache[resource_url]
        try:
            response = requests.get(resource_url)
            response.raise_for_status()
            resource = response.json()
            resource.pop("text", None)
            self.resource_cache[resource_url] = resource
            return resource
        except requests.RequestException as e:
            raise ValueError(
                f"Could not retrieve FHIR resource from {resource_url}: {e}"
            )

    def get_patient_example(self, patient_profile_name):
        """Retrieve the default Patient example JSON from the IG."""
        url = f"{self.ig_root_url}/Patient-{patient_profile_name}Default.json"
        return self.get_fhir_resource(url)

    def get_feature_resources(self, resource_mapping):
        """Retrieve the profile and default example resource for a given feature mapping."""
        target_profile = resource_mapping.get("target_profile")
        if not target_profile:
            raise ValueError("Missing target_profile in mapping")
        # Query the StructureDefinition:
        target_profile_url = (
            f"{self.ig_root_url}/StructureDefinition-{target_profile}.json"
        )
        profile = self.get_fhir_resource(target_profile_url)
        resource_type = profile.get("type")
        # Query the default example:
        target_example_url = (
            f"{self.ig_root_url}/{resource_type}-{target_profile}Default.json"
        )
        example = self.get_fhir_resource(target_example_url)
        # Assign a new unique id to the example resource.
        example["id"] = str(uuid.uuid4())
        return profile, example

    def update_patient_resource(self, patient_json, row):
        """Update patient example using row data."""
        for key, value in row.iloc[0].items():
            if key == "Patient Phenotype ID":
                patient_json.setdefault("identifier", []).append({"value": value})
            elif key == "Phenotype Description":
                patient_json["text"] = str(value)
        return patient_json

    def update_feature_resource(self, example, resource_mapping, cell_value):
        """Update the feature resource example with cell value based on the mapping's FHIR path."""

        fhir_path = resource_mapping.get("target_fhir_path")

        # Find the cell value in the `values` list of the mapping under `phenotype_value`, and grab the element it is part of.
        value_mapping = next(
            (
                x
                for x in resource_mapping.get("values", [])
                if str(x.get("phenotype_value")) == str(cell_value)
            ),
            None,
        )

        # If the value is not found, return the example as is.
        if not value_mapping:
            return example

        # If value is found, update the example resource with the value at the field specified by the FHIR path.
        if fhir_path:
            key = fhir_path.split(".")[-1]
            target_value = value_mapping.get("fhir_value")
            example[key] = target_value
        return example

    def build_bundle(self, patient_resource, feature_resources):
        """Construct a FHIR transaction Bundle from patient and feature resources."""
        # Wrap each resource with a request section using PUT.
        all_resources = [patient_resource] + feature_resources
        entries = []
        for res in all_resources:
            # Make sure resource has an 'id'.
            if not res.get("id"):
                res["id"] = str(uuid.uuid4())
            # Build the request URL from resourceType/id.
            entries.append(
                {
                    "resource": res,
                    "request": {
                        "method": "PUT",
                        "url": f"{res.get('resourceType')}/{res.get('id')}",
                    },
                }
            )
        return {"resourceType": "Bundle", "type": "transaction", "entry": entries}

    def _group_features(self, row):
        """
        Groups feature mappings by grouping_id, updates their resources, applies 'exists'
        flags, and ensures no conflicting exists values.
        Returns a list of updated feature resources (only those where exists is not False).
        """
        grouping_resources = {}
        for column_name, cell_value in row.iloc[0].items():
            # Skip patient-specific columns.
            if column_name in ["Patient Phenotype ID", "Phenotype Description"]:
                continue
            resource_mapping = self.mapping_manager.get_feature_mapping(column_name)
            if not resource_mapping:
                continue
            grouping_id = resource_mapping.get("grouping_id")
            if grouping_id not in grouping_resources:
                try:
                    # Retrieve default resource example for the grouping.
                    _, example = self.get_feature_resources(resource_mapping)
                except Exception as e:
                    print(
                        f"Skipping grouping '{grouping_id}' for feature '{column_name}' due to error: {e}"
                    )
                    continue
                grouping_resources[grouping_id] = {"resource": example, "exists": None}
            # Evaluate exists flag from mapping values.
            exists_val = None
            for val_entry in resource_mapping.get("values", []):
                if str(val_entry.get("phenotype_value")) == str(cell_value):
                    if "exists" in val_entry:
                        exists_val = val_entry["exists"]
                        break
            if exists_val is not None:
                if grouping_resources[grouping_id]["exists"] is None:
                    grouping_resources[grouping_id]["exists"] = exists_val
                    grouping_resources[grouping_id]["resource"]["exists"] = exists_val
                elif grouping_resources[grouping_id]["exists"] != exists_val:
                    raise ValueError(
                        f"Conflicting exists values for grouping {grouping_id}"
                    )
            # Update the feature resource based on FHIR path.
            grouping_resources[grouping_id]["resource"] = self.update_feature_resource(
                grouping_resources[grouping_id]["resource"],
                resource_mapping,
                cell_value,
            )
        # Return resources only if exists flag is not false.
        return [
            grp["resource"]
            for grp in grouping_resources.values()
            if grp["exists"] is not False
        ]

    def _gather_dependent_libraries(self, library_resource, visited=None):
        if visited is None:
            visited = set()
        libs = []
        lib_url = library_resource.get("url")
        if lib_url:
            lib_dep_id = lib_url.rsplit("/", 1)[-1].split("|")[0]
            if lib_dep_id not in visited:
                visited.add(lib_dep_id)
                for dependency in library_resource.get("relatedArtifact", []):
                    if dependency.get("type") == "depends-on" and dependency[
                        "resource"
                    ].startswith("http://smart.who.int/hiv/Library/"):
                        dep_id_version_part = dependency["resource"].split("/")[-1]
                        dep_id = dep_id_version_part.split("|")[0]
                        if dep_id not in visited:
                            library_url = f"{self.ig_root_url}/Library-{dep_id}.json"
                            dep_res = self.get_fhir_resource(library_url)
                            libs.append(dep_res)
                            libs.extend(
                                self._gather_dependent_libraries(dep_res, visited)
                            )
        return libs

    def _find_section_header(self, soup, title):
        # Find the first h3 tag whose text matches the title exactly (after stripping)
        for header in soup.find_all("h3"):
            if header.get_text(strip=True) == title:
                return header
        return None

    def gather_terminology_resources(self):
        """
        Fetches artifacts.html under the IG root and parses sections by finding h3 tags with
        'Terminology: Value Sets' and 'Terminology: Code Systems' as content.
        """
        terminology_resources = []
        try:
            artifacts_url = f"{self.ig_root_url}/artifacts.html"
            resp = requests.get(artifacts_url)
            resp.raise_for_status()
            html_content = resp.text

            soup = BeautifulSoup(html_content, "html.parser")
            sections = {
                "Terminology: Value Sets": None,
                "Terminology: Code Systems": None,
            }
            for title in sections:
                header = self._find_section_header(soup, title)
                if header:
                    table = header.find_next("table", class_="grid")
                    if table:
                        for row in table.find_all("tr"):
                            a_tag = row.find("a", href=True)
                            if a_tag:
                                json_link = a_tag["href"].replace(".html", ".json")
                                if not json_link.startswith("http"):
                                    json_link = (
                                        f"{self.ig_root_url}/{json_link.lstrip('/')}"
                                    )
                                try:
                                    resource = self.get_fhir_resource(json_link)
                                    terminology_resources.append(resource)
                                except Exception as e:
                                    print(f"Error fetching {json_link}: {e}")
        except requests.RequestException as e:
            print(f"Error fetching artifacts.html: {e}")
        return terminology_resources

    def gather_cql_resources(self, mapping_dak_id):
        """
        Gather all CQL related resources from the IG:
         - Measure resource from <ig_root>/Measure-{dak_id_without_periods}.json
         - Main Library resource referenced by the Measure resource.
         - Dependent Library resources based on 'depends-on' fields in the main Library.
         - Terminology resources (CodeSystem and ValueSet) from artifacts.html.

        Returns a dictionary with keys: 'measure', 'main_library', 'dependent_libraries', and 'terminology_resources'.
        """
        # Construct measure URL using dak_id (strip periods)
        measure_url = (
            f"{self.ig_root_url}/Measure-{mapping_dak_id.replace('.', '')}.json"
        )
        measure_resource = self.get_fhir_resource(measure_url)

        # Assume the measure has a 'library' field; extract the main library identifier.
        library_id = measure_resource["library"][0].split("/")[-1]
        main_library_url = f"{self.ig_root_url}/Library-{library_id}.json"
        main_library_resource = self.get_fhir_resource(main_library_url)

        dependent_libraries = self._gather_dependent_libraries(main_library_resource)
        terminology_resources = self.gather_terminology_resources()
        return {
            "measure": measure_resource,
            "main_library": main_library_resource,
            "dependent_libraries": dependent_libraries,
            "terminology_resources": terminology_resources,
        }

    def assemble_cql_bundle(self, patient_bundles, cql_resources):
        """Assemble a complete transaction CQL Bundle by taking all entries from patient bundles as-is."""
        entries = []

        # Add Measure and Library resources.
        for res in [
            cql_resources["measure"],
            cql_resources["main_library"],
        ] + cql_resources["dependent_libraries"]:
            if not res.get("id"):
                res["id"] = str(uuid.uuid4())
            entries.append(
                {
                    "resource": res,
                    "request": {
                        "method": "PUT",
                        "url": f"{res.get('resourceType')}/{res.get('id')}",
                    },
                }
            )

        # Add Terminology resources.
        for res in cql_resources["terminology_resources"]:
            if not res.get("id"):
                res["id"] = str(uuid.uuid4())
            entries.append(
                {
                    "resource": res,
                    "request": {
                        "method": "PUT",
                        "url": f"{res.get('resourceType')}/{res.get('id')}",
                    },
                }
            )

        # Copy each entry from patient bundles without modifying ids.
        for bundle in patient_bundles:
            for entry in bundle.get("entry", []):
                # Ensure the request info is consistent.
                entry["request"]["method"] = "PUT"
                entry["request"][
                    "url"
                ] = f"{entry['resource']['resourceType']}/{entry['resource']['id']}"
                entries.append(entry)

        return {"resourceType": "Bundle", "type": "transaction", "entry": entries}

    def _update_patient_references(self, resource, new_patient_id):
        """Recursively update any references to the default patient with the new patient id."""
        if isinstance(resource, dict):
            for key, value in resource.items():
                if (
                    key == "reference"
                    and isinstance(value, str)
                    and value == "Patient/ExampleHivPatient"
                ):
                    resource[key] = f"Patient/{new_patient_id}"
                else:
                    self._update_patient_references(value, new_patient_id)
        elif isinstance(resource, list):
            for item in resource:
                self._update_patient_references(item, new_patient_id)
        return resource

    def generate_patient_bundles(self):
        """
        Generates individual patient bundles from phenotype data and assembles an
        encapsulated CQL Bundle containing:
         1. Patient Resources updated from the phenotype XLSX.
         2. A Measure resource defining measure criteria.
         3. A primary Library resource along with its dependent libraries (via 'depends-on').
         4. Terminology resources (to be added by parsing an IG's codings documentation).

        Process:
         - Validate that the DAK ID in the phenotype data matches the mapping.
         - For each phenotype row:
             • Update a default Patient resource.
             • Process and update feature resources.
             • Build and save the patient bundle.
         - Call gather_cql_resources() to fetch CQL resources.
         - Call assemble_cql_bundle() to build a consolidated CQL bundle that
           aggregates the Measure, main Library, dependent libraries, and all patient bundles.
         - Save the CQL bundle as "cql_bundle.json" in the output directory.
        """
        data_bundles = []
        mapping_dak_id = self.mapping_manager.mapping.get("dak_id")
        # Validate mapping DAK ID matches phenotype DAK ID.
        phenotype_dak_id = self.indicator_df["DAK ID"].iloc[0]
        if phenotype_dak_id != mapping_dak_id:
            raise ValueError(
                f"Phenotype DAK ID {phenotype_dak_id} does not match mapping DAK ID {mapping_dak_id}"
            )

        # Process each patient phenotype row.
        for idx, row in self.phenotype_df.iterrows():
            # Convert row into single-row DataFrame
            row = pd.DataFrame(row).T
            row.columns = self.phenotype_df.columns

            # Retrieve and update Patient resource.
            patient_profile_name = self.mapping_manager.mapping["patient_profile"]
            patient_resource = self.get_patient_example(patient_profile_name)
            patient_resource = self.update_patient_resource(patient_resource, row)

            # Assign new unique patient id and update patient references.
            new_patient_id = str(uuid.uuid4())
            patient_resource["id"] = new_patient_id
            patient_resource = self._update_patient_references(
                patient_resource, new_patient_id
            )
            patient_phenotype_id = row["Patient Phenotype ID"].iloc[0]

            # Process feature resources for this patient.
            feature_resources = self._group_features(row)
            # Update feature resources to point to the new patient id if needed.
            feature_resources = [
                self._update_patient_references(resource, new_patient_id)
                for resource in feature_resources
            ]

            # Create patient bundle.
            bundle = self.build_bundle(patient_resource, feature_resources)
            bundle["id"] = str(uuid.uuid4())

            # Save the bundle to file.
            bundle_filename = os.path.join(
                self.output_directory,
                f"patient_data_bundle_{patient_phenotype_id}.json",
            )
            with open(bundle_filename, "w") as f:
                f.write(json.dumps(bundle, indent=2))
            data_bundles.append(copy.deepcopy(bundle))

        # --- CQL Bundle Assembly ---
        # 1. Fetch Measure, main Library, and dependent libraries.
        cql_resources = self.gather_cql_resources(mapping_dak_id)
        # 2. Assemble the encapsulated CQL bundle including patient bundles and CQL resources.
        cql_bundle = self.assemble_cql_bundle(data_bundles, cql_resources)
        cql_bundle_filename = os.path.join(self.output_directory, "cql_bundle.json")
        with open(cql_bundle_filename, "w") as f:
            f.write(json.dumps(cql_bundle, indent=2))
        # --- End CQL Bundle Assembly ---

        return data_bundles

    def generate_test_bundle(self):
        """
        Generates a test bundle with a MeasureReport and test artifacts (TestScript and TestPlan)
        to validate FHIR Measure Evaluation.
        """
        # Compute reporting period.
        rp = self.mapping_manager.mapping.get("reporting_period", {})
        period_start = rp.get(
            "start", (datetime.now() - timedelta(days=30)).isoformat()
        )
        period_end = rp.get("end", datetime.now().isoformat())
        reporting_period = {"start": period_start, "end": period_end}
        total_population = len(self.phenotype_df)
        # Build MeasureReport
        measure_report = {
            "resourceType": "MeasureReport",
            "id": str(uuid.uuid4()),
            "status": "final",
            "type": "summary",
            "date": datetime.now().isoformat(),
            "period": reporting_period,
            "group": [
                {
                    "population": [
                        {
                            "code": {"coding": [{"code": "initial-population"}]},
                            "count": total_population,
                        },
                        {"code": {"coding": [{"code": "numerator"}]}, "count": 0},
                        {
                            "code": {"coding": [{"code": "denominator"}]},
                            "count": total_population,
                        },
                    ]
                }
            ],
        }
        measure_report_filename = os.path.join(
            self.output_directory, "test_bundle.json"
        )
        with open(measure_report_filename, "w") as f:
            f.write(json.dumps(measure_report, indent=2))

        # Generate test artifacts using test_artifact_generator
        artifacts = generate_test_artifacts(self.phenotype_df, reporting_period)

        test_script_filename = os.path.join(self.output_directory, "test_script.json")
        with open(test_script_filename, "w") as f:
            f.write(json.dumps(artifacts[0], indent=2))

        test_plan_filename = os.path.join(self.output_directory, "test_plan.json")
        with open(test_plan_filename, "w") as f:
            f.write(json.dumps(artifacts[1], indent=2))

        return measure_report

    def execute(self):
        """
        Executes the complete process:
          1. Creates an output subfolder named after the mapping dak_id.
          2. Generates patient bundles.
          3. Generates the test MeasureReport bundle.
          4. Prints the output location.
        """
        mapping_dak_id = self.mapping_manager.mapping.get("dak_id")
        # Create a subfolder in the output directory named after the DAK ID.
        self.output_directory = os.path.join(self.output_directory, str(mapping_dak_id))
        if not os.path.isdir(self.output_directory):
            os.makedirs(self.output_directory)
        self.generate_patient_bundles()
        self.generate_test_bundle()
        print(f"FHIR resources generated in: {self.output_directory}")
