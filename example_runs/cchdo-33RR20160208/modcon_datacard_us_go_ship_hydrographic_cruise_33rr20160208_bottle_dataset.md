---
datacard_info:
  filename: modcon_datacard_us_go_ship_hydrographic_cruise_33rr20160208_bottle_dataset.md
  id:
    type: null
    value: null
  datacard_access: null
  datacard_creation:
    created_date: '2026-09-24'
    update_date: '2026-09-24'
    creation_method: automated
    created_by: []
  datacard_template_version: 1.0
  language: en
data_identifiers:
  name: 'US GO-SHIP Hydrographic Cruise 33RR20160208: Bottle Dataset'
  dataset_id:
    type: DOI
    value: 10.7942/C2H59N
title: 'US GO-SHIP Hydrographic Cruise 33RR20160208: Bottle Dataset'
id: 10.7942/C2H59N
project: null
identifiers:
- type: DOI
  value: 10.7942/C2H59N
dataset_info:
  modalities:
  - time-series
  data_formats:
  - application/x-netcdf
  features:
  - time
  - latitude
  - longitude
  - btm_depth
  - pressure
  - ctd_temperature
  - ctd_salinity
  - bottle_salinity
  - ctd_oxygen
  - oxygen
  - silicate
  - nitrate
  - nitrite
  - phosphate
  - cfc_11
  - total_carbon
  - ph_total_h_scale
  - ph_temperature
  - ref_temperature_c
  - cdom
  - chlorophyll_a
  - bottle_time
  - bottle_latitude
  - bottle_longitude
  - CDOM_WAVELENGTHS
  - package_depth
  splits: []
  dataobject_type: dataset
  dataset_type: ND
dataset_readiness:
  level: null
  evaluated_against: Genesis Dataset Readiness Model v1.0
  evaluated_at: null
  evaluated_by: null
  confidence: null
release_status: null
review_process:
  review_purpose: null
  review_status: null
  review_institution:
    name: null
    ror_id: null
  review_comments: null
contact_point: null
additional_contacts: []
access_policy:
  sensitivity_tier: tier0_openScience
  access_level: open
  authorization: none
  policy_url: https://learning.cchdo.io/policies_and_procedures/data_license.html
  policy_text: CCHDO assumes CC0 unless the submitter requested CC BY. This cruise page does not state which applies.
cui_markings: null
distribution_statement: null
handling_instructions: null
security_marking:
  classification: unclassified
  cui_marking: null
  distribution_statement: null
  handling_instructions: null
  declassification:
    review_date: null
    authority: null
license:
  spdx_id: null
  name: null
  link: null
additional_licenses: []
categorization:
  science_domain: climate
  modalities:
  - time-series
  task_category: []
  task_subcategory: []
originating_research_organization: null
facilities: []
fundings: null
dataset_authors:
- entity:
    type: person
    person:
      given_name: Alison
      family_name: Macdonald
      orcid: null
      email: null
      affiliation: null
  role: creator
dataset_contributors: []
stewardship:
  level: null
maintenance:
  update_frequency: null
dataset_provenance:
  was_generated_by: CCHDO schema.org JSON-LD embedded in the cruise landing page
  source_data: https://cchdo.ucsd.edu/cruise/33RR20160208#bottle
  processing_steps: GO-SHIP hydrographic bottle (discrete sample) observations
  instrumentation: null
  simulation_details: null
related_resources:
  related_datasets:
  - https://doi.org/10.7284/906584
  publications:
    dois:
    - 10.7284/906584
    arxiv: []
    urls: []
  software: null
  aimodels: []
dates:
  data_collection_start: '2016-02-19'
  data_collection_end: '2016-03-11'
  issued: '2026-09-24'
  modified: '2026-09-24'
