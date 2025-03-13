library HIVIndicatorElements

using FHIR version '4.0.1'

//include fhir.cqf.common.FHIRCommon called FC
include FHIRHelpers version '4.0.1'

include WHOConcepts
include WHOCommon called WC
include WHOElements called WE

include HIVConcepts version '0.0.2' called Concepts
include HIVConceptsCustom version '0.0.1' called ConceptsCustom
include HIVElements called Elements
include HIVCommon called Common
include HIVConfig called Config

parameter "Measurement Period" Interval<Date> default Interval[@2024-01-01, @2024-12-30]

context Patient

/**
 * HIV Elements
 */

/* General Data Elements */

// From Common


// ...subset definitions...
define "HIV test results returned in measurement period":
  Elements."HIV test" O
   where O.issued during "Measurement Period"

define "By Age Stratifier":
  case 
      when "Age In Years" <= 4 then '0-4'
      when "Age In Years" <= 9 then '5-9'
      when "Age In Years" <= 14 then '10–14'
      when "Age In Years" <= 19 then '15–19'
      when "Age In Years" <= 24 then '20–24'
      when "Age In Years" <= 29 then '25–29'
      when "Age In Years" <= 34 then '30–34'
      when "Age In Years" <= 39 then '35–39'
      when "Age In Years" <= 44 then '40–44'
      when "Age In Years" <= 49 then '45–49'
      when "Age In Years" >= 50 then '50+'
      else null
  end
  
  /*
 * By Age Stratifiers
 * Age (0–4, 5–9, 10–14, 15–19, 20–24, 25–49, 50+ years)
 * 
 */

define "Age In Years":
  AgeInYearsAt(start of "Measurement Period")

define "HIV Status Positive Observation":
  Elements."HIV Status Positive Observation" O
  where O.issued before end of "Measurement Period"
  or O.effective.toInterval() starts before end of "Measurement Period"

define "By Geographic Region Stratifier":
    First(Patient.address A where A.use in { 'home' }).state

/*
 * Other Stratifiers
 */

define tb:
  case 
      when "Diagnosed TB"  then Concepts."Diagnosed TB"
      when "Presumptive TB D.DE945" then Concepts."Presumptive TB - HIV.D.DE945"
      when "TB excluded" then Concepts."TB excluded"
      else null
  end

define "TB excluded":
  exists Elements."TB excluded" O
    where O.effective.toInterval() during "Measurement Period"
/* End of TB excluded */

/*
@dataElement: HIV.D.DE945 - Presumptive TB
@activity: HIV.D8 Capture or update client history
@description: Client has signs or symptoms of tuberculosis (TB) without laboratory confirmation
*/

define "Presumptive TB D.DE945":
  exists Elements."Presumptive TB D.DE945" O
    where O.effective.toInterval() during "Measurement Period"
/* End of Presumptive TB D.DE945 */

/*
@dataElement: HIV.D.DE952 - Date of TB diagnosis
@activity: HIV.D8 Capture or update client history
@description: The date when the diagnosis was established
*/

define "Diagnosed TB":
  exists Elements."Diagnosed TB" O
    where O.effective.toInterval() during "Measurement Period"
/* End of Diagnosed TB */

/*
@dataElement: HIV.D.DE941 - TB excluded
@activity: HIV.D8 Capture or update client history
@description: Client is not diagnosed with TB
*/

define patientGroups:
  "Key population member type Observation" O
  return Combine(O.code.coding.code, ':')
/* End of Key population member type B.DE50 */

/*
@dataElement: HIV.B.DE51 - Sex worker
@activity: HIV.B6 Capture or update client history
@description: Client is a sex worker
*/

define "Key population member type Observation":
  Elements."Key population member type Observation" O
    where O.effective.toInterval() before end of "Measurement Period"
    or O.issued before end of "Measurement Period"

// Stratifier

define "HIV Status Positive Condition":
  Elements."HIV Status Positive Condition" C
  where C.onset before end of "Measurement Period"

define "By Administrative Gender Stratifier":
  case 
      when Patient.gender = 'male' then Concepts."Male"
      when Patient.gender = 'female' then Concepts."Female"
      when Patient.gender = 'transgender female' then Concepts."Transgender female"
      when Patient.gender = 'transgender male' then Concepts."Transgender male"
      else Concepts."Other - HIV.A.DE23"
  end

/*
@dataElement: HIV.B.DE5 - Referred through partner services
@activity: HIV.B1 Determine reason for visit
@description: Client reported coming to the facility after receiving a provider-assisted referral or patient referral from a contact or partner
*/
// TODO: Replace placeholder with relevant CQL logic

define setting:
  case
    when Community_testing then Concepts."Community-level testing"
    when Facility_testing then Concepts."Facility-level testing"
    else null
  end

define "Facility-level testing":
  exists "Facility-level testing Condition"
    or exists "Facility-level testing Observation"

define "Facility-level testing Observation":
  Elements."Facility-level testing Observation" O
    where O.effective.toInterval() during "Measurement Period"
/* End of Facility-level testing */

/*
@dataElement: HIV.B.DE29 - Currently pregnant
@activity: HIV.B6 Capture or update client history
@description: Client is currently pregnant
*/

define "Facility-level testing Condition":
  Elements."Facility-level testing Condition" C
    where C.prevalenceInterval() overlaps "Measurement Period"

define "Community-level testing":
  exists "Community-level testing Condition"
    or exists "Community-level testing Observation"

define "Community-level testing Observation":
  Elements."Community-level testing Observation" O
    where O.effective.toInterval() during "Measurement Period"
/* End of Community-level testing */

/*
@dataElement: HIV.B.DE17 - Facility-level testing
@activity: HIV.B1 Determine reason for visit
@description: Testing is happening at a facility
*/
// TODO: Replace placeholder with relevant CQL logic

define "Community-level testing Condition":
  Elements."Community-level testing Condition" C
    where C.prevalenceInterval() overlaps "Measurement Period"