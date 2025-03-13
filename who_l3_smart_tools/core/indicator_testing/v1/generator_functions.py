from re import sub
import re
import traceback
import uuid
from fhir.resources.patient import Patient
from fhir.resources.observation import Observation
from fhir.resources.condition import Condition
from fhir.resources.medicationstatement import MedicationStatement
from fhir.resources.medication import Medication
from fhir.resources.codeablereference import CodeableReference
from fhir.resources.coding import Coding
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.diagnosticreport import DiagnosticReport
from fhir.resources.servicerequest import ServiceRequest
from fhir.resources.episodeofcare import EpisodeOfCare
from fhir.resources.bundle import Bundle
from fhir.resources.bundle import BundleEntry
from fhir.resources.bundle import BundleEntryRequest
from fhir.resources.fhirtypes import UriType as Uri

import random
import time
from datetime import datetime, timedelta

# This collection of functions is used to generate synthetic FHIR resources for testing purposes.


# Helper Functions


def snake_case(s):
    # Replace hyphens with spaces
    s = s.replace("-", " ")
    # Remove all non-alphanumeric characters except spaces
    s = re.sub(r"[^A-Za-z0-9 ]+", "", s)
    # Apply regular expression substitutions for title case conversion and add an underscore between words
    s = "_".join(re.sub("([A-Z][a-z]+)", r" \1", re.sub("([A-Z]+)", r" \1", s)).split())
    # Convert the result to lowercase
    return s.lower()


def generate_patient_resource(row):
    # Create an instance of Patient
    patient = Patient.parse_obj(
        {
            "resourceType": "Patient",
            "id": row["Patient.ID"],
            "gender": (
                row["Patient.Gender"].lower()
                if row["Patient.Gender"] in ["male", "female", "other", "unknown"]
                else "unknown"
            ),
            "birthDate": row["Patient.DOB"],
            # Additional required attributes should be added here
        }
    )
    return patient


def generate_observation_resource(code, patient_id, val=None):

    if code and isinstance(code, dict) and "text" in code:
        code = code
    elif code and isinstance(code, dict) and "code" in code:
        code = {"coding": [code]}

    # Create an instance of Observation
    observation = Observation.parse_obj(
        {
            "resourceType": "Observation",
            "status": "final",
            # Observation subject would need to be a reference to the Patient resource
            "subject": {"reference": f"Patient/{patient_id}"},
            "code": code,
        }
    )

    if val:
        observation.valueString = val

    return observation


def find_or_create_test_resources(bundle, row, test_coding):
    # Create ServiceRequest, DiagnosticReport, and Observation resources
    test_resources = {}

    # Generate uuids for the resources
    dr_uuid = str(uuid.uuid4())
    obs_uuid = str(uuid.uuid4())
    sr_uuid = row["Test.id"] if "Test.id" in row else str(uuid.uuid4())

    # Find ServiceRequest if it exists
    service_request_entry = next(
        (
            x
            for x in bundle.entry
            if x.resource.resource_type == "ServiceRequest"
            and x.resource.code.concept.coding
            and len(x.resource.code.concept.coding) > 0
            and x.resource.code.concept.coding[0].code == test_coding["code"]
        ),
        None,
    )

    service_request = (
        service_request_entry.resource
        if service_request_entry and service_request_entry.resource
        else None
    )

    if not service_request:
        service_request = ServiceRequest.parse_obj(
            {
                "id": f"{sr_uuid}",
                "resourceType": "ServiceRequest",
                "subject": {"reference": f"Patient/{row['Patient.id']}"},
                "status": "active",
                "intent": "order",
                "code": {"concept": {"coding": [test_coding]}},
            }
        )

        bundle.entry.append(
            BundleEntry(
                resource=service_request,
                request=BundleEntryRequest(method="PUT", url=Uri("ServiceRequest")),
            )
        )
    test_resources["sr"] = service_request

    # Find DiagnosticReport if it exists
    diagnostic_report = next(
        (
            x
            for x in bundle.entry
            if x.resource.resource_type == "DiagnosticReport"
            and x.resource.basedOn
            and x.resource.basedOn[0].reference == f"ServiceRequest/{sr_uuid}"
        ),
        None,
    )

    diagnostic_report = (
        diagnostic_report.resource
        if diagnostic_report and diagnostic_report.resource
        else None
    )

    if not diagnostic_report:
        diagnostic_report = DiagnosticReport.parse_obj(
            {
                "id": f"{dr_uuid}",
                "resourceType": "DiagnosticReport",
                "code": {"coding": [test_coding]},
                "basedOn": [{"reference": f"ServiceRequest/{sr_uuid}"}],
                "status": "final",
                "subject": {"reference": f"Patient/{row['Patient.id']}"},
                "result": [{"reference": f"Observation/{obs_uuid}"}],
            }
        )
        bundle.entry.append(
            BundleEntry(
                resource=diagnostic_report,
                request=BundleEntryRequest(method="PUT", url=Uri("DiagnosticReport")),
            )
        )
    test_resources["dr"] = diagnostic_report
    # Find Observation if it exists
    observation = next(
        (
            x
            for x in bundle.entry
            if x.resource.resource_type == "Observation"
            and x.resource.code.coding
            and len(x.resource.code.coding) > 0
            and x.resource.code.coding[0] == test_coding
        ),
        None,
    )

    observation = observation.resource if observation and observation.resource else None

    if not observation:
        observation = Observation.parse_obj(
            {
                "id": f"{obs_uuid}",
                "resourceType": "Observation",
                "status": "final",
                "code": {"coding": [test_coding]},
                "subject": {"reference": f"Patient/{row['Patient.id']}"},
            }
        )
        bundle.entry.append(
            BundleEntry(
                resource=observation,
                request=BundleEntryRequest(method="PUT", url=Uri("Observation")),
            )
        )
    test_resources["obs"] = observation

    return test_resources, bundle


