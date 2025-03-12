import os
import shutil
import unittest
import yaml
import pandas as pd
import requests
import json
import math
from who_l3_smart_tools.core.indicator_testing.v2.phenotype_generator import (
    generate_phenotype_xlsx,
)
from who_l3_smart_tools.core.indicator_testing.v2.dataset_generator import (
    generate_random_dataset,
)

from who_l3_smart_tools.core.indicator_testing.v2.fhir_bundle_generator import (
    FhirBundleGenerator,
)

from who_l3_smart_tools.core.indicator_testing.v2.mapping_template_generator import (
    generate_mapping_template,
)


class TestIndicatorDataGenTooling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.input_excel = "tests/data/l2/test_indicators.xlsx"
        cls.phenotype_template_excel = "tests/data/testing/phenotype_INDEX.xlsx"
        cls.dataset_excel = "tests/output/dataset_v2.xlsx"
        cls.measure_report_json = "tests/output/measure_report_ex.json"
        cls.mapping_template_yaml = "tests/output/mapping_template_INDEX.yaml"
        os.makedirs("tests/output/testing", exist_ok=True)
        os.makedirs("tests/output", exist_ok=True)

    def test_generate_phenotype_template(self):
        generate_phenotype_xlsx(
            self.input_excel, self.phenotype_template_excel, "HIV.IND.EX"
        )
        df = pd.read_excel(self.phenotype_template_excel)
        self.assertEqual(len(df), 3)

    # Ignore for now
    def test_generate_dataset(self):
        generate_random_dataset(
            self.phenotype_template_excel, self.dataset_excel, num_rows=10
        )
        df = pd.read_excel(self.dataset_excel)
        self.assertEqual(len(df), 10)

    def test_generate_mapping_template(self):
        # Generate mapping template using the phenotype file and output YAML location.
        phenotype_file = "tests/data/testing/phenotype_INDEX.xlsx"
        output_yaml = self.mapping_template_yaml

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_yaml), exist_ok=True)

        generate_mapping_template(phenotype_file, output_yaml)

        # Check the file exists
        self.assertTrue(os.path.exists(output_yaml))

        # Read the output file content
        with open(output_yaml, "r") as f:
            content = f.read()

        # Split commented meta (lines starting with '#') from YAML dump
        lines = content.splitlines()
        meta_lines = [line for line in lines if line.startswith("#")]
        yaml_lines = [line for line in lines if not line.startswith("#")]

        # Ensure meta comments are present
        self.assertTrue(len(meta_lines) > 0, "Meta comments missing in YAML output")

        # Parse the YAML part
        yaml_content = yaml.safe_load("\n".join(yaml_lines))
        self.assertIn("dak_id", yaml_content)
        self.assertIn("features", yaml_content)
        self.assertIsInstance(
            yaml_content["features"], list, "Features should be a list"
        )
        self.assertGreater(len(yaml_content["features"]), 0)

        for feature in yaml_content["features"]:
            self.assertIn("name", feature)
            self.assertIn("id", feature)
            self.assertIn("target_profile", feature)
            self.assertIn("target_valueset", feature)
            self.assertIn("values", feature)
            self.assertIsInstance(
                feature["values"], list, "Feature values should be a list"
            )


