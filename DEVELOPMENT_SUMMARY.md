# Plugin Development Summary

## Project: UMM STAC Liability/Claim Converter Plugin

### Location
`/Users/luciocolaiacomo/4113Eng-wfs/cop_defence_stac/umm_stac_converter_plugin/`

### Description
A QGIS plugin that enables bidirectional conversion between NASA's Unified Metadata Model (UMM) and STAC (SpatioTemporal Asset Catalog) format with support for liability and claim extensions.

## Plugin Structure

### Core Files
1. **`__init__.py`** - Plugin initialization and class factory
2. **`umm_stac_converter.py`** - Main plugin class with QGIS integration
3. **`metadata.txt`** - Plugin metadata and configuration

### Conversion Modules
4. **`umm_to_stac.py`** - UMM to STAC converter with liability/claim extension support
5. **`stac_to_umm.py`** - STAC to UMM converter with liability/claim extension support

### User Interface
6. **`converter_dialog.py`** - Dialog class with conversion logic
7. **`converter_dialog_base.ui`** - Qt Designer UI file

### Resources
8. **`icon.png`** - Plugin icon (64x64 pixels)
9. **`resources.qrc`** - Qt resource collection file
10. **`resources.py`** - Compiled Python resources
11. **`pb_tool.cfg`** - Plugin builder configuration

### Documentation
12. **`README.md`** - Main documentation
13. **`INSTALLATION.md`** - Installation guide
14. **`USER_GUIDE.md`** - Detailed user guide

### Examples
15. **`examples/example_umm_granule.json`** - Sample UMM granule data
16. **`examples/example_stac_item.json`** - Sample STAC item data

## Key Features

### Bidirectional Conversion
- **UMM to STAC**: Converts UMM granules/collections to STAC items/collections
- **STAC to UMM**: Converts STAC items/collections to UMM granules/collections

### Liability/Claim Extension Support
The plugin implements a custom STAC extension for liability and claim management:

#### STAC Extension Fields
- `cop:liability` - Liability description and license information
- `cop:claim` - Claim tracking and value
- `cop:liability_contact` - Contact information for liability matters
- `cop:data_provider_liability` - Organization liability information

#### UMM Field Mapping
- `UseConstraints` ↔ `cop:liability`
- `AccessConstraints` ↔ `cop:claim`
- `ContactPersons` ↔ `cop:liability_contact`
- `DataCenters` ↔ `cop:data_provider_liability`

### Data Type Support
- **Items/Granules**: Individual data records
- **Collections**: Dataset-level metadata

### User-Friendly Interface
- Simple dialog-based interface
- Batch processing support
- Progress tracking
- Error handling and validation

## Technical Implementation

### UMM to STAC Conversion
Handles conversion of:
- Spatial extent (BoundingRectangle, Point → GeoJSON)
- Temporal extent (RangeDateTime, SingleDateTime → ISO 8601)
- Metadata properties (platforms, instruments, keywords)
- Related URLs and data links
- Liability and claim information

### STAC to UMM Conversion
Handles conversion of:
- GeoJSON geometry → UMM spatial extent
- ISO 8601 datetime → UMM temporal extent
- STAC properties → UMM metadata
- STAC links and assets → UMM RelatedUrls
- Extension properties → UMM constraints and contacts

### Threading
- Uses QThread for non-blocking conversion
- Progress signals for UI updates
- Cancellation support

## Installation

### Quick Install
1. Copy plugin folder to QGIS plugins directory
2. Enable in QGIS Plugin Manager

### Paths
- **macOS**: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
- **Windows**: `C:\Users\<username>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\`
- **Linux**: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`

## Usage Workflow

1. Open plugin from toolbar or menu
2. Select conversion mode (UMM→STAC or STAC→UMM)
3. Select conversion type (Item or Collection)
4. Choose input file(s)
5. Select output directory
6. Click Convert
7. Review results

## Future Enhancements

Potential improvements:
- Schema validation for input/output
- Support for additional STAC extensions
- UMM version selection
- Conversion preview
- Undo/rollback capability
- Logging to file
- Configuration presets

## Dependencies

- QGIS 3.0+
- Python 3.6+
- PyQt5
- Standard library: json, os, typing, datetime

## License & Support

- Repository: https://github.com/luciocola/qgisplugin4cop
- Issues: https://github.com/luciocola/qgisplugin4cop/issues

## Testing

To test the plugin:
1. Use provided example files in `examples/` folder
2. Test both conversion directions
3. Verify liability/claim fields are preserved
4. Check batch processing with multiple files

## Notes

- The plugin assumes well-formed JSON input
- Output files are automatically named with `_stac` or `_umm` suffix
- Conversion is lossless for supported fields
- Unsupported fields are omitted from output
- The cop: extension prefix is used for custom liability/claim fields

---
Created: December 2, 2025
Author: Lucio Colaiacomo
Version: 1.0.0
