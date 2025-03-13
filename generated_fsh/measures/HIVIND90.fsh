Instance: HIVIND90
InstanceOf: http://hl7.org/fhir/us/cqfmeasures/StructureDefinition/proportion-measure-cqfm
Title: "HIV.IND.90 HBV treatment among people living with HIV"
* meta.profile[+] = "http://hl7.org/fhir/uv/crmi/StructureDefinition/crmi-shareablemeasure"
* meta.profile[+] = "http://hl7.org/fhir/uv/crmi/StructureDefinition/crmi-publishablemeasure"
* extension[http://hl7.org/fhir/us/cqfmeasures/StructureDefinition/cqfm-populationBasis].valueCode = #boolean
* description = "% of people living with HIV and diagnosed with HBV infection who are on TDF-based ART"
* url = "http://smart.who.int/hiv/Measure/HIVIND90"
* status = #draft
* experimental = true
* date = "2025-03-13"
* name = "HIVIND90"
* title = "HIV.IND.90 HBV treatment among people living with HIV"
* publisher = "World Health Organization (WHO)"
* library = "http://smart.who.int/hiv/Library/HIVIND90Logic"
* scoring = $measure-scoring#proportion "Proportion"
* group[+]
  * population[initialPopulation]
    * id = "HIV.IND.90.IP"
    * description = "Initial Population"
    * code = $measure-population#initial-population "Initial Population"
    * criteria.language = #text/cql-identifier
    * criteria.expression = "Initial Population"
  * population[denominator]
    * id = "HIV.IND.90.DEN"
    * description = "Number of people living with HIV who were diagnosed with HBV"
    * code = $measure-population#denominator "Denominator"
    * criteria.language = #text/cql-identifier
    * criteria.expression = "Denominator"
  * population[numerator]
    * id = "HIV.IND.90.NUM"
    * description = "Number of people newly started on HBV treatment (TDF) during the reporting period  | plus | Number of people living with HIV who are already on TDF-based ART"
    * code = $measure-population#numerator "Numerator"
    * criteria.language = #text/cql-identifier
    * criteria.expression = "Numerator"
  * stratifier[+]
    * id = "HIV.IND.90.S"
    * criteria.language = #text/cql-identifier
    * criteria.expression = "Stratification"