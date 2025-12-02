# UMM STAC Liability/Claim Converter - Quick Start

## 📋 Overview

**Location**: `/Users/luciocolaiacomo/4113Eng-wfs/cop_defence_stac/umm_stac_converter_plugin/`

A complete QGIS plugin for bidirectional conversion between NASA's Unified Metadata Model (UMM) and STAC with liability/claim extension support.

## ✅ Project Status

**Status**: ✅ Complete and Tested  
**Lines of Code**: ~2,077  
**Tests**: All passing (3/3) ✅

## 🎯 Key Features

- ✅ UMM to STAC conversion (Items & Collections)
- ✅ STAC to UMM conversion (Items & Collections)
- ✅ Liability/Claim extension support
- ✅ Batch processing
- ✅ User-friendly GUI
- ✅ Progress tracking
- ✅ Comprehensive documentation
- ✅ Test suite included

## 📁 Plugin Files

### Core Components (5 files)
- `__init__.py` - Plugin initialization
- `umm_stac_converter.py` - Main plugin class
- `umm_to_stac.py` - UMM→STAC converter (450+ lines)
- `stac_to_umm.py` - STAC→UMM converter (450+ lines)
- `converter_dialog.py` - UI dialog logic

### User Interface (1 file)
- `converter_dialog_base.ui` - Qt Designer UI file

### Configuration (3 files)
- `metadata.txt` - Plugin metadata
- `pb_tool.cfg` - Plugin builder config
- `resources.qrc` + `resources.py` - Qt resources

### Documentation (4 files)
- `README.md` - Main documentation
- `INSTALLATION.md` - Installation guide
- `USER_GUIDE.md` - User manual
- `DEVELOPMENT_SUMMARY.md` - Technical details

### Examples & Tests (3 files)
- `examples/example_umm_granule.json` - Sample UMM data
- `examples/example_stac_item.json` - Sample STAC data
- `test_converters.py` - Test suite (all tests passing ✅)

### Resources (1 file)
- `icon.png` - Plugin icon

## 🚀 Quick Start

### 1. Test the Converters (Outside QGIS)

```bash
cd /Users/luciocolaiacomo/4113Eng-wfs/cop_defence_stac/umm_stac_converter_plugin
python3 test_converters.py
```

Expected output: All tests pass ✅

### 2. Install in QGIS

#### Option A: Manual Installation
```bash
# Create QGIS plugins directory if needed
mkdir -p ~/Library/Application\ Support/QGIS/QGIS3/profiles/default/python/plugins/

# Copy plugin
cp -r /Users/luciocolaiacomo/4113Eng-wfs/cop_defence_stac/umm_stac_converter_plugin \
      ~/Library/Application\ Support/QGIS/QGIS3/profiles/default/python/plugins/
```

#### Option B: ZIP Installation
1. Create ZIP: `cd .. && zip -r umm_stac_converter.zip umm_stac_converter_plugin/`
2. In QGIS: Plugins → Manage and Install Plugins → Install from ZIP

### 3. Enable in QGIS

1. Open QGIS
2. Go to **Plugins → Manage and Install Plugins**
3. Find **"UMM STAC Liability/Claim Converter"**
4. Check the box to enable it

### 4. Use the Plugin

1. Click the plugin icon in toolbar or **Plugins → UMM STAC Converter**
2. Select conversion mode (UMM→STAC or STAC→UMM)
3. Choose input files (use examples to test)
4. Select output directory
5. Click **Convert**

## 🔬 Liability/Claim Extension

### STAC Extension Fields

```json
{
  "cop:liability": {
    "description": "Liability description",
    "license_text": "License terms",
    "license_url": "https://example.com/license"
  },
  "cop:claim": {
    "description": "Claim information",
    "value": 30
  },
  "cop:liability_contact": {
    "name": "Contact Name",
    "email": "contact@example.com"
  }
}
```

### UMM Field Mapping

- `UseConstraints` ↔ `cop:liability`
- `AccessConstraints` ↔ `cop:claim`
- `ContactPersons` ↔ `cop:liability_contact`
- `DataCenters` ↔ `cop:data_provider_liability`

## 📖 Documentation

- **README.md** - Project overview and features
- **INSTALLATION.md** - Detailed installation instructions
- **USER_GUIDE.md** - Complete user manual with examples
- **DEVELOPMENT_SUMMARY.md** - Technical implementation details

## 🧪 Testing

Test results from `test_converters.py`:

```
Test Summary
============================================================
UMM to STAC          ✅ PASS
STAC to UMM          ✅ PASS
Round-Trip           ✅ PASS
============================================================
🎉 All tests passed!
```

## 🛠️ Technical Details

- **Language**: Python 3.6+
- **Framework**: PyQt5
- **QGIS Version**: 3.0+
- **STAC Version**: 1.0.0
- **UMM Version**: 1.6.4

## 📦 What's Included

- ✅ Complete QGIS plugin
- ✅ Bidirectional converters
- ✅ UI dialog with batch processing
- ✅ Comprehensive documentation
- ✅ Example data files
- ✅ Test suite (passing)
- ✅ Plugin icon
- ✅ Configuration files

## 🎓 Next Steps

1. **Test with sample data**:
   ```bash
   python3 test_converters.py
   ```

2. **Install in QGIS** and test with example files

3. **Try with your own data** (UMM or STAC JSON files)

4. **Customize** as needed:
   - Modify extension fields in `umm_to_stac.py`
   - Adjust UMM mapping in `stac_to_umm.py`
   - Update UI in `converter_dialog_base.ui`

## 📞 Support

- **Repository**: https://github.com/luciocola/qgisplugin4cop
- **Issues**: https://github.com/luciocola/qgisplugin4cop/issues
- **Documentation**: See included `.md` files

## 📝 License

See repository for license information.

---

**Created**: December 2, 2025  
**Author**: Lucio Colaiacomo  
**Version**: 1.0.0  
**Status**: Production Ready ✅
