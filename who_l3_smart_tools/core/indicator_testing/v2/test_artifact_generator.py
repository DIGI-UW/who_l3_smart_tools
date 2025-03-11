from datetime import datetime
import json

# Definitions and Examples
test_plan_definition_json = r"""{
    "resourceType": "TestPlan",
    "url": "<uri>",
    "identifier": [{}],
    "version": "<string>",
    "versionAlgorithmString": "<string>",
    "versionAlgorithmCoding": {},
    "name": "<string>",
    "title": "<string>",
    "status": "<code>",
    "experimental": true,
    "date": "<dateTime>",
    "publisher": "<string>",
    "contact": [{}],
    "description": "<markdown>",
    "useContext": [{}],
    "jurisdiction": [{}],
    "purpose": "<markdown>",
    "copyright": "<markdown>",
    "copyrightLabel": "<string>",
    "category": [{}],
    "scope": [{}],
    "testTools": "<markdown>",
    "dependency": [{
        "description": "<markdown>",
        "predecessor": {}
    }],
    "exitCriteria": "<markdown>",
    "testCase": [{
        "key": "<id>",
        "description": "<markdown>",
        "sequence": 0,
        "scope": [{}],
        "requirement": [{
            "reference": "<canonical(Requirements)>",
            "key": "<id>"
        }],
        "dependency": [{
            "description": "<markdown>",
            "reference": "<canonical(TestPlan)>",
            "key": "<id>"
        }],
        "testRun": [{
            "narrative": "<markdown>",
            "script": {
                "language": {},
                "sourceString": "<string>",
                "sourceReference": {}
            }
        }],
        "testData": [{
            "type": {},
            "content": {},
            "sourceString": "<string>",
            "sourceReference": {}
        }],
        "assertion": [{
            "type": [{}],
            "object": [{}],
            "result": [{}]
        }]
    }]
}"""

test_script_definition_json = r"""{
    "resourceType": "TestScript",
    "url": "<uri>",
    "identifier": [{}],
    "version": "<string>",
    "versionAlgorithmString": "<string>",
    "versionAlgorithmCoding": {},
    "name": "<string>",
    "title": "<string>",
    "status": "<code>",
    "experimental": true,
    "date": "<dateTime>",
    "publisher": "<string>",
    "contact": [{}],
    "description": "<markdown>",
    "useContext": [{}],
    "jurisdiction": [{}],
    "purpose": "<markdown>",
    "copyright": "<markdown>",
    "copyrightLabel": "<string>",
    "origin": [{
        "index": 1,
        "profile": {},
        "url": "<url>"
    }],
    "destination": [{
        "index": 1,
        "profile": {},
        "url": "<url>"
    }],
    "metadata": {
        "link": [{
            "url": "<uri>",
            "description": "<string>"
        }],
        "capability": [{
            "required": true,
            "validated": true,
            "description": "<string>",
            "origin": [1],
            "destination": 1,
            "link": ["<uri>"],
            "capabilities": "<canonical(CapabilityStatement)>"
        }]
    },
    "scope": [{
        "artifact": "<canonical(Any)>",
        "conformance": {},
        "phase": {}
    }],
    "fixture": [{
        "autocreate": true,
        "autodelete": true,
        "resource": {}
    }],
    "profile": ["<canonical(StructureDefinition)>"],
    "variable": [{
        "name": "<string>",
        "defaultValue": "<string>",
        "description": "<string>",
        "expression": "<string>",
        "headerField": "<string>",
        "hint": "<string>",
        "path": "<string>",
        "sourceId": "<id>"
    }],
    "setup": {
        "action": [{
            "common": {
                "testScript": "<canonical(TestScript)>",
                "keyRef": "<id>",
                "parameter": [{
                    "name": "<string>",
                    "value": "<string>"
                }]
            },
            "operation": {
                "type": {},
                "resource": "<uri>",
                "label": "<string>",
                "description": "<string>",
                "accept": "<code>",
                "contentType": "<code>",
                "destination": 1,
                "encodeRequestUrl": true,
                "method": "<code>",
                "origin": 1,
                "params": "<string>",
                "requestHeader": [{
                    "field": "<string>",
                    "value": "<string>"
                }],
                "requestId": "<id>",
                "responseId": "<id>",
                "sourceId": "<id>",
                "targetId": "<id>",
                "url": "<string>"
            },
            "assert": {
                "label": "<string>",
                "description": "<string>",
                "direction": "<code>",
                "compareToSourceId": "<string>",
                "compareToSourceExpression": "<string>",
                "compareToSourcePath": "<string>",
                "contentType": "<code>",
                "defaultManualCompletion": "<code>",
                "expression": "<string>",
                "headerField": "<string>",
                "minimumId": "<string>",
                "navigationLinks": true,
                "operator": "<code>",
                "path": "<string>",
                "requestMethod": "<code>",
                "requestURL": "<string>",
                "resource": "<uri>",
                "response": "<code>",
                "responseCode": "<string>",
                "sourceId": "<id>",
                "stopTestOnFail": true,
                "validateProfileId": "<id>",
                "value": "<string>",
                "warningOnly": true,
                "requirement": [{
                    "reference": "<canonical(Requirements)>",
                    "key": "<id>"
                }]
            }
        }]
    },
    "test": [{
        "name": "<string>",
        "description": "<string>",
        "action": [{
            "common": {},
            "operation": {},
            "assert": {}
        }]
    }],
    "teardown": {
        "action": [{
            "common": {},
            "operation": {}
        }]
    },
    "common": [{
        "key": "<id>",
        "name": "<string>",
        "description": "<string>",
        "parameter": [{
            "name": "<string>",
            "description": "<string>"
        }],
        "action": [{
            "operation": {},
            "assert": {}
        }]
    }]
}"""

