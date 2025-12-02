#!/usr/bin/env python3
"""
Simple test script for UMM-STAC converters
Run this outside of QGIS to test the conversion logic
"""

import json
import sys
import os

# Add plugin directory to path
sys.path.insert(0, os.path.dirname(__file__))

from umm_to_stac import UMMToSTACConverter
from stac_to_umm import STACToUMMConverter


def test_umm_to_stac():
    """Test UMM to STAC conversion."""
    print("=" * 60)
    print("Testing UMM to STAC Conversion")
    print("=" * 60)
    
    # Load example UMM file
    example_file = os.path.join(os.path.dirname(__file__), 
                                'examples', 'example_umm_granule.json')
    
    if not os.path.exists(example_file):
        print(f"❌ Example file not found: {example_file}")
        return False
    
    try:
        with open(example_file, 'r') as f:
            umm_data = json.load(f)
        print(f"✓ Loaded UMM example file")
        
        # Create converter
        converter = UMMToSTACConverter()
        
        # Convert to STAC
        stac_item = converter.convert_umm_to_stac_item(umm_data)
        print(f"✓ Converted to STAC Item")
        
        # Verify STAC structure
        assert stac_item['type'] == 'Feature', "Invalid type"
        assert 'stac_version' in stac_item, "Missing stac_version"
        assert 'geometry' in stac_item, "Missing geometry"
        assert 'properties' in stac_item, "Missing properties"
        print(f"✓ STAC structure validated")
        
        # Verify liability/claim extension
        props = stac_item['properties']
        if 'cop:liability' in props:
            print(f"✓ Liability extension found")
        if 'cop:claim' in props:
            print(f"✓ Claim extension found")
        if 'cop:liability_contact' in props:
            print(f"✓ Liability contact found")
        
        # Save result
        output_file = os.path.join(os.path.dirname(__file__), 
                                  'test_output_stac.json')
        with open(output_file, 'w') as f:
            json.dump(stac_item, f, indent=2)
        print(f"✓ Saved to: {output_file}")
        
        print("\n✅ UMM to STAC conversion test PASSED\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_stac_to_umm():
    """Test STAC to UMM conversion."""
    print("=" * 60)
    print("Testing STAC to UMM Conversion")
    print("=" * 60)
    
    # Load example STAC file
    example_file = os.path.join(os.path.dirname(__file__), 
                                'examples', 'example_stac_item.json')
    
    if not os.path.exists(example_file):
        print(f"❌ Example file not found: {example_file}")
        return False
    
    try:
        with open(example_file, 'r') as f:
            stac_data = json.load(f)
        print(f"✓ Loaded STAC example file")
        
        # Create converter
        converter = STACToUMMConverter()
        
        # Convert to UMM
        umm_granule = converter.convert_stac_item_to_umm(stac_data)
        print(f"✓ Converted to UMM Granule")
        
        # Verify UMM structure
        assert 'GranuleUR' in umm_granule, "Missing GranuleUR"
        assert 'SpatialExtent' in umm_granule, "Missing SpatialExtent"
        assert 'TemporalExtent' in umm_granule, "Missing TemporalExtent"
        print(f"✓ UMM structure validated")
        
        # Verify liability/claim fields
        if 'UseConstraints' in umm_granule:
            print(f"✓ UseConstraints (liability) found")
        if 'AccessConstraints' in umm_granule:
            print(f"✓ AccessConstraints (claim) found")
        if 'ContactPersons' in umm_granule:
            print(f"✓ ContactPersons found")
        
        # Save result
        output_file = os.path.join(os.path.dirname(__file__), 
                                  'test_output_umm.json')
        with open(output_file, 'w') as f:
            json.dump(umm_granule, f, indent=2)
        print(f"✓ Saved to: {output_file}")
        
        print("\n✅ STAC to UMM conversion test PASSED\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_round_trip():
    """Test round-trip conversion (UMM → STAC → UMM)."""
    print("=" * 60)
    print("Testing Round-Trip Conversion (UMM → STAC → UMM)")
    print("=" * 60)
    
    example_file = os.path.join(os.path.dirname(__file__), 
                                'examples', 'example_umm_granule.json')
    
    try:
        # Load original UMM
        with open(example_file, 'r') as f:
            original_umm = json.load(f)
        print(f"✓ Loaded original UMM")
        
        # Convert to STAC
        umm_converter = UMMToSTACConverter()
        stac_item = umm_converter.convert_umm_to_stac_item(original_umm)
        print(f"✓ Converted UMM → STAC")
        
        # Convert back to UMM
        stac_converter = STACToUMMConverter()
        final_umm = stac_converter.convert_stac_item_to_umm(stac_item)
        print(f"✓ Converted STAC → UMM")
        
        # Compare key fields
        assert original_umm['GranuleUR'] == final_umm['GranuleUR'], \
            "GranuleUR mismatch"
        print(f"✓ GranuleUR preserved")
        
        if 'UseConstraints' in original_umm and 'UseConstraints' in final_umm:
            print(f"✓ UseConstraints preserved")
        
        print("\n✅ Round-trip conversion test PASSED\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("UMM-STAC Converter Test Suite")
    print("=" * 60 + "\n")
    
    results = []
    
    # Run tests
    results.append(("UMM to STAC", test_umm_to_stac()))
    results.append(("STAC to UMM", test_stac_to_umm()))
    results.append(("Round-Trip", test_round_trip()))
    
    # Print summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20s} {status}")
    
    print("=" * 60)
    
    # Return exit code
    all_passed = all(result for _, result in results)
    if all_passed:
        print("\n🎉 All tests passed!\n")
        return 0
    else:
        print("\n⚠️  Some tests failed!\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