def find_or_create_condition_resource(bundle, coding):
    condition_resource = None

    for r in bundle.entry:
        try:
            if r.resource.resource_type == "Condition":
                if (
                    r.resource.code.coding[0].code == coding["code"]
                    and r.resource.code.coding[0].system == coding["system"]
                ):
                    condition_resource = r.resource
                    break
        except:
            pass
    if not condition_resource:
        condition_resource = Condition.construct()
        bundle.entry.append(
            BundleEntry(
                resource=condition_resource,
                request=BundleEntryRequest(method="PUT", url=Uri("Condition")),
            )
        )
    return condition_resource, bundle


def update_condition_resource(
    condition, row, coding=None, start_date=None, end_date=None
):
    condition.clinicalStatus = {
        "coding": [
            {
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": "active",
                "display": "Active",
            }
        ]
    }
    condition.verificationStatus = {
        "coding": [
            {
                "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                "code": "confirmed",
            }
        ]
    }

    if coding and isinstance(coding, list):
        condition.code = {"coding": coding}

    if start_date and end_date:
        condition.onsetDateTime = random_date_between(start_date, end_date).isoformat()

    condition.subject = {"reference": f"Patient/{row['Patient.id']}"}


def generate_art_medication_statement_resource(row, start_date, end_date):
    # Create an instance of MedicationStatement
    medication_statement = MedicationStatement.parse_obj(
        {
            "resourceType": "MedicationStatement",
            "status": "active",
            "code": {
                "coding": [
                    {
                        "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                        "code": "1049620",
                        "display": "Tenofovir disoproxil fumarate 300 MG / emtricitabine 200 MG Oral Tablet [Truvada]",
                    }
                ]
            },
            "subject": {"reference": f"Patient/{row['Patient.ID']}"},
            "effectiveDateTime": random_date_between(start_date, end_date).isoformat(),
            "dosage": [
                {
                    "text": "Take one tablet once daily",
                    "timing": {
                        "repeat": {"frequency": 1, "period": 1, "periodUnit": "d"}
                    },
                    "route": {
                        "coding": [
                            {
                                "system": "http://snomed.info/sct",
                                "code": "26643006",
                                "display": "Oral route",
                            }
                        ]
                    },
                    "doseQuantity": {
                        "value": 1,
                        "unit": "tablet",
                        "system": "http://unitsofmeasure.org",
                        "code": "tablet",
                    },
                }
            ],
        }
    )
    return medication_statement


