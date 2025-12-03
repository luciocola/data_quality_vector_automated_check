# DQ4EO Quick Reference

## What is DQ4EO?

DQ4EO (Data Quality for Earth Observation) is a metadata format focused on quality reporting for Earth observation data, based on ISO 19115/19157 standards.

## Quick Start

### Convert UMM to DQ4EO Quality Report

```bash
# In QGIS
1. Plugins → UMM STAC DQ4EO Converter
2. Select "UMM to DQ4EO"
3. Choose "Item/Granule" or "Collection"
4. Select input UMM JSON file
5. Choose output directory
6. Click Convert
```

### Convert DQ4EO back to UMM

```bash
# In QGIS
1. Plugins → UMM STAC DQ4EO Converter
2. Select "DQ4EO to UMM"
3. Choose "Item/Granule" or "Collection"
4. Select input DQ4EO JSON file
5. Choose output directory
6. Click Convert
```

## DQ4EO Structure at a Glance

```json
{
  "type": "DQ4EO-QualityReport",
  "reportId": "unique-id",
  "scope": { "level": "dataset|series", "extent": {...} },
  "metadata": { "resourceId": "...", "temporalExtent": {...} },
  "qualityElements": [
    {
      "elementType": "DQ_xxx",
      "measure": "description",
      "result": { "value": "...", "unit": "..." }
    }
  ],
  "lineage": { "statement": "...", "processSteps": [...] }
}
```

## Common Quality Element Types

| Element Type | Purpose |
|--------------|---------|
| `DQ_CompletenessCommission` | Data completeness |
| `DQ_AbsoluteExternalPositionalAccuracy` | Geometric accuracy |
| `DQ_ProcessingLevel` | Processing level info |
| `DQ_RadiometricAccuracy` | Radiometric quality |
| `DQ_CloudCoverage` | Cloud coverage % |
| `DQ_TemporalValidity` | Temporal accuracy |
| `DQ_Lineage` | Data provenance |

## Examples Location

```bash
examples/dq4eo_granule_example.json     # Landsat 8 example
examples/dq4eo_collection_example.json  # Sentinel-2 example
```

## Programmatic Use

```python
from umm_to_dq4eo import UMMToDQ4EOConverter
from dq4eo_to_umm import DQ4EOToUMMConverter

# UMM → DQ4EO
converter = UMMToDQ4EOConverter()
converter.convert_file('umm.json', 'dq4eo.json', 'item')

# DQ4EO → UMM
converter = DQ4EOToUMMConverter()
converter.convert_file('dq4eo.json', 'umm.json', 'item')
```

## Testing

```bash
cd umm_stac_converter_plugin
python3 test_dq4eo_converters.py
```

## Key Mappings

### UMM → DQ4EO
- `GranuleUR` → `reportId` (prefixed with "DQ4EO-")
- `DataQuality.Completeness` → Quality element
- `DataQuality.Lineage` → `lineage.statement`
- `SpatialExtent` → `scope.extent.geographic`

### DQ4EO → UMM
- `metadata.resourceId` → `GranuleUR`
- Quality elements → `DataQuality` fields
- `lineage.statement` → `DataQuality.Lineage`
- `scope.extent` → `SpatialExtent`

## Documentation

- Full guide: `DQ4EO_CONVERSION.md`
- Implementation: `DQ4EO_IMPLEMENTATION_SUMMARY.md`
- Main README: `README.md`

## Standards

- ISO 19115: Geographic metadata
- ISO 19157: Data quality
- QA4EO: Quality Assurance for EO
- NASA UMM v1.6.4
