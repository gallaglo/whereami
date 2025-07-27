import logging
import os
import json
from typing import Dict, List, Optional
from langchain_core.tools import tool
from google.cloud import compute_v1
from google.cloud import resourcemanager_v3
import requests

class GCPTools:
    """Tools for interacting with GCP APIs to get region and service information"""
    
    def __init__(self):
        self.project_id = os.environ.get("PROJECT_ID")
        if not self.project_id:
            logging.warning("PROJECT_ID not set, some GCP tools may not work")
    
    @tool
    def get_gcp_region_info(region: str) -> str:
        """
        Get detailed information about a specific GCP region including available services and zones.
        
        Args:
            region: The GCP region name (e.g., 'us-central1', 'europe-west1')
            
        Returns:
            JSON string with region details including zones, available services, and location
        """
        try:
            project_id = os.environ.get("PROJECT_ID")
            
            if not project_id:
                return json.dumps({"error": "PROJECT_ID not configured"})
            
            client = compute_v1.RegionsClient()
            
            # Get region details
            region_info = client.get(project=project_id, region=region)
            
            # Get zones in this region
            zones_client = compute_v1.ZonesClient()
            zones = zones_client.list(project=project_id)
            region_zones = [zone.name for zone in zones if zone.region.endswith(f"/{region}")]
            
            result = {
                "region": region_info.name,
                "description": region_info.description,
                "status": region_info.status,
                "zones": region_zones,
                "quotas": [{"metric": quota.metric, "limit": quota.limit} for quota in region_info.quotas][:5],  # Limit to first 5
                "deprecated": getattr(region_info, 'deprecated', None) is not None
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logging.error(f"Error getting GCP region info for {region}: {str(e)}")
            return json.dumps({"error": f"Failed to get region info: {str(e)}"})
    
    @tool
    def list_gcp_regions() -> str:
        """
        List all available GCP regions with their basic information.
        
        Returns:
            JSON string with list of all GCP regions and their locations
        """
        try:
            project_id = os.environ.get("PROJECT_ID")
            
            if not project_id:
                return json.dumps({"error": "PROJECT_ID not configured"})
            
            client = compute_v1.RegionsClient()
            
            regions = client.list(project=project_id)
            
            result = []
            for region in regions:
                result.append({
                    "name": region.name,
                    "description": region.description,
                    "status": region.status,
                    "zone_count": len([zone for zone in region.zones])
                })
            
            return json.dumps({"regions": result}, indent=2)
            
        except Exception as e:
            logging.error(f"Error listing GCP regions: {str(e)}")
            return json.dumps({"error": f"Failed to list regions: {str(e)}"})
    
    @tool
    def get_gcp_services_in_region(region: str) -> str:
        """
        Get information about GCP services available in a specific region.
        Note: This is a simplified implementation. Full service availability requires Service Usage API.
        
        Args:
            region: The GCP region name (e.g., 'us-central1')
            
        Returns:
            JSON string with information about services in the region
        """
        try:
            # Common GCP services and their general availability
            # In a full implementation, you'd use the Service Usage API
            common_services = {
                "compute": "Compute Engine - Virtual machines and infrastructure",
                "storage": "Cloud Storage - Object storage service", 
                "bigquery": "BigQuery - Data warehouse and analytics",
                "cloudsql": "Cloud SQL - Managed relational databases",
                "gke": "Google Kubernetes Engine - Managed Kubernetes",
                "functions": "Cloud Functions - Serverless compute",
                "run": "Cloud Run - Serverless containers",
                "dataflow": "Dataflow - Stream and batch data processing",
                "pubsub": "Pub/Sub - Messaging service",
                "firestore": "Firestore - NoSQL document database"
            }
            
            # Most services are available in major regions
            # This is a simplified check - in reality you'd query the actual APIs
            major_regions = ['us-central1', 'us-east1', 'us-west1', 'europe-west1', 'asia-east1']
            
            if region in major_regions:
                available_services = common_services
                note = "This is a major region with full service availability"
            else:
                # Some services might have limited availability in smaller regions
                available_services = {k: v for k, v in common_services.items() if k in ['compute', 'storage', 'cloudsql']}
                note = "This region may have limited service availability. Check GCP documentation for specific services."
            
            result = {
                "region": region,
                "note": note,
                "available_services": available_services,
                "service_count": len(available_services)
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logging.error(f"Error getting services for region {region}: {str(e)}")
            return json.dumps({"error": f"Failed to get services info: {str(e)}"})

# Create instances of the tools for easy import
gcp_tools = GCPTools()
get_gcp_region_info = gcp_tools.get_gcp_region_info
list_gcp_regions = gcp_tools.list_gcp_regions  
get_gcp_services_in_region = gcp_tools.get_gcp_services_in_region