semantic_layer:
  schema_url: http://vocab.nerc.ac.uk/standard_name/
  ontology_alignment: []
  semantic_context: []
  controlled_vocabularies:
  - CF standard names (http://vocab.nerc.ac.uk/standard_name/); distributions named cf_netcdf, exchange, whp_netcdf, woce
data_quality:
  completeness: null
  known_issues: null
  validation_methods: null
  noise_characteristics: null
  uncertainty_notes: null
integrity:
  checksum_available: false
  checksum_type: null
  fixity_policy: null
  versioning_strategy: null
ai_usage:
  ai_ready: true
  training_use_allowed: true
  inference_use_allowed: true
  restrictions: null
  bias_risks: null
  safety_considerations: null
  human_review_required: false
dataset_counts:
  value: null
  category: timesteps
  unit: null
dataset_storage:
  compressed_bytes: null
  unpacked_bytes: null
repository_access:
  populated_by_repository: true
  distributions:
  - name: exchange
    encodingFormat: text/csv
    contentUrl: https://cchdo.ucsd.edu/data/27121/33RR20160208_hy1.csv
    contentSize: 1899562 bytes
  - name: whp_netcdf
    encodingFormat: application/zip
    contentUrl: https://cchdo.ucsd.edu/data/27122/33RR20160208_nc_hyd.zip
    contentSize: 888130 bytes
  - name: woce
    encodingFormat: text/plain
    contentUrl: https://cchdo.ucsd.edu/data/27123/33RR20160208hy.txt
    contentSize: 701952 bytes
  - name: cf_netcdf
    encodingFormat: application/x-netcdf
    contentUrl: https://cchdo.ucsd.edu/data/38395/33RR20160208_bottle.nc
    contentSize: 842156 bytes
  data_services: []
---

# Datacard for US GO-SHIP Hydrographic Cruise 33RR20160208: Bottle Dataset
**Last Updated**: 2026-09-24

**Dataset Readiness Level:** [!TODO]

### Machine Usability Snapshot
| Aspect | Status |
|--------|--------|
| AI Ready | Yes |
| License Clarity | No |
| Machine Access | Yes (HTTPS, no authentication on the cruise page) |
| Checksum / Fixity | No |
| Semantic Context | Yes |


# ---- Level 1: Discoverable ----
---
## Identification

### Files & Structure
Four downloadable encodings of the same bottle dataset, listed on the cruise page. They are alternate formats, not a summed archive. Row count is not in the JSON-LD record.

- cf_netcdf: `33RR20160208_bottle.nc` (application/x-netcdf, 842156 bytes, updated 2023-07-24) https://cchdo.ucsd.edu/data/38395/33RR20160208_bottle.nc
- exchange: `33RR20160208_hy1.csv` (text/csv, 1899562 bytes, updated 2022-07-06) https://cchdo.ucsd.edu/data/27121/33RR20160208_hy1.csv
- whp_netcdf: `33RR20160208_nc_hyd.zip` (application/zip, 888130 bytes, updated 2022-07-06) https://cchdo.ucsd.edu/data/27122/33RR20160208_nc_hyd.zip
- woce: `33RR20160208hy.txt` (text/plain, 701952 bytes, updated 2022-07-06) https://cchdo.ucsd.edu/data/27123/33RR20160208hy.txt

Format: application/x-netcdf (CF-NetCDF distribution). Columns: 26. Time range in the JSON-LD record: 2016-02-19 to 2016-03-11. Cruise-page Date Start/End: 2016-02-08 to 2016-03-16. Ship: ROGER REVELLE.

---
## Description

### Dataset Description [required]
Bottle (discrete sample) data from the hydrographic cruise 33RR20160208 Temporal coverage in the JSON-LD record is 2016-02-19/2016-03-11. The cruise page lists Date Start/End 2016-02-08/2016-03-16, ship ROGER REVELLE, country US.

### Keywords [strongly recommended]
ROGER REVELLE, ctd, bottle, Jonathan Nash, Alison Macdonald, USHYDRO, southern, SOCCOM, I08S, GO-SHIP, indian

### Citation
CCHDO file-header guidance on this cruise (AGU-style template, not a separate minted citation string): data provider(s), cruise name or cruise ID, data file name(s), CLIVAR and Carbon Hydrographic Data Office, La Jolla, CA, USA, and data file date. Users are also requested to acknowledge the NSF/NOAA-funded U.S. Repeat Hydrography Program.

Filled from fields on the page: Alison Macdonald; cruise 33RR20160208; 33RR20160208_bottle.nc (updated 2023-07-24); CLIVAR and Carbon Hydrographic Data Office, La Jolla, CA, USA. DOI: 10.7942/C2H59N.

---

# ---- Level 2: Interoperable and Reusable ----

### Sharing & Access
Open HTTPS downloads from https://cchdo.ucsd.edu/cruise/33RR20160208. JSON-LD `isAccessibleForFree` is true. No authentication is described on the cruise page.

### Security / Marking Considerations
Classification: unclassified. Distribution: [!TODO]

---
### Access and Permissions
Access level: open. License: [!TODO]. Authorization: none required.

### Access conditions
No license is stated on this cruise page or in the JSON-LD. CCHDO policy (https://learning.cchdo.io/policies_and_procedures/data_license.html) assumes CC0 unless the submitter requested CC BY. That assumption was not written as this dataset's SPDX license.

### Release review process
[!TODO]

---
## Context

### Domain and Purpose
Domain: climate (SetGo domain used for CF/ACDD; the cruise page itself says GO-SHIP hydrography, line I08S).

Bottle (discrete sample) observations from US GO-SHIP cruise 33RR20160208.

### Resources used, including funding and facilities, to create the dataset
Ship: ROGER REVELLE. The cruise page asks users to acknowledge the NSF/NOAA-funded U.S. Repeat Hydrography Program. Award numbers, facility ROR IDs, and a funder ROR are not on the record.

---
## Provenance

### Developed by
Alison Macdonald

### Contributed by
Publisher: CCHDO (https://cchdo.ucsd.edu). Keywords on the cruise record also name Jonathan Nash; role is not stated, so that name is not listed as an author.

---
## Related Resources

### Related datasets, standards, metadata, and ontologies
Controlled vocabulary: CF standard names (http://vocab.nerc.ac.uk/standard_name/). Distributions named cf_netcdf, exchange, whp_netcdf, woce. Related R2R cruise DOI: https://doi.org/10.7284/906584 (RR1602).

### Related publications
[!TODO]

### Related software
SetGo (https://github.com/ORNL/setgo) generated this card from the CCHDO cruise-page JSON-LD. It did not process the bottle measurements.

### Related ai model
[!TODO]

---
## Methods

### Dataset generation, collection, and procedures
Source data: https://cchdo.ucsd.edu/cruise/33RR20160208#bottle. Processed by CCHDO schema.org JSON-LD embedded in the cruise landing page. GO-SHIP hydrographic bottle (discrete sample) observations

### Maintenance & Updates
[!TODO]


# ---- Level 3: Understandable & Trustworthy ----

### Data Characteristics
| Variable Name | Description | Unit | Value Labels |
|---------------|-------------|------|--------------|
| time | time | not stated | N/A |
| latitude | latitude | degree_north | N/A |
| longitude | longitude | degree_east | N/A |
| btm_depth | sea_floor_depth_below_sea_surface | meters | N/A |
| pressure | sea_water_pressure | dbar | N/A |
| ctd_temperature | sea_water_temperature | degC | N/A |
| ctd_salinity | sea_water_practical_salinity | 1 | N/A |
| bottle_salinity | sea_water_practical_salinity | 1 | N/A |
| ctd_oxygen | moles_of_oxygen_per_unit_mass_in_sea_water | umol/kg | N/A |
| oxygen | moles_of_oxygen_per_unit_mass_in_sea_water | umol/kg | N/A |
| silicate | moles_of_silicate_per_unit_mass_in_sea_water | umol/kg | N/A |
| nitrate | moles_of_nitrate_per_unit_mass_in_sea_water | umol/kg | N/A |
| nitrite | moles_of_nitrite_per_unit_mass_in_sea_water | umol/kg | N/A |
| phosphate | moles_of_phosphate_per_unit_mass_in_sea_water | umol/kg | N/A |
| cfc_11 | moles_of_cfc11_per_unit_mass_in_sea_water | pmol/kg | N/A |
| total_carbon | moles_of_dissolved_inorganic_carbon_per_unit_mass_in_sea_water | umol/kg | N/A |
| ph_total_h_scale | sea_water_ph_reported_on_total_scale | 1 | N/A |
| ph_temperature | temperature_of_analysis_of_sea_water | degC | N/A |
| ref_temperature_c | sea_water_temperature | degC | N/A |
| cdom | volume_beam_attenuation_coefficient_of_radiative_flux_in_sea_water | m^-1 | N/A |
| chlorophyll_a | mass_concentration_of_chlorophyll_a_in_sea_water | ug/l | N/A |
| bottle_time | time | not stated | N/A |
| bottle_latitude | latitude | degree_north | N/A |
| bottle_longitude | longitude | degree_east | N/A |
| CDOM_WAVELENGTHS | radiation_wavelength | nm | N/A |
| package_depth | depth | meters | N/A |


### Data Quality & Limitations
[!TODO]

### Related Schemas or Ontologies
CF standard names (http://vocab.nerc.ac.uk/standard_name/); distributions named cf_netcdf, exchange, whp_netcdf, woce

### List of variable name(s), description(s), unit(s), and value labels for each variable in the dataset/file.
| Variable Name | Description | Unit | Value Labels |
|---------------|-------------|------|--------------|
| time | time | not stated | N/A |
| latitude | latitude | degree_north | N/A |
| longitude | longitude | degree_east | N/A |
| btm_depth | sea_floor_depth_below_sea_surface | meters | N/A |
| pressure | sea_water_pressure | dbar | N/A |
| ctd_temperature | sea_water_temperature | degC | N/A |
| ctd_salinity | sea_water_practical_salinity | 1 | N/A |
| bottle_salinity | sea_water_practical_salinity | 1 | N/A |
| ctd_oxygen | moles_of_oxygen_per_unit_mass_in_sea_water | umol/kg | N/A |
| oxygen | moles_of_oxygen_per_unit_mass_in_sea_water | umol/kg | N/A |
| silicate | moles_of_silicate_per_unit_mass_in_sea_water | umol/kg | N/A |
| nitrate | moles_of_nitrate_per_unit_mass_in_sea_water | umol/kg | N/A |
| nitrite | moles_of_nitrite_per_unit_mass_in_sea_water | umol/kg | N/A |
| phosphate | moles_of_phosphate_per_unit_mass_in_sea_water | umol/kg | N/A |
| cfc_11 | moles_of_cfc11_per_unit_mass_in_sea_water | pmol/kg | N/A |
| total_carbon | moles_of_dissolved_inorganic_carbon_per_unit_mass_in_sea_water | umol/kg | N/A |
| ph_total_h_scale | sea_water_ph_reported_on_total_scale | 1 | N/A |
| ph_temperature | temperature_of_analysis_of_sea_water | degC | N/A |
| ref_temperature_c | sea_water_temperature | degC | N/A |
| cdom | volume_beam_attenuation_coefficient_of_radiative_flux_in_sea_water | m^-1 | N/A |
| chlorophyll_a | mass_concentration_of_chlorophyll_a_in_sea_water | ug/l | N/A |
| bottle_time | time | not stated | N/A |
| bottle_latitude | latitude | degree_north | N/A |
| bottle_longitude | longitude | degree_east | N/A |
| CDOM_WAVELENGTHS | radiation_wavelength | nm | N/A |
| package_depth | depth | meters | N/A |


### Codes used for missing data
[!TODO]

### Specialized formats or other abbreviations used
[!TODO]

### Example of the contents
[!TODO]

### Data Processing
GO-SHIP hydrographic bottle (discrete sample) observations

### Software used to preprocess/ clean/ label the data
Not stated on the metadata record. Cruise history notes mention the `hydro` package for file conversion; a single version was not taken from that log. SetGo only generated this card.

## Integrity & Versioning
Checksums: not yet generated. [!TODO]

## Semantic / Schema Information
CF standard names (http://vocab.nerc.ac.uk/standard_name/); distributions named cf_netcdf, exchange, whp_netcdf, woce

## AI / Machine Learning Considerations
AI-ready: Yes. Training use allowed: Yes. Inference use allowed: Yes.
Bias risks: [!TODO]. Safety considerations: [!TODO].

---

## Additional Information
Card dates `issued` and `modified` (2026-09-24) are the SetGo generation date, not CCHDO file dates. File update dates are in Files & Structure. License, ORCID, affiliation, award numbers, checksums, and row count remain unknown. A 2016 processing note on the page said the files were preliminary; later file updates exist (bottle NetCDF updated 2023-07-24), so that note is not treated as the current release status.

---