def add_deceased_information(patient, measurementEnd):
    # Generate random date of death before measurementEnd
    deathDate = random_date(patient.birthDate, measurementEnd)

    # Add deceased information to the Patient resource
    if random.choice([True, False]):
        patient.deceasedBoolean = True
    else:
        patient.deceasedDateTime = deathDate

    return patient


def add_future_deceased_information(patient, measurementEnd):
    # Generate random date of death after measurementEnd
    deathDate = random_date(measurementEnd, measurementEnd + timedelta(days=365))

    # Add deceased information to the Patient resource
    if random.choice([True, False]):
        patient.deceasedBoolean = True
    else:
        patient.deceasedDateTime = deathDate

    return patient


def str_time_prop(start, end, time_format, prop):
    """Get a time at a proportion of a range of two formatted times.

    start and end should be strings specifying times formatted in the
    given format (strftime-style), giving an interval [start, end].
    prop specifies how a proportion of the interval to be taken after
    start.  The returned time will be in the specified format.
    """
    start = start[:10]
    end = end[:10]

    stime = time.mktime(time.strptime(start, time_format))
    etime = time.mktime(time.strptime(end, time_format))

    ptime = stime + prop * (etime - stime)

    return time.strftime(time_format, time.localtime(ptime))


def random_date(start, end):
    return str_time_prop(
        start.isoformat(), end.isoformat(), "%Y-%m-%d", random.random()
    )


def get_episode_of_care_scaffold():
    return EpisodeOfCare.parse_obj(
        {
            "resourceType": "EpisodeOfCare",
            "patient": {"reference": f"Patient/{row['Patient.id']}"},
            "diagnosis": [
                {
                    "condition": {"reference": "Condition/condition1"},
                    "role": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/diagnosis-role",
                                "code": "primary",
                            }
                        ]
                    },
                    "rank": 1,
                }
            ],
        }
    )


def generate_episode_of_care_finished_before_measurement(row, measurement_end):
    """
    Generate an EpisodeOfCare resource that ends before the measurement period.
    """
    # Parse from string
    episode_of_care = get_episode_of_care_scaffold()
    episode_of_care.status = "finished"

    # Assuming the date of birth is in row['Patient.birthDate']
    dob = datetime.fromisoformat(row["Patient.birthDate"])
    period_end = random_date_between(dob, measurement_end)
    period_start = random_date_between(dob, period_end)

    # Create the period
    episode_of_care.period = {
        "start": period_start.isoformat(),
        "end": period_end.isoformat(),
    }

    return episode_of_care


def generate_episode_of_care_finished_after_measurement(row, measurement_end):
    """
    Generate an EpisodeOfCare resource that ends after the measurement period.
    """
    episode_of_care = get_episode_of_care_scaffold()
    episode_of_care.status = "active"

    period_start = random_date_between(
        measurement_end, measurement_end + timedelta(days=365)
    )

    # Create the period
    episode_of_care.period = {
        "start": period_start.isoformat()
        # The 'end' key is not set, assuming the episode is ongoing after the measurement period.
    }

    return episode_of_care


def random_date_between(start_date, end_date):
    """
    Generate a random datetime between start_date and end_date.
    """
    time_between_dates = end_date - start_date
    random_number_of_days = random.randrange(time_between_dates.days)
    random_date = start_date + timedelta(days=random_number_of_days)
    return random_date


def create_transaction_bundle(resources):
    entries = []

    for resource in resources:
        entry = BundleEntry(
            resource=resource,
            request=BundleEntryRequest(method="POST", url=Uri(resource.resource_type)),
        )
        entries.append(entry)

    bundle = Bundle(type="transaction", entry=entries)

    return bundle


# Function to generate a random date of birth
def random_dob(start_year=1920, end_year=2003):
    start = datetime(year=start_year, month=1, day=1)
    end = datetime(year=end_year, month=12, day=31)
    random_date = start + timedelta(days=randint(0, (end - start).days))
    return random_date.isoformat()[:10]


# Generator Fuctions
# These functions are mapped to the features from the list above using the snake_case
# function. They generate FHIR resources based on the input data.
#
# Each function is a passthrough: it takes in a FHIR bundle, makes some modifications,
# and returns the modified bundle.


