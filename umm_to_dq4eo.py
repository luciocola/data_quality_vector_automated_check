"""
UMM to DQ4EO Converter Module

Converts NASA Unified Metadata Model (UMM) to DQ4EO (Data Quality for Earth Observation)
format with ISO 19115/19157 quality reporting.
"""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime


class UMMToDQ4EOConverter:
    """Converter for UMM to DQ4EO format with quality focus."""

    def __init__(self):
        """Initialize the converter."""
        self.dq4eo_version = "1.0.0"

    def convert_file(self, input_file: str, output_file: str, conversion_type: str = 'item') -> bool:
        """Convert UMM file to DQ4EO format.
        
        :param input_file: Path to input UMM JSON file
        :param output_file: Path to output DQ4EO JSON file
        :param conversion_type: Type of conversion ('item' or 'collection')
        :return: Success status
        """
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                umm_data = json.load(f)
            
            if conversion_type == 'item':
                dq4eo_data = self.convert_umm_granule_to_dq4eo(umm_data)
            else:
                dq4eo_data = self.convert_umm_collection_to_dq4eo(umm_data)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(dq4eo_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error converting UMM to DQ4EO: {str(e)}")
            return False

    def convert_umm_granule_to_dq4eo(self, umm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert UMM Granule to DQ4EO quality report.

        :param umm_data: UMM Granule dictionary
        :return: DQ4EO quality report dictionary
        """
        dq4eo = {
            "type": "DQ4EO-QualityReport",
            "version": self.dq4eo_version,
            "reportId": f"DQ4EO-{umm_data.get('GranuleUR', 'unknown')}",
            "scope": {
                "level": "dataset",
                "extent": self._extract_extent(umm_data)
            },
            "reportDate": datetime.now().isoformat(),
            "metadata": self._extract_metadata(umm_data),
            "qualityElements": self._extract_quality_elements(umm_data),
            "lineage": self._extract_lineage(umm_data)
        }

        return dq4eo

    def convert_umm_collection_to_dq4eo(self, umm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert UMM Collection to DQ4EO quality report.

        :param umm_data: UMM Collection dictionary
        :return: DQ4EO quality report dictionary
        """
        dq4eo = {
            "type": "DQ4EO-QualityReport",
            "version": self.dq4eo_version,
            "reportId": f"DQ4EO-{umm_data.get('ShortName', 'unknown')}",
            "scope": {
                "level": "series",
                "extent": self._extract_extent(umm_data)
            },
            "reportDate": datetime.now().isoformat(),
            "metadata": self._extract_collection_metadata(umm_data),
            "qualityElements": self._extract_collection_quality_elements(umm_data),
            "lineage": self._extract_lineage(umm_data)
        }

        return dq4eo

    def _extract_metadata(self, umm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract basic metadata from UMM Granule.

        :param umm_data: UMM data
        :return: Metadata dictionary
        """
        metadata = {
            "resourceId": umm_data.get("GranuleUR", ""),
            "resourceType": "granule"
        }

        # Add temporal extent
        temporal = umm_data.get("TemporalExtent", {})
        if temporal:
            metadata["temporalExtent"] = self._convert_temporal(temporal)

        # Add collection reference
        collection_ref = umm_data.get("CollectionReference", {})
        if collection_ref:
            metadata["parentCollection"] = collection_ref.get("ShortName", "")

        return metadata

    def _extract_collection_metadata(self, umm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract basic metadata from UMM Collection.

        :param umm_data: UMM Collection data
        :return: Metadata dictionary
        """
        return {
            "resourceId": umm_data.get("ShortName", ""),
            "resourceType": "collection",
            "title": umm_data.get("EntryTitle", ""),
            "abstract": umm_data.get("Abstract", ""),
            "temporalExtent": self._convert_collection_temporal(umm_data)
        }

    def _extract_extent(self, umm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract spatial extent from UMM data.

        :param umm_data: UMM data
        :return: Extent dictionary
        """
        spatial = umm_data.get("SpatialExtent", {})
        extent = {}

        if "HorizontalSpatialDomain" in spatial:
            geometry_data = spatial["HorizontalSpatialDomain"].get("Geometry", {})
            
            if "BoundingRectangle" in geometry_data:
                rect = geometry_data["BoundingRectangle"]
                extent["geographic"] = {
                    "westBoundLongitude": rect.get("WestBoundingCoordinate", -180),
                    "eastBoundLongitude": rect.get("EastBoundingCoordinate", 180),
                    "southBoundLatitude": rect.get("SouthBoundingCoordinate", -90),
                    "northBoundLatitude": rect.get("NorthBoundingCoordinate", 90)
                }

        return extent

    def _extract_quality_elements(self, umm_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract quality elements from UMM Granule.

        :param umm_data: UMM Granule data
        :return: List of quality elements
        """
        quality_elements = []

        # Extract from DataQuality if available
        data_quality = umm_data.get("DataQuality", {})
        
        if data_quality:
            # Completeness
            if "Completeness" in data_quality:
                quality_elements.append({
                    "elementType": "DQ_CompletenessCommission",
                    "measure": "Completeness assessment",
                    "result": {
                        "value": data_quality["Completeness"],
                        "valueType": "Boolean",
                        "pass": data_quality.get("Completeness", False)
                    },
                    "evaluationMethod": "UMM DataQuality field"
                })

            # Lineage
            if "Lineage" in data_quality:
                quality_elements.append({
                    "elementType": "DQ_Lineage",
                    "measure": "Data lineage statement",
                    "result": {
                        "statement": data_quality["Lineage"],
                        "valueType": "CharacterString"
                    },
                    "evaluationMethod": "UMM DataQuality.Lineage"
                })

        # Processing level quality
        data_granule = umm_data.get("DataGranule", {})
        if "ProductionDateTime" in data_granule:
            quality_elements.append({
                "elementType": "DQ_TemporalValidity",
                "measure": "Production date validity",
                "result": {
                    "value": data_granule["ProductionDateTime"],
                    "valueType": "DateTime"
                },
                "evaluationMethod": "UMM DataGranule.ProductionDateTime"
            })

        # Add default quality element if none found
        if not quality_elements:
            quality_elements.append({
                "elementType": "DQ_UsabilityElement",
                "measure": "Data usability",
                "result": {
                    "value": "Converted from UMM format",
                    "valueType": "CharacterString"
                },
                "evaluationMethod": "UMM to DQ4EO conversion"
            })

        return quality_elements

    def _extract_collection_quality_elements(self, umm_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract quality elements from UMM Collection.

        :param umm_data: UMM Collection data
        :return: List of quality elements
        """
        quality_elements = []

        # Extract from DataQuality if available
        data_quality = umm_data.get("DataQuality", {})
        
        if data_quality:
            # Completeness
            if "Completeness" in data_quality:
                quality_elements.append({
                    "elementType": "DQ_CompletenessCommission",
                    "measure": "Collection completeness",
                    "result": {
                        "value": data_quality["Completeness"],
                        "valueType": "Boolean",
                        "pass": data_quality.get("Completeness", False)
                    },
                    "evaluationMethod": "UMM DataQuality field"
                })

        # Quality information from CollectionDataQuality
        coll_quality = umm_data.get("CollectionDataQuality", {})
        if coll_quality:
            for key, value in coll_quality.items():
                quality_elements.append({
                    "elementType": "DQ_UsabilityElement",
                    "measure": key,
                    "result": {
                        "value": str(value),
                        "valueType": "CharacterString"
                    },
                    "evaluationMethod": f"UMM CollectionDataQuality.{key}"
                })

        # Add default quality element if none found
        if not quality_elements:
            quality_elements.append({
                "elementType": "DQ_UsabilityElement",
                "measure": "Collection usability",
                "result": {
                    "value": "Converted from UMM Collection format",
                    "valueType": "CharacterString"
                },
                "evaluationMethod": "UMM to DQ4EO conversion"
            })

        return quality_elements

    def _extract_lineage(self, umm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract lineage information from UMM data.

        :param umm_data: UMM data
        :return: Lineage dictionary
        """
        lineage = {
            "statement": "Data converted from NASA UMM format",
            "processSteps": []
        }

        # Extract from DataQuality.Lineage
        data_quality = umm_data.get("DataQuality", {})
        if "Lineage" in data_quality:
            lineage["statement"] = data_quality["Lineage"]

        # Extract processing information
        processing_level = umm_data.get("ProcessingLevel", {})
        if processing_level:
            lineage["processSteps"].append({
                "description": f"Processing level: {processing_level.get('Id', 'unknown')}",
                "rationale": processing_level.get("ProcessingLevelDescription", "")
            })

        # Extract provider dates
        provider_dates = umm_data.get("ProviderDates", [])
        for date_info in provider_dates:
            lineage["processSteps"].append({
                "description": f"{date_info.get('Type', 'Process')} date",
                "dateTime": date_info.get("Date", "")
            })

        return lineage

    def _convert_temporal(self, temporal: Dict[str, Any]) -> Dict[str, Any]:
        """Convert UMM temporal extent to DQ4EO format.

        :param temporal: UMM temporal extent
        :return: DQ4EO temporal extent
        """
        extent = {}

        if "RangeDateTime" in temporal:
            range_dt = temporal["RangeDateTime"]
            extent["begin"] = range_dt.get("BeginningDateTime", "")
            extent["end"] = range_dt.get("EndingDateTime", "")
        elif "SingleDateTime" in temporal:
            extent["instant"] = temporal["SingleDateTime"]

        return extent

    def _convert_collection_temporal(self, umm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert UMM Collection temporal extent to DQ4EO format.

        :param umm_data: UMM Collection data
        :return: DQ4EO temporal extent
        """
        extent = {}
        
        temporal_extents = umm_data.get("TemporalExtents", [])
        if temporal_extents:
            first_extent = temporal_extents[0]
            if "RangeDateTimes" in first_extent:
                range_dates = first_extent["RangeDateTimes"]
                if range_dates:
                    extent["begin"] = range_dates[0].get("BeginningDateTime", "")
                    extent["end"] = range_dates[0].get("EndingDateTime", "")
            elif "SingleDateTimes" in first_extent:
                singles = first_extent["SingleDateTimes"]
                if singles:
                    extent["instant"] = singles[0]

        return extent
