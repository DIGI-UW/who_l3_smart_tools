import os
import unittest
from who_l3_smart_tools.core.cql_tools.subset_generation.cql_subset_generation import (
    CQLSubsetGenerator,
)


class TestCQLSubsetGeneration(unittest.TestCase):
    def setUp(self):
        # Setup paths to test data and output
        self.base_cql_dir = "/Users/pmanko/code/who_l3_smart_tools/tests/data/cql"
        self.parent_file = os.path.join(self.base_cql_dir, "HIVIND20Logic.cql")
        self.elements_file = os.path.join(self.base_cql_dir, "HIVElements.cql")
        self.indicators_file = os.path.join(
            self.base_cql_dir, "HIVIndicatorElements.cql"
        )
        self.output_dir = os.path.join(self.base_cql_dir, "subsets")
        os.makedirs(self.output_dir, exist_ok=True)

    def test_subset_generation(self):
        generator = CQLSubsetGenerator(
            parent_path=self.parent_file,
            base_cql_dir=self.base_cql_dir,
            output_dir=self.output_dir,
            elements_path=self.elements_file,
            indicators_path=self.indicators_file,
        )
        # Run subset generation
        generator.run()

        # Check that both generated files exist and are not empty
        indicator_subset_path = os.path.join(
            self.output_dir, os.path.basename(self.indicators_file)
        )
        elements_subset_path = os.path.join(
            self.output_dir, os.path.basename(self.elements_file)
        )
        self.assertTrue(
            os.path.exists(indicator_subset_path),
            f"File not found: {indicator_subset_path}",
        )
        self.assertTrue(
            os.path.exists(elements_subset_path),
            f"File not found: {elements_subset_path}",
        )

        with open(indicator_subset_path, "r", encoding="utf-8") as f:
            indicator_subset = f.read()
        with open(elements_subset_path, "r", encoding="utf-8") as f:
            elements_subset = f.read()

        # Check that the new subset marker is present
        self.assertIn("// ...subset definitions...", indicator_subset)
        self.assertIn("// ...subset definitions...", elements_subset)

        # Additionally, verify that an intra-file definition (for example "HIV Status Observation")
        # has been captured in the elements subset.
        self.assertIn('define "HIV Status Observation":', elements_subset)


if __name__ == "__main__":
    unittest.main()
