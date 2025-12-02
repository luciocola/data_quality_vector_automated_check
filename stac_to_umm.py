"""
STAC to UMM Converter Module

Converts STAC Items/Collections with liability/claim extension
to NASA Unified Metadata Model (UMM) format.
"""
import json
from typing import Dict, Any, List, Optional


class STACToUMMConverter:
    """Converter for STAC to UMM format with liability/claim extension support."""

    def __init__(self):
        """Initialize the converter."""
        self.umm_version = "1.6.4"

    def convert_stac_item_to_umm(self, stac_item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert STAC Item to UMM Granule format.

        :param stac_item: STAC Item dictionary
        :type stac_item: Dict[str, Any]
        :return: UMM Granule dictionary
        :rtype: Dict[str, Any]
        """
        umm_granule = {
            "GranuleUR": stac_item.get("id", ""),
            "ProviderDates": self._convert_provider_dates(stac_item),
            "CollectionReference": self._extract_collection_reference(stac_item),
            "DataGranule": self._convert_data_granule(stac_item),
            "TemporalExtent": self._convert_temporal_extent(stac_item),
            "SpatialExtent": self._convert_spatial_extent(stac_item),
            "RelatedUrls": self._convert_related_urls(stac_item),
        }

        # Add liability/claim properties from extension
        umm_granule.update(self._extract_umm_liability_claim(stac_item))

        # Add quality information from STAC
        quality_info = self._extract_umm_quality(stac_item)
        if quality_info:
            umm_granule["DataQuality"] = quality_info

        # Remove None values
        return {k: v for k, v in umm_granule.items() if v is not None}

    def convert_stac_collection_to_umm(self, stac_collection: Dict[str, Any]) -> Dict[str, Any]:
        """Convert STAC Collection to UMM Collection format.

        :param stac_collection: STAC Collection dictionary
        :type stac_collection: Dict[str, Any]
        :return: UMM Collection dictionary
        :rtype: Dict[str, Any]
        """
        umm_collection = {
            "ShortName": stac_collection.get("id", ""),
            "EntryTitle": stac_collection.get("title", ""),
            "Abstract": stac_collection.get("description", ""),
            "DataCenters": self._convert_data_centers(stac_collection),
            "Platforms": self._convert_platforms(stac_collection),
            "TemporalExtents": self._convert_collection_temporal_extent(stac_collection),
            "SpatialExtent": self._convert_spatial_extent(stac_collection),
            "ScienceKeywords": self._convert_science_keywords(stac_collection),
            "RelatedUrls": self._convert_related_urls(stac_collection),
        }

        # Add license information
        if "license" in stac_collection:
            umm_collection["UseConstraints"] = {
                "LicenseURL": {
                    "URL": stac_collection["license"]
                }
            }

        # Add liability/claim extension properties
        umm_collection.update(self._extract_umm_collection_liability_claim(stac_collection))

        # Add quality information from STAC
        quality_info = self._extract_umm_quality(stac_collection)
        if quality_info:
            umm_collection["DataQuality"] = quality_info

        # Remove None values
        return {k: v for k, v in umm_collection.items() if v is not None}

    def _convert_provider_dates(self, stac_item: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert STAC datetime properties to UMM ProviderDates.

        :param stac_item: STAC Item
        :return: List of provider dates
        """
        provider_dates = []
        props = stac_item.get("properties", {})

        if "created" in props:
            provider_dates.append({
                "Date": props["created"],
                "Type": "Create"
            })

        if "updated" in props:
            provider_dates.append({
                "Date": props["updated"],
                "Type": "Update"
            })

        return provider_dates if provider_dates else None

    def _extract_collection_reference(self, stac_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract collection reference from STAC Item.

        :param stac_item: STAC Item
        :return: Collection reference or None
        """
        props = stac_item.get("properties", {})
        
        if "collection" in props:
            return {
                "ShortName": props["collection"]
            }
        
        # Check for collection link
        links = stac_item.get("links", [])
        for link in links:
            if link.get("rel") == "collection":
                return {
                    "ShortName": link.get("href", "").split("/")[-1]
                }
        
        return None

    def _convert_data_granule(self, stac_item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert STAC properties to UMM DataGranule.

        :param stac_item: STAC Item
        :return: DataGranule object
        """
        props = stac_item.get("properties", {})
        data_granule = {}

        if "created" in props:
            data_granule["ProductionDateTime"] = props["created"]

        # Calculate size from assets
        assets = stac_item.get("assets", {})
        total_size = 0
        for asset in assets.values():
            if "file:size" in asset:
                total_size += asset["file:size"]
        
        if total_size > 0:
            data_granule["SizeMBDataGranule"] = total_size / (1024 * 1024)

        return data_granule if data_granule else None

    def _convert_temporal_extent(self, stac_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert STAC datetime to UMM TemporalExtent.

        :param stac_item: STAC Item
        :return: TemporalExtent object or None
        """
        props = stac_item.get("properties", {})
        
        if "datetime" in props and props["datetime"]:
            return {
                "SingleDateTime": props["datetime"]
            }
        
        # Handle start/end datetime
        if "start_datetime" in props and "end_datetime" in props:
            return {
                "RangeDateTime": {
                    "BeginningDateTime": props["start_datetime"],
                    "EndingDateTime": props["end_datetime"]
                }
            }
        
        return None

    def _convert_spatial_extent(self, stac_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert STAC geometry/bbox to UMM SpatialExtent.

        :param stac_data: STAC Item or Collection
        :return: SpatialExtent object or None
        """
        spatial_extent = None

        # For STAC Items
        if "geometry" in stac_data:
            geometry = stac_data["geometry"]
            if geometry:
                spatial_extent = {
                    "HorizontalSpatialDomain": {
                        "Geometry": self._convert_geometry_to_umm(geometry)
                    }
                }
        
        # For STAC Collections
        elif "extent" in stac_data and "spatial" in stac_data["extent"]:
            bbox_list = stac_data["extent"]["spatial"].get("bbox", [])
            if bbox_list and bbox_list[0]:
                bbox = bbox_list[0]
                spatial_extent = {
                    "HorizontalSpatialDomain": {
                        "Geometry": {
                            "BoundingRectangle": {
                                "WestBoundingCoordinate": bbox[0],
                                "SouthBoundingCoordinate": bbox[1],
                                "EastBoundingCoordinate": bbox[2],
                                "NorthBoundingCoordinate": bbox[3]
                            }
                        }
                    }
                }
        
        # Also check bbox in item
        elif "bbox" in stac_data:
            bbox = stac_data["bbox"]
            if bbox:
                spatial_extent = {
                    "HorizontalSpatialDomain": {
                        "Geometry": {
                            "BoundingRectangle": {
                                "WestBoundingCoordinate": bbox[0],
                                "SouthBoundingCoordinate": bbox[1],
                                "EastBoundingCoordinate": bbox[2],
                                "NorthBoundingCoordinate": bbox[3]
                            }
                        }
                    }
                }

        return spatial_extent

    def _convert_geometry_to_umm(self, geometry: Dict[str, Any]) -> Dict[str, Any]:
        """Convert GeoJSON geometry to UMM Geometry.

        :param geometry: GeoJSON geometry
        :return: UMM Geometry object
        """
        geom_type = geometry.get("type")
        coordinates = geometry.get("coordinates")

        if geom_type == "Point":
            return {
                "Point": {
                    "Longitude": coordinates[0],
                    "Latitude": coordinates[1]
                }
            }
        elif geom_type == "Polygon":
            # Calculate bounding rectangle from polygon
            lons = [coord[0] for coord in coordinates[0]]
            lats = [coord[1] for coord in coordinates[0]]
            
            return {
                "BoundingRectangle": {
                    "WestBoundingCoordinate": min(lons),
                    "SouthBoundingCoordinate": min(lats),
                    "EastBoundingCoordinate": max(lons),
                    "NorthBoundingCoordinate": max(lats)
                }
            }
        
        return {}

    def _convert_related_urls(self, stac_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert STAC links and assets to UMM RelatedUrls.

        :param stac_data: STAC Item or Collection
        :return: List of RelatedUrl objects
        """
        related_urls = []

        # Convert links
        links = stac_data.get("links", [])
        for link in links:
            rel = link.get("rel", "")
            if rel not in ["self", "root", "parent"]:
                url_obj = {
                    "URL": link.get("href", ""),
                    "Type": self._map_link_rel_to_umm_type(rel)
                }
                
                if "title" in link:
                    url_obj["Description"] = link["title"]
                
                if "type" in link:
                    url_obj["MimeType"] = link["type"]
                
                related_urls.append(url_obj)

        # Convert assets (for Items)
        assets = stac_data.get("assets", {})
        for asset_key, asset in assets.items():
            url_obj = {
                "URL": asset.get("href", ""),
                "Type": "GET DATA",
                "Description": asset.get("title", asset_key)
            }
            
            if "type" in asset:
                url_obj["MimeType"] = asset["type"]
            
            related_urls.append(url_obj)

        return related_urls if related_urls else None

    def _map_link_rel_to_umm_type(self, rel: str) -> str:
        """Map STAC link rel to UMM URL Type.

        :param rel: STAC link relation
        :return: UMM URL Type
        """
        mapping = {
            "license": "VIEW RELATED INFORMATION",
            "about": "VIEW RELATED INFORMATION",
            "describedby": "VIEW RELATED INFORMATION",
            "via": "VIEW RELATED INFORMATION",
            "alternate": "GET DATA",
            "item": "GET DATA",
            "child": "VIEW RELATED INFORMATION",
            "collection": "VIEW RELATED INFORMATION"
        }
        
        return mapping.get(rel.lower(), "VIEW RELATED INFORMATION")

    def _convert_data_centers(self, stac_collection: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert STAC providers to UMM DataCenters.

        :param stac_collection: STAC Collection
        :return: List of DataCenter objects
        """
        data_centers = []
        providers = stac_collection.get("providers", [])

        for provider in providers:
            data_center = {
                "ShortName": provider.get("name", ""),
                "Roles": [role.upper() for role in provider.get("roles", [])]
            }
            
            if "description" in provider:
                data_center["LongName"] = provider["description"]
            
            if "url" in provider:
                data_center["ContactInformation"] = {
                    "ContactMechanisms": [{
                        "Type": "Email" if "mailto:" in provider["url"] else "URL",
                        "Value": provider["url"].replace("mailto:", "")
                    }]
                }
            
            data_centers.append(data_center)

        return data_centers if data_centers else None

    def _convert_platforms(self, stac_collection: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert STAC platform information to UMM Platforms.

        :param stac_collection: STAC Collection
        :return: List of Platform objects
        """
        platforms = []
        summaries = stac_collection.get("summaries", {})

        platform_names = summaries.get("platform", [])
        instrument_names = summaries.get("instruments", [])

        for platform_name in platform_names:
            platform = {
                "ShortName": platform_name,
                "Type": "Earth Observation Satellites"
            }
            
            if instrument_names:
                platform["Instruments"] = [
                    {"ShortName": inst} for inst in instrument_names
                ]
            
            platforms.append(platform)

        return platforms if platforms else None

    def _convert_collection_temporal_extent(self, stac_collection: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert STAC temporal extent to UMM TemporalExtents.

        :param stac_collection: STAC Collection
        :return: List of TemporalExtent objects
        """
        temporal_extents = []
        extent = stac_collection.get("extent", {})
        temporal = extent.get("temporal", {})
        intervals = temporal.get("interval", [])

        for interval in intervals:
            if interval and len(interval) >= 2:
                temporal_extent = {
                    "RangeDateTime": {
                        "BeginningDateTime": interval[0],
                        "EndingDateTime": interval[1]
                    }
                }
                temporal_extents.append(temporal_extent)

        return temporal_extents if temporal_extents else None

    def _convert_science_keywords(self, stac_collection: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert STAC keywords to UMM ScienceKeywords.

        :param stac_collection: STAC Collection
        :return: List of ScienceKeyword objects
        """
        science_keywords = []
        keywords = stac_collection.get("keywords", [])

        # Group keywords into science keyword structure
        # This is a simplified conversion - real UMM uses a controlled vocabulary
        for i in range(0, len(keywords), 3):
            keyword_group = keywords[i:i+3]
            science_keyword = {}
            
            if len(keyword_group) > 0:
                science_keyword["Category"] = keyword_group[0]
            if len(keyword_group) > 1:
                science_keyword["Topic"] = keyword_group[1]
            if len(keyword_group) > 2:
                science_keyword["Term"] = keyword_group[2]
            
            if science_keyword:
                science_keywords.append(science_keyword)

        return science_keywords if science_keywords else None

    def _extract_umm_quality(self, stac_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract UMM DataQuality from STAC liability:quality field.

        :param stac_item: STAC Item
        :return: UMM DataQuality object or None
        """
        props = stac_item.get("properties", {})
        
        if "liability:quality" not in props:
            return None
        
        quality_data = props["liability:quality"]
        umm_quality = {}
        
        # Handle both single quality report and array
        quality_reports = quality_data if isinstance(quality_data, list) else [quality_data]
        
        for report in quality_reports:
            # Extract summary as quality flag
            if "summary" in report:
                umm_quality["QualityFlag"] = report["summary"]
            
            # Process quality elements
            if "elements" in report:
                for element in report["elements"]:
                    element_type = element.get("elementType", "")
                    detail = element.get("detail", {})
                    
                    # Lineage
                    if element_type == "lineage":
                        if "statement" in detail:
                            umm_quality["Lineage"] = detail["statement"]
                        elif "summary" in element:
                            umm_quality["Lineage"] = element["summary"]
                    
                    # Positional Accuracy
                    elif element_type == "positionalAccuracy":
                        accuracy_value = detail.get("accuracyValue")
                        measure = detail.get("measure", {})
                        
                        # Determine if horizontal or vertical
                        description = measure.get("description", "").lower()
                        if "vertical" in description or "elevation" in description:
                            if accuracy_value:
                                umm_quality["VerticalPositionalAccuracy"] = accuracy_value
                        else:
                            if accuracy_value:
                                umm_quality["HorizontalPositionalAccuracy"] = accuracy_value
                    
                    # Completeness
                    elif element_type == "completeness":
                        if "summary" in element:
                            umm_quality["CompletenessReport"] = element["summary"]
                        elif detail.get("measure", {}).get("description"):
                            umm_quality["CompletenessReport"] = detail["measure"]["description"]
                    
                    # Thematic/Attribute Accuracy
                    elif element_type in ["thematicAccuracy", "attributeAccuracy"]:
                        measure = detail.get("measure", {})
                        if measure.get("description"):
                            if "ThematicAccuracy" not in umm_quality:
                                umm_quality["ThematicAccuracy"] = {}
                            umm_quality["ThematicAccuracy"]["Description"] = measure["description"]
                            if measure.get("value"):
                                umm_quality["ThematicAccuracy"]["Value"] = measure["value"]
        
        return umm_quality if umm_quality else None

    def _extract_umm_liability_claim(self, stac_item: Dict[str, Any]) -> Dict[str, Any]:
        """Extract UMM liability/claim properties from STAC extension.

        :param stac_item: STAC Item
        :return: UMM liability/claim properties
        """
        umm_props = {}
        props = stac_item.get("properties", {})

        # Extract liability information
        if "liability:responsible_party" in props:
            umm_props["UseConstraints"] = {
                "Description": props.get("liability:responsible_party", "")
            }
            if "liability:notes" in props:
                umm_props["UseConstraints"]["LicenseText"] = props["liability:notes"]
            if "liability:evidence_refs" in props and props["liability:evidence_refs"]:
                umm_props["UseConstraints"]["LicenseURL"] = {
                    "URL": props["liability:evidence_refs"][0]
                }

        # Extract claim information
        if "liability:damages_estimated" in props or "liability:notes" in props:
            umm_props["AccessConstraints"] = {}
            if "liability:notes" in props:
                umm_props["AccessConstraints"]["Description"] = props["liability:notes"]
            if "liability:damages_estimated" in props:
                umm_props["AccessConstraints"]["Value"] = props["liability:damages_estimated"]

        # Extract liability contact
        if "liability:affected_parties" in props:
            affected_parties = props["liability:affected_parties"]
            contact_persons = []
            for party in affected_parties:
                name_parts = party.get("name", "").split(" ", 1)
                contact_person = {
                    "FirstName": name_parts[0] if name_parts else "",
                    "LastName": name_parts[1] if len(name_parts) > 1 else "",
                    "ContactInformation": {
                        "ContactMechanisms": [{
                            "Type": "Email",
                            "Value": party.get("contact", "")
                        }]
                    }
                }
                contact_persons.append(contact_person)
            if contact_persons:
                umm_props["ContactPersons"] = contact_persons

        return umm_props

    def _extract_umm_collection_liability_claim(self, stac_collection: Dict[str, Any]) -> Dict[str, Any]:
        """Extract collection-level UMM liability/claim properties.

        :param stac_collection: STAC Collection
        :return: UMM collection liability/claim properties
        """
        umm_props = {}

        # Extract data provider liability
        if "liability:responsible_party" in stac_collection:
            if "DataCenters" not in umm_props:
                umm_props["DataCenters"] = []
            
            roles = []
            if "liability:origin" in stac_collection:
                roles = stac_collection["liability:origin"].split(", ")
            
            umm_props["DataCenters"].append({
                "ShortName": stac_collection.get("liability:responsible_party", ""),
                "Roles": roles
            })

        return umm_props

    def convert_file(self, input_path: str, output_path: str,
                     conversion_type: str = "item") -> bool:
        """Convert a STAC JSON file to UMM format.

        :param input_path: Path to input STAC JSON file
        :param output_path: Path to output UMM JSON file
        :param conversion_type: Type of conversion ('item' or 'collection')
        :return: True if successful, False otherwise
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                stac_data = json.load(f)
            
            if conversion_type == "collection":
                umm_data = self.convert_stac_collection_to_umm(stac_data)
            else:
                umm_data = self.convert_stac_item_to_umm(stac_data)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(umm_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error converting file: {e}")
            return False
