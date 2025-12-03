"""
DQ4EO to UMM Converter Module

Converts DQ4EO (Data Quality for Earth Observation) format to 
NASA Unified Metadata Model (UMM) with quality preservation.
"""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime


class DQ4EOToUMMConverter:
    """Converter for DQ4EO to UMM format."""

    def __init__(self):
        """Initialize the converter."""
        self.umm_version = "1.6.4"

    def convert_file(self, input_file: str, output_file: str, conversion_type: str = 'item') -> bool:
        """Convert DQ4EO file to UMM format.
        
        :param input_file: Path to input DQ4EO JSON file
        :param output_file: Path to output UMM JSON file
        :param conversion_type: Type of conversion ('item' for granule or 'collection')
        :return: Success status
        """
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                dq4eo_data = json.load(f)
            
            if conversion_type == 'item':
                umm_data = self.convert_dq4eo_to_umm_granule(dq4eo_data)
            else:
                umm_data = self.convert_dq4eo_to_umm_collection(dq4eo_data)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(umm_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error converting DQ4EO to UMM: {str(e)}")
            return False

    def convert_dq4eo_to_umm_granule(self, dq4eo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DQ4EO quality report to UMM Granule.

        :param dq4eo_data: DQ4EO quality report dictionary
        :return: UMM Granule dictionary
        """
        metadata = dq4eo_data.get("metadata", {})
        
        umm_granule = {
            "GranuleUR": metadata.get("resourceId", dq4eo_data.get("reportId", "unknown")),
            "ProviderDates": self._convert_provider_dates(dq4eo_data),
            "DataGranule": self._convert_data_granule(dq4eo_data),
            "TemporalExtent": self._convert_temporal_extent(dq4eo_data),
            "SpatialExtent": self._convert_spatial_extent(dq4eo_data),
            "DataQuality": self._convert_quality_to_umm(dq4eo_data)
        }

        # Add collection reference if available
        if "parentCollection" in metadata:
            umm_granule["CollectionReference"] = {
                "ShortName": metadata["parentCollection"]
            }

        # Remove None values
        return {k: v for k, v in umm_granule.items() if v is not None}

    def convert_dq4eo_to_umm_collection(self, dq4eo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DQ4EO quality report to UMM Collection.

        :param dq4eo_data: DQ4EO quality report dictionary
        :return: UMM Collection dictionary
        """
        metadata = dq4eo_data.get("metadata", {})
        
        umm_collection = {
            "ShortName": metadata.get("resourceId", dq4eo_data.get("reportId", "unknown")),
            "EntryTitle": metadata.get("title", "Untitled Collection"),
            "Abstract": metadata.get("abstract", "Collection converted from DQ4EO quality report"),
            "TemporalExtents": self._convert_collection_temporal_extent(dq4eo_data),
            "SpatialExtent": self._convert_spatial_extent(dq4eo_data),
            "DataQuality": self._convert_quality_to_umm(dq4eo_data),
            "CollectionDataQuality": self._convert_collection_quality(dq4eo_data)
        }

        # Remove None values
        return {k: v for k, v in umm_collection.items() if v is not None}

    def _convert_provider_dates(self, dq4eo_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert DQ4EO dates to UMM ProviderDates.

        :param dq4eo_data: DQ4EO data
        :return: List of provider dates
        """
        provider_dates = []

        # Add report date
        if "reportDate" in dq4eo_data:
            provider_dates.append({
                "Date": dq4eo_data["reportDate"],
                "Type": "Create"
            })

        # Extract dates from lineage process steps
        lineage = dq4eo_data.get("lineage", {})
        process_steps = lineage.get("processSteps", [])
        
        for step in process_steps:
            if "dateTime" in step:
                provider_dates.append({
                    "Date": step["dateTime"],
                    "Type": "Update"
                })

        return provider_dates if provider_dates else None

    def _convert_data_granule(self, dq4eo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DQ4EO data to UMM DataGranule.

        :param dq4eo_data: DQ4EO data
        :return: DataGranule dictionary or None
        """
        data_granule = {}

        # Use report date as production date
        if "reportDate" in dq4eo_data:
            data_granule["ProductionDateTime"] = dq4eo_data["reportDate"]

        return data_granule if data_granule else None

    def _convert_temporal_extent(self, dq4eo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DQ4EO temporal extent to UMM format.

        :param dq4eo_data: DQ4EO data
        :return: UMM temporal extent or None
        """
        metadata = dq4eo_data.get("metadata", {})
        temporal = metadata.get("temporalExtent", {})

        if not temporal:
            return None

        umm_temporal = {}

        if "begin" in temporal and "end" in temporal:
            umm_temporal["RangeDateTime"] = {
                "BeginningDateTime": temporal["begin"],
                "EndingDateTime": temporal["end"]
            }
        elif "instant" in temporal:
            umm_temporal["SingleDateTime"] = temporal["instant"]

        return umm_temporal if umm_temporal else None

    def _convert_collection_temporal_extent(self, dq4eo_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert DQ4EO temporal extent to UMM Collection format.

        :param dq4eo_data: DQ4EO data
        :return: List of temporal extents or None
        """
        metadata = dq4eo_data.get("metadata", {})
        temporal = metadata.get("temporalExtent", {})

        if not temporal:
            return None

        temporal_extents = []

        if "begin" in temporal and "end" in temporal:
            temporal_extents.append({
                "RangeDateTimes": [{
                    "BeginningDateTime": temporal["begin"],
                    "EndingDateTime": temporal["end"]
                }]
            })
        elif "instant" in temporal:
            temporal_extents.append({
                "SingleDateTimes": [temporal["instant"]]
            })

        return temporal_extents if temporal_extents else None

    def _convert_spatial_extent(self, dq4eo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DQ4EO spatial extent to UMM format.

        :param dq4eo_data: DQ4EO data
        :return: UMM spatial extent or None
        """
        scope = dq4eo_data.get("scope", {})
        extent = scope.get("extent", {})
        geographic = extent.get("geographic", {})

        if not geographic:
            return None

        return {
            "HorizontalSpatialDomain": {
                "Geometry": {
                    "BoundingRectangle": {
                        "WestBoundingCoordinate": geographic.get("westBoundLongitude", -180),
                        "EastBoundingCoordinate": geographic.get("eastBoundLongitude", 180),
                        "SouthBoundingCoordinate": geographic.get("southBoundLatitude", -90),
                        "NorthBoundingCoordinate": geographic.get("northBoundLatitude", 90)
                    }
                }
            }
        }

    def _convert_quality_to_umm(self, dq4eo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DQ4EO quality elements to UMM DataQuality.

        :param dq4eo_data: DQ4EO data
        :return: UMM DataQuality dictionary or None
        """
        quality_elements = dq4eo_data.get("qualityElements", [])
        lineage = dq4eo_data.get("lineage", {})

        if not quality_elements and not lineage:
            return None

        data_quality = {}

        # Extract completeness information
        for element in quality_elements:
            element_type = element.get("elementType", "")
            
            if "Completeness" in element_type:
                result = element.get("result", {})
                data_quality["Completeness"] = result.get("pass", True)
            
            # Build lineage statement
            if element_type == "DQ_Lineage":
                result = element.get("result", {})
                if "statement" in result:
                    data_quality["Lineage"] = result["statement"]

        # Add lineage statement if available
        if "statement" in lineage and "Lineage" not in data_quality:
            data_quality["Lineage"] = lineage["statement"]

        # Add quality flag
        if quality_elements:
            data_quality["DataQualityFlag"] = "Available"

        return data_quality if data_quality else None

    def _convert_collection_quality(self, dq4eo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DQ4EO quality elements to UMM CollectionDataQuality.

        :param dq4eo_data: DQ4EO data
        :return: CollectionDataQuality dictionary or None
        """
        quality_elements = dq4eo_data.get("qualityElements", [])

        if not quality_elements:
            return None

        collection_quality = {}

        for element in quality_elements:
            element_type = element.get("elementType", "Unknown")
            measure = element.get("measure", "")
            result = element.get("result", {})
            
            # Create a quality entry
            key = measure if measure else element_type
            value = result.get("value", "")
            
            if value:
                collection_quality[key] = value

        return collection_quality if collection_quality else None
