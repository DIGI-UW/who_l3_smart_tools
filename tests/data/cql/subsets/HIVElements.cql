library HIVElements

using FHIR version '4.0.1'

//include fhir.cqf.common.FHIRCommon called FC
include FHIRHelpers version '4.0.1'

include WHOConcepts
include WHOCommon called WC
include WHOElements called WE

include HIVConcepts version '0.0.2' called Concepts
include HIVConceptsCustom version '0.0.1' called ConceptsCustom
include HIVCommon called Common

context Patient

/**
 * HIV Elements
 */

/* General Element Definitions */

// From Common

// Exposure to HIV

// ...subset definitions...
define "HIV test":
  [Observation: Concepts."HIV test type - HIV.B.DE81 Choices"] O
  where O.status in { 'final', 'amended', 'corrected' }

define "HIV Status Positive Observation":
"HIV Status Observation" O
    where O.value ~ Concepts."HIV-positive - HIV.B.DE116"
      sort by start of effective.toInterval()

define "HIV Status Observation":
  [Observation: Concepts."HIV status"] O
    where O.status in { 'final', 'amended', 'corrected' }

/*
@dataElement: HIV.B.DE116 - HIV-positive
@activity: HIV.B7 Test for HIV using testing algorithm
@description: Client is HIV-positive
*/

define "TB excluded":
  "TB diagnosis result" O
    where O.status in { 'final', 'amended', 'corrected' }
      and O.value ~ Concepts."TB excluded"
/* End of TB excluded */

/*
@dataElement: HIV.D.DE945 - Presumptive TB
@activity: HIV.D8 Capture or update client history
@description: Client has signs or symptoms of tuberculosis (TB) without laboratory confirmation
*/

define "TB diagnosis result":
  [Observation: Concepts."TB diagnosis result"] O
    where O.status in { 'final', 'amended', 'corrected' }
/* End of TB diagnosis result */

/*
@dataElement: HIV.D.DE940 - Diagnosed TB
@activity: HIV.D8 Capture or update client history
@description: Client is diagnosed with TB disease
*/

define "Presumptive TB D.DE945":
  "TB diagnosis result" O
    where O.status in { 'final', 'amended', 'corrected' }
      and O.value ~ Concepts."Presumptive TB - HIV.D.DE945"
/* End of Presumptive TB D.DE945 */

/*
@dataElement: HIV.D.DE952 - Date of TB diagnosis
@activity: HIV.D8 Capture or update client history
@description: The date when the diagnosis was established
*/

define "Diagnosed TB":
  "TB diagnosis result" O
    where O.status in { 'final', 'amended', 'corrected' }
      and O.value ~ Concepts."Diagnosed TB"
/* End of Diagnosed TB */

/*
@dataElement: HIV.D.DE941 - TB excluded
@activity: HIV.D8 Capture or update client history
@description: Client is not diagnosed with TB
*/

define "Key population member type Observation":
  [Observation: Concepts."Key population member - HIV.B.DE49"] O
    where O.status in { 'final', 'amended', 'corrected' }
    and exists(O.category OC where OC ~ ConceptsCustom."social-history")
/* End of Key population member type B.DE50 */

/*
@dataElement: HIV.B.DE51 - Sex worker
@activity: HIV.B6 Capture or update client history
@description: Client is a sex worker
*/

define "HIV Status Positive Condition":
  [Condition: Concepts."HIV-positive - HIV.B.DE116"] C
    where C.clinicalStatus ~ ConceptsCustom."active"
      and exists(C.category CC where CC ~ ConceptsCustom."encounter-diagnosis")
    sort by start of onset.toInterval()

define "Facility-level testing Observation":
  "Testing entry point Observation" O
    where O.status in { 'final', 'amended', 'corrected' }
      and O.value ~ Concepts."Facility-level testing"
/* End of Facility-level testing */

/*
@dataElement: HIV.B.DE29 - Currently pregnant
@activity: HIV.B6 Capture or update client history
@description: Client is currently pregnant
*/

define "Facility-level testing":
  exists "Facility-level testing Condition"
    or exists "Facility-level testing Observation"

define "Facility-level testing Condition":
  [Condition: Concepts."Facility-level testing"]

define "Testing entry point Observation":
  [Observation: Concepts."Testing entry point"] O
    where O.status in { 'final', 'amended', 'corrected' }
/* End of Testing entry point */

/*
@dataElement: HIV.B.DE16 - Community-level testing
@activity: HIV.B1 Determine reason for visit
@description: Testing is happening in the community, which includes mobile testing
*/
// TODO: Replace placeholder with relevant CQL logic

define "Testing entry point":
  exists "Testing entry point Observation"

define "Community-level testing Observation":
  "Testing entry point Observation" O
    where O.status in { 'final', 'amended', 'corrected' }
      and O.value ~ Concepts."Community-level testing"
/* End of Community-level testing */

/*
@dataElement: HIV.B.DE17 - Facility-level testing
@activity: HIV.B1 Determine reason for visit
@description: Testing is happening at a facility
*/
// TODO: Replace placeholder with relevant CQL logic

define "Community-level testing":
  exists "Community-level testing Condition"
    or exists "Community-level testing Observation"

define "Community-level testing Condition":
  [Condition: Concepts."Community-level testing"]