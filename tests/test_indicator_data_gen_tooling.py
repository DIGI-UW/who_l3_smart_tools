import os
import shutil
import unittest
import yaml
import pandas as pd
import requests
import json
import math
import logging
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
        phenotype_file = "tests/data/scaffolding/v2/phenotype_HIVIND20_filled.xlsx"
        mapping_file = "tests/data/scaffolding/v2/phenotypes_IND20.yaml"
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
        expected_dak_id = "HIV.IND.20"
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

        # Make sure that the cql_bundle has the right contents based on the example indicator files:
        # - 3 Patients
        # - 3 Conditions (1 patient with 0, one with 1, one with 2)
        # - 1 Measure
        # - 1 Library
        with open(cql_bundle_path, "r") as f:
            cql_bundle = json.load(f)
        self.assertIn("entry", cql_bundle)
        entries = cql_bundle.get("entry", [])
        self.assertGreaterEqual(len(entries), 6)
        resource_types = [entry["resource"]["resourceType"] for entry in entries]
        self.assertEqual(resource_types.count("Patient"), 3)
        self.assertEqual(resource_types.count("Condition"), 3)
        self.assertEqual(resource_types.count("Measure"), 1)
        self.assertEqual(resource_types.count("Library"), 2)


if __name__ == "__main__":
    unittest.main()