class FhirGenerator:

    codings = {
        "hiv-positive": {
            "system": "http://snomed.info/sct",
            "code": "38341003",
            "display": "HIV Positive",
        },
        "hiv-negative": {
            "system": "http://snomed.info/sct",
            "code": "165815009",
            "display": "HIV Negative",
        },
        "hiv-test": {
            "system": "http://snomed.info/sct",
            "code": "31676001",
            "display": "HIV Antigen test",
        },
        "hiv-condition": {
            "system": "http://snomed.info/sct",
            "code": "86406008",
            "display": "Human immunodeficiency virus infection",
        },
        "inconclusive": {
            "system": "http://snomed.info/sct",
            "code": "419984006",
            "display": "Inconclusive",
        },
        "presumptive-tb": {
            "system": "http://snomed.info/sct",
            "code": "161920001",
            "display": "Presumptive TB",
        },
        "diagnosed-tb": {
            "system": "http://snomed.info/sct",
            "code": "56717001",
            "display": "Diagnosed TB",
        },
        "self-reported": {
            "system": "http://snomed.info/sct",
            "code": "1156040003",
            "display": "Self reported (qualifier value)",
        },
        "lost-to-follow-up": {
            "system": "http://snomed.info/sct",
            "code": "399307001",
            "display": "Lost to follow-up (finding)",
        },
        "patient-transfer": {
            "system": "http://snomed.info/sct",
            "code": "107724000",
            "display": "Patient transfer (procedure)",
        },
        "death": {
            "system": "http://snomed.info/sct",
            "code": "419620001",
            "display": "Death (event)",
        },
        "patient-non-compliant": {
            "system": "http://snomed.info/sct",
            "code": "413312003",
            "display": "Patient non-compliant - refused service (situation)",
        },
        "key-population": {
            "text": "Key population member",
        },
    }

    def __init__(
        self, all_feature_keys, reporting_period_start_date, reporting_period_end_date
    ):
        self.all_feature_keys = all_feature_keys
        self.reporting_period_start_date = reporting_period_start_date
        self.reporting_period_end_date = reporting_period_end_date

        return

    def generate_for(self, header, row, bundle):
        try:
            # Get the function to call based on the header
            print(f"Generating resource for header '{header}'")
            function = self.get_mapped_function(header)
            return function(row, bundle, header)
        except Exception as e:
            print(f"Error generating resource for header '{header}':\n{e}")
            print(traceback.format_exc())
            return bundle

    def get_mapped_function(self, key):
        if key not in self.all_feature_keys:
            raise Exception(f"Function {function_name} not found for key '{key}'")

        function_name = "generate_" + snake_case(key)

        fn = getattr(self, function_name)

        if callable(fn):
            return fn
        else:
            raise Exception(f"Function {function_name} not found for key '{key}'")

    # See generator_functions.py
    def generate_patient(self, row, bundle, header):
        # Patient-based bundle

        return bundle

    def generate_test(self, row, bundle, header):
        # Service Request-based bundle

        return bundle

    def generate_exclusion_observation(self, row, bundle, header, coding):
        val = row[header]
        my_coding = self.codings[coding]

        if val == "1":
            # Generate observation for the given coding
            observation = generate_observation_resource(
                code=my_coding, patient_id=row["Patient.id"]
            )

            # Add effective datetime
            observation.effectiveDateTime = random_date(
                end=self.reporting_period_end_date
            )

            bundle.entry.append(
                BundleEntry(
                    resource=observation,
                    request=BundleEntryRequest(method="PUT", url=Uri("Observation")),
                )
            )
        else:
            # Do nothing or add observation after reporting period
            if random.choice([True, False]):
                observation = generate_observation_resource(
                    code=my_coding, patient_id=row["Patient.id"]
                )
                observation.effectiveDateTime = random_date(
                    self.reporting_period_end_date,
                    self.reporting_period_end_date + timedelta(days=365),
                )

                bundle.entry.append(
                    BundleEntry(
                        resource=observation,
                        request=BundleEntryRequest(
                            method="PUT", url=Uri("Observation")
                        ),
                    )
                )

        return bundle

    def generate_key_population_member_type(self, row, bundle, header):
        obs_value = row[header]

        bundle.entry.append(
            BundleEntry(
                resource=generate_observation_resource(
                    val=obs_value,
                    code=self.codings["key-population"],
                    patient_id=row["Patient.id"],
                ),
                request=BundleEntryRequest(method="PUT", url=Uri("Observation")),
            )
        )

        return bundle

    def generate_tb_diagnosis_result(self, row, bundle, header):
        obs_value = row[header]

        if obs_value == "Yes":
            condition_resource, bundle = find_or_create_condition_resource(
                bundle, self.codings["diagnosed-tb"]
            )
            update_condition_resource(
                condition_resource,
                row,
                coding=[self.codings["diagnosed-tb"]],
                start_date=self.reporting_period_start_date,
                end_date=self.reporting_period_end_date,
            )

        return bundle

    def generate_presumptive_tb(self, row, bundle, header):
        obs_value = row[header]

        if obs_value == "Yes":
            condition_resource, bundle = find_or_create_condition_resource(
                bundle, self.codings["presumptive-tb"]
            )
            update_condition_resource(
                condition_resource,
                row,
                coding=[self.codings["presumptive-tb"]],
                start_date=self.reporting_period_start_date,
                end_date=self.reporting_period_end_date,
            )
        return bundle

    def generate_testing_entry_point(self, row, bundle, header):
        val = row[header]

        # If value exists, modify the DiagnosticReport or Observation resources

        return bundle

    def generate_self_testing(self, row, bundle, header):
        val = row[header]

        # If value exists, modify the DiagnosticReport or Observation resources
        if val == "Yes":
            test_resources, bundle = find_or_create_test_resources(
                bundle, row, self.codings["hiv-test"]
            )
            observation = test_resources["obs"]
            observation.method = self.codings["self-reported"]

        return bundle

    def generate_hiv_test_result_hiv_positive(self, row, bundle, header):
        # Add / modify condition resource based on value of feature
        test_coding = self.codings["hiv-test"]
        unrelated_coding = CodeableConcept.parse_obj(
            {
                "coding": [
                    {
                        "code": "1234567",
                        "display": "Unrelated",
                    }
                ]
            }
        )
        positive_coding = CodeableConcept.parse_obj(
            {"coding": [self.codings["hiv-positive"]]}
        )
        negative_coding = CodeableConcept.parse_obj(
            {"coding": [self.codings["hiv-negative"]]}
        )
        inconclusive_coding = CodeableConcept.parse_obj(
            {"coding": [self.codings["inconclusive"]]}
        )

        # Search for existing condition resource or create new
        test_resources, bundle = find_or_create_test_resources(bundle, row, test_coding)

        obs = test_resources.get("obs")

        if row[header] == "1":
            obs.valueCodeableConcept = positive_coding
        else:
            # Randomly assign negative, inconclusive or no result
            coding = random.choice(
                [negative_coding, inconclusive_coding, unrelated_coding, None]
            )
            if coding is not None:
                if obs and isinstance(obs, Observation):
                    obs.valueCodeableConcept = coding
                else:
                    raise Exception(
                        "Observation resource does not exist for test result"
                    )
            else:
                # Remove Observation resource
                bundle.entry = [
                    x
                    for x in bundle.entry
                    if x.resource.resource_type != "Observation"
                    or x.resource.id != obs.id
                ]

        return bundle

    def generate_date_hiv_test_results_returned_in_the_reporting_period(
        self, row, bundle, header
    ):
        associated_header = "\"HIV test result\"='HIV-positive'"

        hiv_pos_value = row[associated_header]
        my_value = row[header]

        my_coding = self.codings["hiv-test"]

        if hiv_pos_value == "1":
            # Test resources should exist - update the date based on the value of the feature
            test_resources, bundle = find_or_create_test_resources(
                bundle, row, my_coding
            )

            dr = test_resources["dr"]
            obs = test_resources["obs"]

            if my_value == "1":
                # Date should be in the reporting period
                dr.effectiveDateTime = random_date_between(
                    self.reporting_period_start_date, self.reporting_period_end_date
                ).isoformat()
                obs.effectiveDateTime = dr.effectiveDateTime
            else:
                # Date should be outside the reporting period
                outside_start = self.reporting_period_start_date - timedelta(days=10)
                outside_end = outside_start + timedelta(days=5)
                dr.effectiveDateTime = random_date_between(
                    outside_start, outside_end
                ).isoformat()
                obs.effectiveDateTime = dr.effectiveDateTime

        else:
            # Test resources should not exist - do nothing
            pass
        return bundle

    def generate_hiv_diagnosis_date_in_the_reporting_period(self, row, bundle, header):
        return self.generate_hiv_status_hiv_positive(row, bundle, value=row[header])

    def generate_hiv_test_date_in_the_reporting_period(self, row, bundle, header):
        val = row[header]

        if val == "1":
            test_resources, bundle = find_or_create_test_resources(
                bundle, row, self.codings["hiv-test"]
            )
            sr = test_resources["sr"]
            sr.authoredOn = random_date_between(
                self.reporting_period_start_date, self.reporting_period_end_date
            ).isoformat()
        else:
            if random.choice([True, False]):
                test_resources, bundle = find_or_create_test_resources(
                    bundle, row, self.codings["hiv-test"]
                )
                sr = test_resources["sr"]
                sr.authoredOn = random_date_between(
                    self.reporting_period_start_date - timedelta(days=10),
                    self.reporting_period_end_date,
                ).isoformat()
        return bundle

    def generate_hiv_status_hiv_positive(self, row, bundle, header=None, value=None):
        # Note - qualified by `at the end of the reporting period`

        # Add / modify condition resource based on value of feature
        my_coding = self.codings["hiv-condition"]

        # Determine if creating a new condition
        create_new_condition = random.choice([True, False])
        if header:
            hiv_positive = row[header] and row[header] == "1"
        else:
            hiv_positive = value == "1"

        # Search for existing condition resource or create new
        if create_new_condition or hiv_positive:
            condition_resource, bundle = find_or_create_condition_resource(
                bundle, my_coding
            )
            if hiv_positive:
                update_condition_resource(
                    condition_resource,
                    row,
                    coding=[my_coding],
                    start_date=self.reporting_period_start_date,
                    end_date=self.reporting_period_end_date,
                )
            else:
                update_condition_resource(
                    condition_resource,
                    row,
                    coding=[my_coding],
                    start_date=self.reporting_period_end_date - timedelta(days=10),
                    end_date=self.reporting_period_end_date - timedelta(days=5),
                )
        else:
            # Condition should not exist - do nothing
            pass
        return bundle

    def generate_hiv_treatment_outcome_in_death_documented(self, row, bundle, header):
        val = row[header]
        patient = next(
            (
                x.resource
                for x in bundle.entry
                if x.resource.resource_type == "Patient"
                and x.resource.id == row["Patient.id"]
            ),
            None,
        )

        patient = (
            patient.resource if patient and isinstance(patient, BundleEntry) else None
        )

        if patient:
            if val == "1":
                patient.resource = add_deceased_information(
                    patient.resource, self.reporting_period_end_date
                )
            else:
                if random.choice([True, False]):
                    patient.resource = add_future_deceased_information(
                        patient.resource, self.reporting_period_end_date
                    )

        return bundle

    def generate_on_art_true_at_reporting_period_end_date(self, row, bundle, header):
        val = row[header]

        if val == "1":
            # Generate Episode of Care resource, connect to condition resource, and add
            bundle.entry.append(
                BundleEntry(
                    resource=generate_art_medication_statement_resource(
                        row,
                        self.reporting_period_start_date,
                        self.reporting_period_end_date,
                    ),
                    request=BundleEntryRequest(
                        method="PUT", url=Uri("MedicationStatement")
                    ),
                )
            )
        else:
            # Either do nothing or add medication statement with end date before reporting period
            pass
        return bundle

    def generate_hiv_treatment_outcome_in_transferred_out(self, row, bundle, header):
        # TODO: make more applicable to real-world scenarios by using Encounter resources
        # and other resources to indicate transfer out
        return self.generate_exclusion_observation(
            row, bundle, header, "patient-transfer"
        )

    def generate_hiv_treatment_outcome_in_lost_to_follow_up(self, row, bundle, header):
        # TODO: Make more applicable to real-world scenarios
        return self.generate_exclusion_observation(
            row, bundle, header, "lost-to-follow-up"
        )
