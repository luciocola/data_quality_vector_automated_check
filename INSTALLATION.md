# Installation Guide

## Requirements

- QGIS 3.0 or higher
- Python 3.6+
- PyQt5

## Installation Methods

### Method 1: From ZIP File

1. Download the plugin ZIP file
2. Open QGIS
3. Go to `Plugins` → `Manage and Install Plugins`
4. Click on `Install from ZIP`
5. Select the downloaded ZIP file
6. Click `Install Plugin`

### Method 2: Manual Installation

1. Copy the `umm_stac_converter_plugin` folder to your QGIS plugins directory:
   - **Windows**: `C:\Users\<username>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\`
   - **macOS**: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
   - **Linux**: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`

2. Restart QGIS

3. Enable the plugin:
   - Go to `Plugins` → `Manage and Install Plugins`
   - Find "UMM STAC Liability/Claim Converter" in the list
   - Check the box to enable it

## Verification

After installation, you should see:
- A new toolbar icon
- A menu entry under `Plugins` → `UMM STAC Converter`

## Troubleshooting

### Plugin doesn't appear after installation

1. Check that the plugin folder is in the correct location
2. Verify that all required files are present
3. Check the QGIS Python console for any error messages

### Import errors

If you see import errors, ensure that:
- QGIS is using Python 3.6 or higher
- PyQt5 is properly installed

## Updating

To update the plugin:
1. Remove the old version
2. Install the new version using one of the methods above

## Uninstallation

1. Go to `Plugins` → `Manage and Install Plugins`
2. Find "UMM STAC Liability/Claim Converter"
3. Click `Uninstall Plugin`

Or manually delete the plugin folder from your plugins directory.
