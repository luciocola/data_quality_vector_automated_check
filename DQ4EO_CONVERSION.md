# DQ4EO Conversion Support

## Overview

The UMM STAC Converter Plugin now supports bidirectional conversion between NASA's Unified Metadata Model (UMM) and DQ4EO (Data Quality for Earth Observation) format.

DQ4EO is a quality-focused metadata format based on ISO 19115/19157 standards, designed to capture comprehensive quality information for Earth observation data.

## Features

### UMM to DQ4EO Conversion

Converts UMM Granule or Collection metadata to DQ4EO quality reports, extracting and transforming:

- **Spatial Extent**: Geographic bounding boxes
- **Temporal Extent**: Time ranges or single timestamps
- **Quality Elements**: 
  - Completeness (from UMM DataQuality)
  - Processing level information
  - Temporal validity
  - Custom quality metrics
- **Lineage**: Processing history and provenance
  - Process steps from ProviderDates
  - Processing level descriptions
  - Data production information

### DQ4EO to UMM Conversion

Converts DQ4EO quality reports back to UMM format, preserving:

- **Granule/Collection Identification**: Resource IDs and titles
- **Spatial Coverage**: Geographic extents
- **Temporal Information**: Date ranges and timestamps
- **Data Quality**: Completeness and quality flags
- **Lineage**: Processing statements and history

## DQ4EO Format Structure

### Quality Report Structure

```json
{
  "type": "DQ4EO-QualityReport",
  "version": "1.0.0",
  "reportId": "unique-report-identifier",
  "scope": {
    "level": "dataset|series",
    "extent": {
      "geographic": {
        "westBoundLongitude": -180,
        "eastBoundLongitude": 180,
        "southBoundLatitude": -90,
        "northBoundLatitude": 90
      }
    }
  },
  "reportDate": "2025-12-03T10:30:00Z",
  "metadata": {
    "resourceId": "dataset-identifier",
    "resourceType": "granule|collection",
    "temporalExtent": {...}
  },
  "qualityElements": [...],
  "lineage": {...}
}
```

### Quality Element Types

DQ4EO supports ISO 19115/19157 quality element types:

- **DQ_CompletenessCommission**: Data completeness assessment
- **DQ_AbsoluteExternalPositionalAccuracy**: Geometric accuracy
- **DQ_ProcessingLevel**: Processing level information
- **DQ_RadiometricAccuracy**: Radiometric calibration accuracy
- **DQ_CloudCoverage**: Cloud coverage percentage
- **DQ_ThematicClassificationCorrectness**: Classification accuracy
- **DQ_TemporalValidity**: Temporal accuracy and currency
- **DQ_UsabilityElement**: General usability information
- **DQ_Lineage**: Data provenance and processing history

## Usage

### Using the Plugin Dialog

1. Open the UMM STAC Converter Plugin
2. Select conversion mode:
   - **UMM to DQ4EO**: Convert UMM metadata to DQ4EO quality report
   - **DQ4EO to UMM**: Convert DQ4EO quality report to UMM metadata
3. Select conversion type:
   - **Item/Granule**: For individual datasets
   - **Collection**: For dataset series
4. Browse and select input JSON file(s)
5. Select output directory
6. Click "Convert"

### Programmatic Usage

```python
from umm_to_dq4eo import UMMToDQ4EOConverter
from dq4eo_to_umm import DQ4EOToUMMConverter

# UMM to DQ4EO
umm_to_dq4eo = UMMToDQ4EOConverter()
umm_to_dq4eo.convert_file(
    'input_umm_granule.json',
    'output_dq4eo_report.json',
    'item'
)

# DQ4EO to UMM
dq4eo_to_umm = DQ4EOToUMMConverter()
dq4eo_to_umm.convert_file(
    'input_dq4eo_report.json',
    'output_umm_granule.json',
    'item'
)
```

## Examples

Example DQ4EO files are provided in the `examples/` directory:

- `dq4eo_granule_example.json`: Landsat 8 granule quality report
- `dq4eo_collection_example.json`: Sentinel-2 collection quality report

## Quality Mapping

### UMM → DQ4EO

| UMM Field | DQ4EO Mapping |
|-----------|---------------|
| `GranuleUR` / `ShortName` | `reportId` and `metadata.resourceId` |
| `SpatialExtent.BoundingRectangle` | `scope.extent.geographic` |
| `TemporalExtent` | `metadata.temporalExtent` |
| `DataQuality.Completeness` | Quality element with type `DQ_CompletenessCommission` |
| `DataQuality.Lineage` | `lineage.statement` |
| `ProviderDates` | `lineage.processSteps` |
| `ProcessingLevel` | Quality element with type `DQ_ProcessingLevel` |
| `DataGranule.ProductionDateTime` | Quality element with type `DQ_TemporalValidity` |

### DQ4EO → UMM

| DQ4EO Field | UMM Mapping |
|-------------|-------------|
| `reportId` / `metadata.resourceId` | `GranuleUR` / `ShortName` |
| `scope.extent.geographic` | `SpatialExtent.HorizontalSpatialDomain.Geometry.BoundingRectangle` |
| `metadata.temporalExtent` | `TemporalExtent` |
| Quality elements with `Completeness` | `DataQuality.Completeness` |
| `lineage.statement` | `DataQuality.Lineage` |
| `lineage.processSteps` | `ProviderDates` |
| `reportDate` | `ProviderDates` (Create type) |

## Standards Compliance

- **ISO 19115**: Geographic information - Metadata
- **ISO 19115-4**: Metadata for imagery and gridded data
- **ISO 19157**: Data quality
- **QA4EO**: Quality Assurance Framework for Earth Observation
- **NASA UMM**: Unified Metadata Model v1.6.4

## Future Enhancements

Planned improvements include:

- Support for additional ISO 19115-4 quality elements
- Enhanced lineage provenance tracking
- Integration with STAC quality extension
- Validation against QA4EO guidelines
- Support for uncertainty quantification

## Related Conversions

This plugin also supports:

- **UMM ↔ STAC**: Conversion between UMM and STAC formats
- **STAC ↔ UMM**: Bidirectional STAC/UMM conversion

All converters preserve quality information and maintain compatibility with the liability and claims extension.

## References

- [ISO 19115-1:2014](https://www.iso.org/standard/53798.html) - Geographic information - Metadata
- [ISO 19157:2013](https://www.iso.org/standard/32575.html) - Data quality
- [QA4EO Guidelines](https://qa4eo.org/) - Quality Assurance Framework for Earth Observation
- [NASA EOSDIS UMM](https://earthdata.nasa.gov/eosdis/science-system-description/eosdis-components/common-metadata-repository/unified-metadata-model) - Unified Metadata Model
