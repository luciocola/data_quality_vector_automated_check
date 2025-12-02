"""
UMM to STAC Converter Module

Converts NASA Unified Metadata Model (UMM) to STAC Items/Collections
with liability/claim extension support.
"""
import json
from datetime import datetime
from typing import Dict, Any, List, Optional


class UMMToSTACConverter:
    """Converter for UMM to STAC format with liability/claim extension."""

    def __init__(self):
        """Initialize the converter."""
        self.stac_version = "1.0.0"
        self.liability_claim_extension = "https://stac-extensions.github.io/liability-claims/v1.0.0/schema.json"

    def convert_umm_to_stac_item(self, umm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert UMM data to a STAC Item.

        :param umm_data: UMM data dictionary
        :type umm_data: Dict[str, Any]
        :return: STAC Item dictionary
        :rtype: Dict[str, Any]
        """
        stac_item = {
            "type": "Feature",
            "stac_version": self.stac_version,
            "stac_extensions": [self.liability_claim_extension],
            "id": self._extract_id(umm_data),
            "geometry": self._convert_geometry(umm_data),
            "bbox": self._calculate_bbox(umm_data),
            "properties": self._convert_properties(umm_data),
            "links": self._convert_links(umm_data),
            "assets": self._convert_assets(umm_data)
        }

        # Add liability/claim extension properties
        stac_item["properties"].update(self._extract_liability_claim_properties(umm_data))

        return stac_item

    def convert_umm_to_stac_collection(self, umm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert UMM collection to STAC Collection.

        :param umm_data: UMM collection data
        :type umm_data: Dict[str, Any]
        :return: STAC Collection dictionary
        :rtype: Dict[str, Any]
        """
        stac_collection = {
            "type": "Collection",
            "stac_version": self.stac_version,
            "stac_extensions": [self.liability_claim_extension],
            "id": self._extract_id(umm_data),
            "title": umm_data.get("EntryTitle", ""),
            "description": self._extract_description(umm_data),
            "keywords": self._extract_keywords(umm_data),
            "license": self._extract_license(umm_data),
            "providers": self._convert_providers(umm_data),
            "extent": self._convert_extent(umm_data),
            "summaries": self._convert_summaries(umm_data),
            "links": self._convert_links(umm_data)
        }

        # Add liability/claim extension at collection level
        stac_collection.update(self._extract_collection_liability_claim(umm_data))

        # Add quality information
        quality_info = self._extract_quality_information(umm_data)
        if quality_info:
            stac_collection["liability:quality"] = quality_info

        return stac_collection

    def _extract_id(self, umm_data: Dict[str, Any]) -> str:
        """Extract ID from UMM data.

        :param umm_data: UMM data
        :return: ID string
        """
        return umm_data.get("GranuleUR") or umm_data.get("ShortName", "unknown-id")

    def _convert_geometry(self, umm_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert UMM spatial extent to GeoJSON geometry.

        :param umm_data: UMM data
        :return: GeoJSON geometry or None
        """
        spatial = umm_data.get("SpatialExtent", {})
        
        if "HorizontalSpatialDomain" in spatial:
            geometry_data = spatial["HorizontalSpatialDomain"].get("Geometry", {})
            
            # Handle BoundingRectangle
            if "BoundingRectangle" in geometry_data:
                rect = geometry_data["BoundingRectangle"]
                west = rect.get("WestBoundingCoordinate", -180)
                east = rect.get("EastBoundingCoordinate", 180)
                north = rect.get("NorthBoundingCoordinate", 90)
                south = rect.get("SouthBoundingCoordinate", -90)
                
                return {
                    "type": "Polygon",
                    "coordinates": [[
                        [west, south],
                        [east, south],
                        [east, north],
                        [west, north],
                        [west, south]
                    ]]
                }
            
            # Handle Point
            if "Point" in geometry_data:
                point = geometry_data["Point"]
                return {
                    "type": "Point",
                    "coordinates": [
                        point.get("Longitude", 0),
                        point.get("Latitude", 0)
                    ]
                }
        
        return None

    def _calculate_bbox(self, umm_data: Dict[str, Any]) -> Optional[List[float]]:
        """Calculate bounding box from UMM spatial extent.

        :param umm_data: UMM data
        :return: Bounding box [west, south, east, north] or None
        """
        spatial = umm_data.get("SpatialExtent", {})
        
        if "HorizontalSpatialDomain" in spatial:
            geometry_data = spatial["HorizontalSpatialDomain"].get("Geometry", {})
            
            if "BoundingRectangle" in geometry_data:
                rect = geometry_data["BoundingRectangle"]
                return [
                    rect.get("WestBoundingCoordinate", -180),
                    rect.get("SouthBoundingCoordinate", -90),
                    rect.get("EastBoundingCoordinate", 180),
                    rect.get("NorthBoundingCoordinate", 90)
                ]
        
        return None

    def _convert_properties(self, umm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert UMM properties to STAC properties.

        :param umm_data: UMM data
        :return: STAC properties dictionary
        """
        properties = {
            "datetime": self._extract_datetime(umm_data),
            "created": umm_data.get("DataGranule", {}).get("ProductionDateTime"),
            "updated": umm_data.get("ProviderDates", [{}])[0].get("Date") if umm_data.get("ProviderDates") else None,
        }
        
        # Add platform/instrument info
        if "Platforms" in umm_data:
            platforms = umm_data["Platforms"]
            if platforms:
                properties["platform"] = platforms[0].get("ShortName", "")
                if "Instruments" in platforms[0]:
                    instruments = platforms[0]["Instruments"]
                    if instruments:
                        properties["instruments"] = [i.get("ShortName", "") for i in instruments]

        # Add collection reference
        if "CollectionReference" in umm_data:
            properties["collection"] = umm_data["CollectionReference"].get("ShortName", "")

        # Add quality information
        quality_info = self._extract_quality_information(umm_data)
        if quality_info:
            properties["liability:quality"] = quality_info

        return {k: v for k, v in properties.items() if v is not None}

    def _extract_datetime(self, umm_data: Dict[str, Any]) -> Optional[str]:
        """Extract datetime from UMM temporal extent.

        :param umm_data: UMM data
        :return: ISO 8601 datetime string
        """
        temporal = umm_data.get("TemporalExtent", {})
        
        if "RangeDateTime" in temporal:
            range_dt = temporal["RangeDateTime"]
            begin = range_dt.get("BeginningDateTime")
            if begin:
                return begin
        
        if "SingleDateTime" in temporal:
            return temporal["SingleDateTime"]
        
        return None

    def _extract_quality_information(self, umm_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract quality information from UMM DataQuality.

        :param umm_data: UMM data
        :return: ISO 19115-like quality report or None
        """
        if "DataQuality" not in umm_data:
            return None
        
        data_quality = umm_data["DataQuality"]
        quality_report = {}
        
        # Extract basic quality metadata
        if "QualityFlag" in data_quality:
            quality_report["summary"] = f"Quality Flag: {data_quality['QualityFlag']}"
        
        # Build quality elements array
        elements = []
        
        # Lineage
        if "Lineage" in data_quality:
            lineage = data_quality["Lineage"]
            elements.append({
                "elementType": "lineage",
                "summary": lineage if isinstance(lineage, str) else str(lineage),
                "detail": {
                    "type": "lineage",
                    "statement": lineage if isinstance(lineage, str) else str(lineage)
                }
            })
        
        # Positional accuracy
        if "HorizontalPositionalAccuracy" in data_quality:
            horiz_acc = data_quality["HorizontalPositionalAccuracy"]
            elements.append({
                "elementType": "positionalAccuracy",
                "summary": f"Horizontal accuracy: {horiz_acc}",
                "detail": {
                    "type": "positionalAccuracy",
                    "accuracyValue": float(horiz_acc) if isinstance(horiz_acc, (int, float, str)) else None,
                    "units": "m",
                    "measure": {
                        "description": "Horizontal positional accuracy",
                        "value": float(horiz_acc) if isinstance(horiz_acc, (int, float, str)) else None,
                        "valueType": "absolute",
                        "units": "m"
                    }
                }
            })
        
        if "VerticalPositionalAccuracy" in data_quality:
            vert_acc = data_quality["VerticalPositionalAccuracy"]
            elements.append({
                "elementType": "positionalAccuracy",
                "summary": f"Vertical accuracy: {vert_acc}",
                "detail": {
                    "type": "positionalAccuracy",
                    "accuracyValue": float(vert_acc) if isinstance(vert_acc, (int, float, str)) else None,
                    "units": "m",
                    "measure": {
                        "description": "Vertical positional accuracy",
                        "value": float(vert_acc) if isinstance(vert_acc, (int, float, str)) else None,
                        "valueType": "absolute",
                        "units": "m"
                    }
                }
            })
        
        # Completeness
        if "CompletenessReport" in data_quality:
            completeness = data_quality["CompletenessReport"]
            elements.append({
                "elementType": "completeness",
                "summary": completeness if isinstance(completeness, str) else str(completeness),
                "detail": {
                    "type": "completeness",
                    "scope": "dataset"
                }
            })
        
        # If we have elements, build the report
        if elements:
            quality_report["elements"] = elements
            
            # Add report metadata
            if "ProviderDates" in umm_data and umm_data["ProviderDates"]:
                quality_report["date"] = umm_data["ProviderDates"][0].get("Date")
            
            quality_report["scope"] = "dataset"
            
            return quality_report
        
        return None

    def _extract_liability_claim_properties(self, umm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract liability and claim related properties from UMM.

        :param umm_data: UMM data
        :return: Liability/claim properties
        """
        liability_props = {}
        
        # Extract use constraints (liability information)
        if "UseConstraints" in umm_data:
            use_constraints = umm_data["UseConstraints"]
            liability_props["liability:responsible_party"] = use_constraints.get("Description", "")
            if use_constraints.get("LicenseText"):
                liability_props["liability:notes"] = use_constraints.get("LicenseText", "")
            if use_constraints.get("LicenseURL", {}).get("URL"):
                liability_props["liability:evidence_refs"] = [use_constraints["LicenseURL"]["URL"]]
        
        # Extract access constraints (claim information)
        if "AccessConstraints" in umm_data:
            access_constraints = umm_data["AccessConstraints"]
            if access_constraints.get("Description"):
                if not liability_props.get("liability:notes"):
                    liability_props["liability:notes"] = access_constraints.get("Description", "")
            if access_constraints.get("Value"):
                liability_props["liability:damages_estimated"] = access_constraints.get("Value", 0)
        
        # Extract contact information for liability
        if "ContactPersons" in umm_data:
            contacts = umm_data["ContactPersons"]
            if contacts:
                contact_list = []
                for contact in contacts:
                    name = (contact.get("FirstName", "") + " " + contact.get("LastName", "")).strip()
                    email = contact.get("ContactInformation", {}).get("ContactMechanisms", [{}])[0].get("Value", "")
                    if name or email:
                        contact_list.append({
                            "name": name,
                            "role": "contact",
                            "contact": email
                        })
                if contact_list:
                    liability_props["liability:affected_parties"] = contact_list
        
        return liability_props

    def _extract_collection_liability_claim(self, umm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract collection-level liability/claim properties.

        :param umm_data: UMM collection data
        :return: Collection liability/claim properties
        """
        collection_props = {}
        
        # Collection-level liability information
        if "DataCenters" in umm_data:
            data_centers = umm_data["DataCenters"]
            if data_centers:
                org_name = data_centers[0].get("ShortName", "")
                roles = data_centers[0].get("Roles", [])
                collection_props["liability:responsible_party"] = org_name
                if roles:
                    collection_props["liability:origin"] = ", ".join(roles)
        
        return collection_props

    def _convert_links(self, umm_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert UMM related URLs to STAC links.

        :param umm_data: UMM data
        :return: List of STAC links
        """
        links = []
        
        # Self link
        links.append({
            "rel": "self",
            "href": "",  # Would be filled in with actual URL
            "type": "application/geo+json"
        })
        
        # Related URLs
        if "RelatedUrls" in umm_data:
            for url_obj in umm_data["RelatedUrls"]:
                link = {
                    "rel": url_obj.get("Type", "related").lower(),
                    "href": url_obj.get("URL", ""),
                }
                
                if "Description" in url_obj:
                    link["title"] = url_obj["Description"]
                
                if "MimeType" in url_obj:
                    link["type"] = url_obj["MimeType"]
                
                links.append(link)
        
        return links

    def _convert_assets(self, umm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert UMM data links to STAC assets.

        :param umm_data: UMM data
        :return: STAC assets dictionary
        """
        assets = {}
        
        if "RelatedUrls" in umm_data:
            for i, url_obj in enumerate(umm_data["RelatedUrls"]):
                url_type = url_obj.get("Type", "")
                
                # Only convert GET DATA type URLs to assets
                if "GET DATA" in url_type.upper():
                    asset_key = f"data_{i}"
                    assets[asset_key] = {
                        "href": url_obj.get("URL", ""),
                        "title": url_obj.get("Description", f"Data Asset {i}"),
                        "type": url_obj.get("MimeType", "application/octet-stream"),
                        "roles": ["data"]
                    }
        
        return assets

    def _extract_description(self, umm_data: Dict[str, Any]) -> str:
        """Extract description from UMM data.

        :param umm_data: UMM data
        :return: Description string
        """
        return umm_data.get("Abstract", "") or umm_data.get("Purpose", "")

    def _extract_keywords(self, umm_data: Dict[str, Any]) -> List[str]:
        """Extract keywords from UMM data.

        :param umm_data: UMM data
        :return: List of keywords
        """
        keywords = []
        
        if "ScienceKeywords" in umm_data:
            for sk in umm_data["ScienceKeywords"]:
                keywords.extend([
                    sk.get("Category", ""),
                    sk.get("Topic", ""),
                    sk.get("Term", "")
                ])
        
        return [k for k in keywords if k]

    def _extract_license(self, umm_data: Dict[str, Any]) -> str:
        """Extract license information from UMM.

        :param umm_data: UMM data
        :return: License string
        """
        if "UseConstraints" in umm_data:
            license_url = umm_data["UseConstraints"].get("LicenseURL", {}).get("URL", "")
            if license_url:
                return license_url
        
        return "proprietary"

    def _convert_providers(self, umm_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert UMM data centers to STAC providers.

        :param umm_data: UMM data
        :return: List of provider objects
        """
        providers = []
        
        if "DataCenters" in umm_data:
            for dc in umm_data["DataCenters"]:
                provider = {
                    "name": dc.get("ShortName", ""),
                    "roles": [role.lower() for role in dc.get("Roles", [])]
                }
                
                if "LongName" in dc:
                    provider["description"] = dc["LongName"]
                
                if "ContactInformation" in dc:
                    contact_info = dc["ContactInformation"]
                    if "ContactMechanisms" in contact_info:
                        for cm in contact_info["ContactMechanisms"]:
                            if cm.get("Type") == "Email":
                                provider["url"] = f"mailto:{cm.get('Value', '')}"
                                break
                
                providers.append(provider)
        
        return providers

    def _convert_extent(self, umm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert UMM spatial and temporal extent to STAC extent.

        :param umm_data: UMM data
        :return: STAC extent object
        """
        extent = {
            "spatial": {
                "bbox": [[]]
            },
            "temporal": {
                "interval": [[None, None]]
            }
        }
        
        # Spatial extent
        bbox = self._calculate_bbox(umm_data)
        if bbox:
            extent["spatial"]["bbox"] = [bbox]
        
        # Temporal extent
        if "TemporalExtents" in umm_data and umm_data["TemporalExtents"]:
            temp_extent = umm_data["TemporalExtents"][0]
            if "RangeDateTime" in temp_extent:
                range_dt = temp_extent["RangeDateTime"]
                extent["temporal"]["interval"] = [[
                    range_dt.get("BeginningDateTime"),
                    range_dt.get("EndingDateTime")
                ]]
        
        return extent

    def _convert_summaries(self, umm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert UMM metadata to STAC summaries.

        :param umm_data: UMM data
        :return: Summaries dictionary
        """
        summaries = {}
        
        # Platform summaries
        if "Platforms" in umm_data:
            platforms = [p.get("ShortName", "") for p in umm_data["Platforms"]]
            if platforms:
                summaries["platform"] = platforms
        
        # Instrument summaries
        instruments = []
        if "Platforms" in umm_data:
            for platform in umm_data["Platforms"]:
                if "Instruments" in platform:
                    instruments.extend([i.get("ShortName", "") for i in platform["Instruments"]])
        if instruments:
            summaries["instruments"] = instruments
        
        return summaries

    def convert_file(self, input_path: str, output_path: str, 
                     conversion_type: str = "item") -> bool:
        """Convert a UMM JSON file to STAC format.

        :param input_path: Path to input UMM JSON file
        :param output_path: Path to output STAC JSON file
        :param conversion_type: Type of conversion ('item' or 'collection')
        :return: True if successful, False otherwise
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                umm_data = json.load(f)
            
            if conversion_type == "collection":
                stac_data = self.convert_umm_to_stac_collection(umm_data)
            else:
                stac_data = self.convert_umm_to_stac_item(umm_data)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(stac_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error converting file: {e}")
            return False