class TestFhirBundleTests(unittest.TestCase):
    # Skip for CI
    # @unittest.skip("Skip for CI")
    def setUp(self):
        phenotype_file = "tests/data/scaffolding/v2/phenotype_INDEX.xlsx"
        mapping_file = "tests/data/testing/mapping_template_INDEX.yaml"
        output_directory = "tests/output/fhir_bundles"
        if os.path.exists(output_directory):
            shutil.rmtree(output_directory)
        os.makedirs(output_directory)
        generator = FhirBundleGenerator(
            phenotype_file, mapping_file, output_directory, "http://localhost:8099"
        )
        generator.execute()

    def test_fhir_bundle_generator(self):
        """
        Tests FHIR bundle generation:
          - Uses given phenotype and mapping files.
          - Verifies that output is created inside a subfolder named after the dak_id.
          - Checks that the test_bundle.json and patient_data_bundle_<Patient Phenotype ID>.json files exist.
        """
        # Retrieve the dak_id from the mapping file.
        expected_dak_id = "HIV.IND.EX"
        subfolder = os.path.join("tests/output/fhir_bundles", expected_dak_id)
        self.assertTrue(os.path.isdir(subfolder), f"Subfolder {subfolder} not found.")

        # Check that test artifact bundle exists in the subfolder.
        test_bundle_path = os.path.join(subfolder, "test_bundle.json")
        self.assertTrue(
            os.path.exists(test_bundle_path),
            f"Test bundle {test_bundle_path} not found.",
        )

        # Check that cql_bundle.json is created
        cql_bundle_path = os.path.join(subfolder, "cql_bundle.json")
        self.assertTrue(
            os.path.exists(cql_bundle_path),
            f"cql_bundle.json not found in {subfolder}.",
        )

        # Check that test_script.json and test_plan.json are generated
        test_script_path = os.path.join(subfolder, "test_script.json")
        test_plan_path = os.path.join(subfolder, "test_plan.json")
        self.assertTrue(
            os.path.exists(test_script_path),
            f"test_script.json not found in {subfolder}.",
        )
        self.assertTrue(
            os.path.exists(test_plan_path), f"test_plan.json not found in {subfolder}."
        )

        # Check that at least one patient bundle file (with prefix 'patient_data_bundle_') exists in the subfolder.
        patient_bundles = [
            f
            for f in os.listdir(subfolder)
            if f.startswith("patient_data_bundle_") and f.endswith(".json")
        ]
        self.assertTrue(len(patient_bundles) > 0, "No patient bundles were generated.")

    def test_load_and_evaluate_indicator(self):
        CLEANUP_HAPI = False  # Set to False to skip cleanup
        FHIR_SERVER_URL = "http://localhost:8080/fhir"
        # Check that the FHIR server is up
        try:
            meta = requests.get(f"{FHIR_SERVER_URL}/metadata")
            self.assertEqual(meta.status_code, 200, "FHIR server is down.")
        except Exception as e:
            self.fail(f"FHIR server check failed: {e}")

        # Load and post the CQL bundle
        subfolder = os.path.join("tests/output/fhir_bundles", "HIV.IND.20")
        cql_bundle_path = os.path.join(subfolder, "cql_bundle.json")
        with open(cql_bundle_path, "r") as f:
            cql_bundle = json.load(f)

        # Sanitize the bundle to replace NaN values
        def sanitize_nan(obj):
            if isinstance(obj, float) and math.isnan(obj):
                return None
            elif isinstance(obj, dict):
                return {k: sanitize_nan(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [sanitize_nan(item) for item in obj]
            return obj

        cql_bundle = sanitize_nan(cql_bundle)

        post_resp = requests.post(f"{FHIR_SERVER_URL}", json=cql_bundle)
        if not post_resp.ok:
            raise Exception(
                f"Error loading CQL bundle: {post_resp.status_code} - {post_resp.text}"
            )

        # Load expected measure report from the generated test bundle
        expected_bundle_path = os.path.join(subfolder, "test_bundle.json")
        with open(expected_bundle_path, "r") as f:
            expected_report = json.load(f)

        period = expected_report.get("period", {})
        period_start = period.get("start")
        period_end = period.get("end")
        self.assertIsNotNone(period_start, "Period start missing in expected report.")
        self.assertIsNotNone(period_end, "Period end missing in expected report.")

        # Execute the $evaluate-measure operation using the period from expected report.
        evaluate_url = f"{FHIR_SERVER_URL}/Measure/HIVIND20/$evaluate-measure"
        params = {"periodStart": period_start, "periodEnd": period_end}
        resp = requests.get(evaluate_url, params=params)

        # Print response
        print(resp.text)

        # self.assertEqual(resp.status_code, 200, "Evaluate measure operation failed.")
        # new_report = resp.json()

        # # Compare population counts for initial-population, numerator, denominator.
        # def get_population_counts(report):
        #     counts = {}
        #     for group in report.get("group", []):
        #         for pop in group.get("population", []):
        #             code = pop.get("code", {}).get("coding", [{}])[0].get("code")
        #             counts[code] = pop.get("count")
        #     return counts

        # expected_counts = get_population_counts(expected_report)
        # evaluated_counts = get_population_counts(new_report)
        # for key in ["initial-population", "numerator", "denominator"]:
        #     self.assertIn(key, expected_counts, f"Expected count for {key} not found.")
        #     self.assertIn(
        #         key, evaluated_counts, f"Evaluated count for {key} not found."
        #     )
        #     self.assertEqual(
        #         expected_counts[key],
        #         evaluated_counts[key],
        #         f"Mismatch in count for {key}.",
        #     )

        # Cleanup: remove the resources loaded via the CQL bundle after evaluation
        if CLEANUP_HAPI:
            entries = []
            if isinstance(cql_bundle, dict):
                temp_entries = cql_bundle.get("entry")
                if isinstance(temp_entries, list):
                    entries = temp_entries
            for entry in entries:
                if isinstance(entry, dict):
                    resource = entry.get("resource", {})
                    if isinstance(resource, dict):
                        resource_type = resource.get("resourceType")
                        resource_id = resource.get("id")
                        if resource_type and resource_id:
                            delete_url = (
                                f"{FHIR_SERVER_URL}/{resource_type}/{resource_id}"
                            )
                            del_resp = requests.delete(delete_url)
                            if not del_resp.ok and del_resp.status_code != 404:
                                raise Exception(
                                    f"Cleanup failed for {resource_type}/{resource_id}: {del_resp.status_code}"
                                )


if __name__ == "__main__":
    unittest.main()
