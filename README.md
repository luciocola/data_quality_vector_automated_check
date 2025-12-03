# UMM STAC DQ4EO Converter Plugin

## Overview

This QGIS plugin enables bidirectional conversion between multiple geospatial metadata formats:
- **UMM** (NASA's Unified Metadata Model)
- **STAC** (SpatioTemporal Asset Catalog) with liability-claims extension
- **DQ4EO** (Data Quality for Earth Observation) - ISO 19115/19157-based quality reports

## Features

- **UMM ↔ STAC**: Convert between NASA UMM and STAC Items/Collections with liability-claims extension
- **UMM ↔ DQ4EO**: Convert between UMM and DQ4EO quality-focused metadata
- **Liability/Claims Extension Support**: Full support for liability and claims metadata fields (liability:*)
- **Quality Information Support**: Comprehensive ISO 19115/19157 quality reporting
- **Batch Processing**: Process multiple files at once
- **Validation**: Validate converted data against schemas

## Conversion Modes

### 1. UMM to STAC
Convert NASA UMM data format to STAC Items/Collections with liability-claims extension

### 2. STAC to UMM
Convert STAC Items/Collections to NASA UMM format

### 3. UMM to DQ4EO (NEW!)
Convert UMM metadata to DQ4EO quality reports with comprehensive quality elements

### 4. DQ4EO to UMM (NEW!)
Convert DQ4EO quality reports back to UMM metadata format

## Installation

1. Copy the plugin folder to your QGIS plugins directory
2. Enable the plugin in QGIS Plugin Manager
3. Access via Plugins menu or toolbar icon

## Usage

### Convert UMM to STAC

1. Open the plugin dialog
2. Select "UMM to STAC" conversion mode
3. Choose conversion type (Item/Granule or Collection)
4. Select input UMM file(s)
5. Specify output directory
6. Click "Convert"

### Convert STAC to UMM

1. Open the plugin dialog
2. Select "STAC to UMM" conversion mode
3. Choose conversion type (Item/Granule or Collection)
4. Select input STAC file(s)
5. Specify output directory
6. Click "Convert"

### Convert UMM to DQ4EO

1. Open the plugin dialog
2. Select "UMM to DQ4EO" conversion mode
3. Choose conversion type (Item/Granule or Collection)
4. Select input UMM file(s)
5. Specify output directory
6. Click "Convert"

### Convert DQ4EO to UMM

1. Open the plugin dialog
2. Select "DQ4EO to UMM" conversion mode
3. Choose conversion type (Item/Granule or Collection)
4. Select input DQ4EO file(s)
5. Specify output directory
6. Click "Convert"

## DQ4EO Format

DQ4EO (Data Quality for Earth Observation) is a quality-focused metadata format based on ISO 19115/19157 standards. It provides comprehensive quality reporting for Earth observation data.

For detailed information about DQ4EO conversion, see [DQ4EO_CONVERSION.md](DQ4EO_CONVERSION.md).

### DQ4EO Quality Elements

- DQ_CompletenessCommission
- DQ_AbsoluteExternalPositionalAccuracy
- DQ_ProcessingLevel
- DQ_RadiometricAccuracy
- DQ_CloudCoverage
- DQ_ThematicClassificationCorrectness
- DQ_TemporalValidity
- DQ_UsabilityElement
- DQ_Lineage

## UMM Format

NASA's Unified Metadata Model (UMM) is a standardized metadata format used across NASA's Earth Observing System Data and Information System (EOSDIS).

### UMM Quality Information

The converter extracts and converts UMM DataQuality fields including:
- **Lineage**: Processing history and data sources
- **HorizontalPositionalAccuracy**: Horizontal accuracy measurements
- **VerticalPositionalAccuracy**: Vertical/elevation accuracy measurements  
- **CompletenessReport**: Dataset completeness information
- **QualityFlag**: Overall quality indicators

## STAC Liability/Claims Extension

The STAC extension for liability and claims includes fields for:
- Liability information (responsible_party, claim_status, claim_id, etc.)
- Claim tracking (claim_date, claim_type, resolution_status, etc.)
- Legal metadata (legal_jurisdiction, insurance_provider, policy_number, etc.)
- Geographic coverage (coverage_area, affected_parties, etc.)
- Compliance data (evidence_refs, notes, origin, etc.)
- **Quality information** (ISO 19115-based quality reports in liability:quality field)

## Quality Data Conversion

### UMM to STAC Quality Mapping

UMM DataQuality fields are converted to ISO 19115-like quality reports in the `liability:quality` field:

- `UMM.DataQuality.Lineage` → `liability:quality.elements[].elementType: "lineage"`
- `UMM.DataQuality.HorizontalPositionalAccuracy` → `liability:quality.elements[].elementType: "positionalAccuracy"`
- `UMM.DataQuality.VerticalPositionalAccuracy` → `liability:quality.elements[].elementType: "positionalAccuracy"`
- `UMM.DataQuality.CompletenessReport` → `liability:quality.elements[].elementType: "completeness"`

### STAC to UMM Quality Mapping

STAC `liability:quality` reports are converted back to UMM DataQuality fields:

- Quality elements with `elementType: "lineage"` → `UMM.DataQuality.Lineage`
- Quality elements with `elementType: "positionalAccuracy"` → `UMM.DataQuality.HorizontalPositionalAccuracy` or `VerticalPositionalAccuracy`
- Quality elements with `elementType: "completeness"` → `UMM.DataQuality.CompletenessReport`

## Requirements

- QGIS 3.0 or higher
- Python 3.6+

## License

See LICENSE file for details.

## Author

Lucio Colaiacomo

## Support

For issues and feature requests, please visit:
https://github.com/luciocola/qgisplugin4cop/issues
