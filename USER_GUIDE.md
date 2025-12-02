# User Guide

## Overview

The UMM STAC Liability/Claim Converter plugin enables conversion between NASA's Unified Metadata Model (UMM) and STAC (SpatioTemporal Asset Catalog) format with support for liability and claim extensions.

## Opening the Plugin

There are two ways to open the plugin:

1. Click the plugin icon in the toolbar
2. Go to `Plugins` → `UMM STAC Converter`

## User Interface

The plugin dialog contains the following sections:

### 1. Conversion Mode

Select the direction of conversion:
- **UMM to STAC**: Convert UMM JSON files to STAC format
- **STAC to UMM**: Convert STAC JSON files to UMM format

### 2. Conversion Type

Select the type of data being converted:
- **Item/Granule**: For individual data items (UMM Granule ↔ STAC Item)
- **Collection**: For collections/datasets (UMM Collection ↔ STAC Collection)

### 3. Input Files

- Click "Browse..." to select one or more JSON files to convert
- Multiple files can be selected for batch processing
- The number of selected files will be displayed

### 4. Output Directory

- Click "Browse..." to select the destination folder for converted files
- Output files will be automatically named based on input files
- Naming convention:
  - UMM to STAC: `<original_name>_stac.json`
  - STAC to UMM: `<original_name>_umm.json`

### 5. Progress

- Shows the current conversion status
- Progress bar indicates completion percentage
- Displays which file is currently being processed

## Step-by-Step Usage

### Converting UMM to STAC

1. Select "UMM to STAC" conversion mode
2. Select conversion type (Item or Collection)
3. Click "Browse..." under Input Files
4. Select one or more UMM JSON files
5. Click "Browse..." under Output Directory
6. Select destination folder
7. Click "Convert"
8. Wait for conversion to complete
9. Check the output directory for converted files

### Converting STAC to UMM

1. Select "STAC to UMM" conversion mode
2. Select conversion type (Item or Collection)
3. Click "Browse..." under Input Files
4. Select one or more STAC JSON files
5. Click "Browse..." under Output Directory
6. Select destination folder
7. Click "Convert"
8. Wait for conversion to complete
9. Check the output directory for converted files

## Liability/Claim Extension

The plugin supports the STAC COP (Community of Practice) extension for liability and claim information.

### Fields Supported

**Liability Information:**
- `cop:liability`: Liability description and license information
- `cop:liability_contact`: Contact information for liability matters

**Claim Information:**
- `cop:claim`: Claim description and value
- `cop:data_provider_liability`: Organization liability information

### UMM Mapping

The extension maps to the following UMM fields:
- `UseConstraints`: Liability and license information
- `AccessConstraints`: Claim information
- `ContactPersons`: Liability contact information
- `DataCenters`: Provider liability information

## Tips and Best Practices

1. **Validate Input Files**: Ensure your JSON files are valid before conversion
2. **Backup Original Files**: Keep backups of original files before batch conversion
3. **Check Output**: Review converted files to ensure accuracy
4. **Consistent Types**: Use the same conversion type for related files
5. **Organization**: Keep input and output in separate directories

## Error Handling

If conversion fails:
- Check that input files are valid JSON
- Verify files match the selected conversion type
- Check QGIS message log for detailed error information
- Ensure you have write permissions to the output directory

## Batch Processing

The plugin supports batch processing:
- Select multiple files in the input file dialog
- All files will be converted using the same settings
- Progress is shown for each file
- A summary is displayed when complete

## Keyboard Shortcuts

- **Enter**: Start conversion (when Convert button is focused)
- **Escape**: Close dialog
- **Tab**: Navigate between fields

## Getting Help

If you encounter issues:
1. Check the QGIS message log: `View` → `Panels` → `Log Messages`
2. Review the error message displayed in the dialog
3. Consult the README.md file
4. Report issues at: https://github.com/luciocola/qgisplugin4cop/issues
