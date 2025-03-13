import os
import json
import math
import unittest
import requests
import logging


def sanitize_nan(obj):
    """
    Converts float('NaN') values into None values, ensuring valid JSON before uploading.
    Prereqs: Python 'math' imported, object might contain nested structures.
    """
    if isinstance(obj, float) and math.isnan(obj):
        return None
    elif isinstance(obj, dict):
        return {k: sanitize_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_nan(item) for item in obj]
    return obj


def compare_measure_reports(response_report, expected_report):
    """
    Compares the measure report from the $evaluate-measure operation
    with the one provided in the test bundle for a given indicator.
    Future expansions will handle additional checks like measureScore.
    """
    if response_report.get("resourceType") != "MeasureReport":
        raise ValueError("Response must be a MeasureReport resource.")
    response_groups = response_report.get("group", [])
    expected_groups = expected_report.get("group", [])
    if len(response_groups) != len(expected_groups):
        raise ValueError("Group count mismatch.")
    for i, eg in enumerate(expected_groups):
        rg = response_groups[i]
        # Compare measureScore
        e_score = eg.get("measureScore", {}).get("value")
        r_score = rg.get("measureScore", {}).get("value")
        if e_score is not None and r_score is not None:
            if not math.isclose(e_score, r_score, rel_tol=1e-4):
                raise ValueError("Measure score mismatch.")
        # Compare populations
        e_pops = eg.get("population", [])
        r_pops = rg.get("population", [])
        if len(e_pops) != len(r_pops):
            raise ValueError("Population count mismatch.")
        for j, e_pop in enumerate(e_pops):
            r_pop = r_pops[j]
            e_count = e_pop.get("count")
            r_count = r_pop.get("count")
            if e_count != r_count:
                raise ValueError(
                    f"Population count mismatch for {e_pop.get('id', 'unknown')}"
                )


def run_bundle_test(
    indicator_name="HIV.IND.EX",
    fhir_server_url="http://localhost:8080/fhir",
    cleanup_hapi=False,
):
    """
    Test Outline:
      - Prereqs: A cql_bundle.json & test_bundle.json in tests/output/fhir_bundles/<indicator_name>.
      - Setup: Load the cql_bundle.json, sanitize NaNs, and POST to FHIR server.
      - Test Data: The FHIR server uses measure references from that bundle.
      - Action: Perform a $evaluate-measure operation with the expected period from the test_bundle.json.
      - Assert: Check that the response is a valid MeasureReport with the expected measureScore value.
      - Teardown: Optionally delete loaded resources if cleanup_hapi is True.
    """
    subfolder = os.path.join("tests/data/fhir_bundles", indicator_name)
    cql_bundle_path = os.path.join(subfolder, "cql_bundle.json")
    measure_report_path = os.path.join(subfolder, "measure_report.json")
    measure_name = indicator_name.replace(".", "")

    # Load CQL bundle and POST to FHIR server
    with open(cql_bundle_path, "r") as f:
        cql_bundle = json.load(f)
    cql_bundle = sanitize_nan(cql_bundle)

    post_resp = requests.post(f"{fhir_server_url}", json=cql_bundle)
    if not post_resp.ok:
        raise requests.HTTPError(
            f"Error loading CQL bundle: {post_resp.status_code} - {post_resp.text}"
        )

    # Save created resource ids for cleanup
    created_ids = []
    for entry in post_resp.json().get("entry", []):
        # Get id from location like Measure/HIVINDEX/_history/1
        response = entry.get("response", {})
        location = response.get("location")
        split_location = location.split("/")
        resource_path = split_location[0] + "/" + split_location[1]
        if resource_path and resource_path is not None:
            created_ids.append(resource_path)

    # Load expected report and compare with evaluate response
    with open(measure_report_path, "r") as f:
        expected_report = json.load(f)
    period = expected_report.get("period", {})
    period_start = period.get("start")
    period_end = period.get("end")

    evaluate_url = f"{fhir_server_url}/Measure/{measure_name}/$evaluate-measure"
    params = {"periodStart": period_start, "periodEnd": period_end}
    evaluate_op_response = requests.get(evaluate_url, params=params)
    logging.info("Evaluate measure response: %s", evaluate_op_response.text)

    if '"resourceType": "MeasureReport"' not in evaluate_op_response.text:
        raise ValueError(
            "Evaluate measure response does not contain MeasureReport resource."
        )

    compare_measure_reports(evaluate_op_response.json(), expected_report)

    if cleanup_hapi:
        # Clean up all resources with ids in created_ids
        for resource_path in created_ids:
            delete_url = (
                f"{fhir_server_url}/{resource_path}?_cascade=delete&_expunge=true"
            )
            del_resp = requests.delete(delete_url)
            if not del_resp.ok and del_resp.status_code != 404:
                logging.error(
                    "Failed to delete resource %s: %s", resource_path, del_resp.json()
                )

    return evaluate_op_response.json()


class TestIndicatorEvaluation(unittest.TestCase):
    """
    Tests for indicator evaluation workflow:
      1. Load existing CQL bundle into the specified FHIR server.
      2. Evaluate a measure using the $evaluate-measure operation.
      3. Compare results.
    """

    def test_bundle_loading_default(self):
        """
        Default test using 'HIVINDEX' as the indicator_name.
        Asserts that the returned structure is a dict.
        """
        result = run_bundle_test(cleanup_hapi=True)
        # with open("tests/data/fhir_bundles/HIV.IND.EX/test_bundle.json", "r") as f:
        #     expected_report = json.load(f)
        # compare_measure_reports(result, expected_report)
        self.assertIsInstance(result, dict)

    def test_bundle_loading_custom_indicator(self):
        """
        Test using a custom indicator name, verifying reusability with different data sets.
        Assumes a matching cql_bundle.json exists for 'CUSTOMINDICATOR'.
        """
        custom_indicator = "HIVIND20"
        result = run_bundle_test(indicator_name=custom_indicator, cleanup_hapi=True)
        with open(
            f"tests/data/fhir_bundles/{custom_indicator}/test_bundle.json", "r"
        ) as f:
            expected_report = json.load(f)
        compare_measure_reports(result, expected_report)
        self.assertIsInstance(result, dict)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