measure_report_example = {
    "resourceType": "MeasureReport",
    "status": "final",
    "type": "summary",
    "date": "2024-07-08 13:18:25.300803+00:00",
    "period": {
        "start": "2023-07-09 13:15:42.955790+00:00",
        "end": "2024-07-08 13:15:42.955790+00:00",
    },
    "group": [
        {
            "population": [
                {"code": {"coding": [{"code": "initial-population"}]}, "count": 1016},
                {"code": {"coding": [{"code": "numerator"}]}, "count": 208},
                {"code": {"coding": [{"code": "denominator"}]}, "count": 424},
            ]
        }
    ],
}


def generate_test_artifacts(phenotype_dataset, reporting_period):
    # Generate MeasureReport using the existing function
    measure_report = generate_measure_report(phenotype_dataset, reporting_period)

    # Load and update TestPlan
    test_plan = json.loads(test_plan_definition_json)
    test_plan.update(
        {
            "title": "Automated Test Plan",
            "date": datetime.now().isoformat(),
            "publisher": "Automated Generator",
            "fixture": [
                {
                    "sourceId": "test-data-bundle",
                    "description": "Test data bundle containing patient and additional resources",
                }
            ],
        }
    )

    # Load and update TestScript
    test_script = json.loads(test_script_definition_json)
    test_script.update(
        {
            "title": "Automated Test Script",
            "date": datetime.now().isoformat(),
            "setup": {
                "action": [
                    {
                        "operation": {
                            "type": {
                                "system": "http://hl7.org/fhir/testscript-operation-codes",
                                "code": "create",
                            },
                            "resource": "Bundle",
                            "sourceId": "test-data-bundle",
                            "responseId": "create-data-response",
                        }
                    },
                    {
                        "operation": {
                            "type": {
                                "system": "http://hl7.org/fhir/testscript-operation-codes",
                                "code": "create",
                            },
                            "resource": "Measure",
                            "sourceId": "given-measure",
                            "responseId": "create-measure-response",
                        }
                    },
                    {
                        "operation": {
                            "type": {
                                "system": "http://hl7.org/fhir/testscript-operation-codes",
                                "code": "create",
                            },
                            "resource": "Library",
                            "sourceId": "cql-library",
                            "responseId": "create-library-response",
                        }
                    },
                ]
            },
            "test": [
                {
                    "name": "Evaluate Measure Test",
                    "description": "Load test data, execute $evaluate-measure, and compare the generated MeasureReport.",
                    "action": [
                        {
                            "operation": {
                                "type": {
                                    "system": "http://hl7.org/fhir/testscript-operation-codes",
                                    "code": "operation",
                                },
                                "resource": "Measure",
                                "url": "$evaluate-measure",
                                "params": f"?reportingPeriodStart={reporting_period["start"]}&reportingPeriodEnd={reporting_period["end"]}",
                                "sourceId": "create-measure-response",
                                "responseId": "evaluate-response",
                            }
                        },
                        {
                            "assert": {
                                "compareToExpression": "expectedMeasureReport",
                                "response": "evaluate-response",
                                "operator": "equals",
                            }
                        },
                    ],
                }
            ],
            "teardown": {
                "action": [
                    {
                        "operation": {
                            "type": {
                                "system": "http://hl7.org/fhir/testscript-operation-codes",
                                "code": "delete",
                            },
                            "targetId": "create-data-response",
                        }
                    },
                    {
                        "operation": {
                            "type": {
                                "system": "http://hl7.org/fhir/testscript-operation-codes",
                                "code": "delete",
                            },
                            "targetId": "create-measure-response",
                        }
                    },
                    {
                        "operation": {
                            "type": {
                                "system": "http://hl7.org/fhir/testscript-operation-codes",
                                "code": "delete",
                            },
                            "targetId": "create-library-response",
                        }
                    },
                ]
            },
        }
    )

    # Wrap resources in transaction entries
    def transaction_wrap(res):
        return {
            "resource": res,
            "request": {
                "method": "PUT",
                "url": f"{res.get('resourceType')}/{res.get('id')}",
            },
        }

    measure_report = transaction_wrap(measure_report)
    test_plan = transaction_wrap(test_plan)
    test_script = transaction_wrap(test_script)

    # Build and return the Testing Bundle containing MeasureReport, TestPlan, and TestScript
    test_bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            measure_report,  # assuming measure_report is JSON serializable
            test_plan,
            test_script,
        ],
    }
    return json.dumps(test_bundle, indent=4)


def generate_measure_report(phenotype_dataset, reporting_period, output_json=None):
    # Count sum of 1s in the `Counted as Numerator (0,1)` and `Counted as Denominator (0,1)` columns
    denominator_sum = sum(phenotype_dataset["Counted as Denominator (0,1)"])
    numerator_sum = sum(phenotype_dataset["Counted as Numerator (0,1)"])

    measure_report = {
        "resourceType": "MeasureReport",
        "id": "measurereport-v2",
        "status": "complete",
        "type": "summary",
        "measure": "http://example.org/measure/HIV.IND.20",
        "date": datetime.now().isoformat(),
        "period": {"start": reporting_period["start"], "end": reporting_period["end"]},
        "group": [
            {
                "population": [
                    {
                        "code": {"coding": [{"code": "initial-population"}]},
                        "count": denominator_sum,
                    },
                    {
                        "code": {"coding": [{"code": "numerator"}]},
                        "count": numerator_sum,
                    },
                ]
            }
        ],
    }

    if output_json is not None:
        with open(output_json, "w") as f:
            json.dump(measure_report, f, indent=4)

    return measure_report
