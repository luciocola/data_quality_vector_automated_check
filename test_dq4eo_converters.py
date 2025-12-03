#!/usr/bin/env python3
"""
Test script for DQ4EO conversion functionality
"""
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from umm_to_dq4eo import UMMToDQ4EOConverter
from dq4eo_to_umm import DQ4EOToUMMConverter


def test_umm_to_dq4eo():
    """Test UMM to DQ4EO conversion with sample data"""
    print("\n=== Testing UMM to DQ4EO Conversion ===")
    
    # Sample UMM Granule
    umm_granule = {
        "GranuleUR": "TEST_GRANULE_001",
        "ProviderDates": [
            {
                "Date": "2025-12-01T10:00:00Z",
                "Type": "Create"
            }
        ],
        "CollectionReference": {
            "ShortName": "TEST_COLLECTION"
        },
        "DataGranule": {
            "ProductionDateTime": "2025-12-01T10:00:00Z"
        },
        "TemporalExtent": {
            "RangeDateTime": {
                "BeginningDateTime": "2025-12-01T00:00:00Z",
                "EndingDateTime": "2025-12-01T23:59:59Z"
            }
        },
        "SpatialExtent": {
            "HorizontalSpatialDomain": {
                "Geometry": {
                    "BoundingRectangle": {
                        "WestBoundingCoordinate": -122.5,
                        "EastBoundingCoordinate": -122.0,
                        "SouthBoundingCoordinate": 37.5,
                        "NorthBoundingCoordinate": 38.0
                    }
                }
            }
        },
        "DataQuality": {
            "Completeness": True,
            "Lineage": "Test data generated for converter validation"
        }
    }
    
    # Convert
    converter = UMMToDQ4EOConverter()
    dq4eo_result = converter.convert_umm_granule_to_dq4eo(umm_granule)
    
    # Verify
    assert dq4eo_result["type"] == "DQ4EO-QualityReport"
    assert "reportId" in dq4eo_result
    assert "qualityElements" in dq4eo_result
    assert len(dq4eo_result["qualityElements"]) > 0
    
    print("✓ UMM to DQ4EO conversion successful")
    print(f"  - Report ID: {dq4eo_result['reportId']}")
    print(f"  - Quality Elements: {len(dq4eo_result['qualityElements'])}")
    
    return dq4eo_result


def test_dq4eo_to_umm():
    """Test DQ4EO to UMM conversion with sample data"""
    print("\n=== Testing DQ4EO to UMM Conversion ===")
    
    # Sample DQ4EO report
    dq4eo_report = {
        "type": "DQ4EO-QualityReport",
        "version": "1.0.0",
        "reportId": "DQ4EO-TEST-001",
        "scope": {
            "level": "dataset",
            "extent": {
                "geographic": {
                    "westBoundLongitude": -122.5,
                    "eastBoundLongitude": -122.0,
                    "southBoundLatitude": 37.5,
                    "northBoundLatitude": 38.0
                }
            }
        },
        "reportDate": "2025-12-03T10:30:00Z",
        "metadata": {
            "resourceId": "TEST_RESOURCE_001",
            "resourceType": "granule",
            "temporalExtent": {
                "begin": "2025-12-01T00:00:00Z",
                "end": "2025-12-01T23:59:59Z"
            }
        },
        "qualityElements": [
            {
                "elementType": "DQ_CompletenessCommission",
                "measure": "Data completeness",
                "result": {
                    "value": True,
                    "pass": True,
                    "valueType": "Boolean"
                }
            }
        ],
        "lineage": {
            "statement": "Test data for DQ4EO to UMM conversion"
        }
    }
    
    # Convert
    converter = DQ4EOToUMMConverter()
    umm_result = converter.convert_dq4eo_to_umm_granule(dq4eo_report)
    
    # Verify
    assert "GranuleUR" in umm_result
    assert "SpatialExtent" in umm_result
    assert "DataQuality" in umm_result
    
    print("✓ DQ4EO to UMM conversion successful")
    print(f"  - Granule UR: {umm_result['GranuleUR']}")
    print(f"  - Has DataQuality: {bool(umm_result.get('DataQuality'))}")
    
    return umm_result


def test_round_trip():
    """Test round-trip conversion UMM -> DQ4EO -> UMM"""
    print("\n=== Testing Round-Trip Conversion ===")
    
    # Original UMM data
    original_umm = {
        "GranuleUR": "ROUNDTRIP_TEST_001",
        "SpatialExtent": {
            "HorizontalSpatialDomain": {
                "Geometry": {
                    "BoundingRectangle": {
                        "WestBoundingCoordinate": -120.0,
                        "EastBoundingCoordinate": -119.0,
                        "SouthBoundingCoordinate": 36.0,
                        "NorthBoundingCoordinate": 37.0
                    }
                }
            }
        },
        "TemporalExtent": {
            "SingleDateTime": "2025-12-01T12:00:00Z"
        },
        "DataQuality": {
            "Completeness": True,
            "Lineage": "Original test data"
        }
    }
    
    # UMM -> DQ4EO
    umm_to_dq4eo = UMMToDQ4EOConverter()
    dq4eo_intermediate = umm_to_dq4eo.convert_umm_granule_to_dq4eo(original_umm)
    
    # DQ4EO -> UMM
    dq4eo_to_umm = DQ4EOToUMMConverter()
    final_umm = dq4eo_to_umm.convert_dq4eo_to_umm_granule(dq4eo_intermediate)
    
    # Verify key fields preserved
    # Note: reportId is prefixed with "DQ4EO-" so we check if the original ID is in the report ID
    assert original_umm["GranuleUR"] in dq4eo_intermediate["reportId"]
    assert final_umm["GranuleUR"] == original_umm["GranuleUR"]
    assert "SpatialExtent" in final_umm
    assert "DataQuality" in final_umm
    
    print("✓ Round-trip conversion successful")
    print(f"  - Original GranuleUR: {original_umm['GranuleUR']}")
    print(f"  - Final GranuleUR: {final_umm['GranuleUR']}")
    print(f"  - Quality preserved: {bool(final_umm.get('DataQuality'))}")


def main():
    """Run all tests"""
    print("=" * 60)
    print("DQ4EO Converter Test Suite")
    print("=" * 60)
    
    try:
        # Run tests
        test_umm_to_dq4eo()
        test_dq4eo_to_umm()
        test_round_trip()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        
        return 0
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
