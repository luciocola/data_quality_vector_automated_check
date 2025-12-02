# UMM STAC Liability/Claims Converter Plugin

## Overview

This QGIS plugin enables bidirectional conversion between NASA's Unified Metadata Model (UMM) and STAC (SpatioTemporal Asset Catalog) with the liability-claims extension.

## Features

- **Import UMM to STAC**: Convert NASA UMM data format to STAC Items/Collections with liability-claims extension
- **Export STAC to UMM**: Convert STAC Items/Collections to NASA UMM format
- **Liability/Claims Extension Support**: Full support for liability and claims metadata fields (liability:*)
- **Quality Information Support**: Converts UMM DataQuality to/from ISO 19115-like quality reports in STAC
- **Batch Processing**: Process multiple files at once
- **Validation**: Validate converted data against schemas

## Installation

1. Copy the plugin folder to your QGIS plugins directory
2. Enable the plugin in QGIS Plugin Manager
3. Access via Plugins menu or toolbar icon

## Usage

### Import UMM to STAC

1. Open the plugin dialog
2. Select "UMM to STAC" conversion mode
3. Choose input UMM file(s)
4. Specify output directory
5. Configure liability-claims extension options
6. Click "Convert"

### Export STAC to UMM

1. Open the plugin dialog
2. Select "STAC to UMM" conversion mode
3. Choose input STAC file(s)
4. Specify output directory
5. Click "Convert"

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
