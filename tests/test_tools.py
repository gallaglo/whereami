#!/usr/bin/env python3
"""
Unit tests for GCP and Weather tools
"""

import unittest
import json
import os
import sys
from unittest.mock import patch, MagicMock

# Add parent directory to path to import tool modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestGCPTools(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        os.environ['PROJECT_ID'] = 'test-project'

    @patch('gcp_tools.compute_v1.RegionsClient')
    def test_get_gcp_region_info_success(self, mock_client):
        """Test successful GCP region info retrieval"""
        # Mock the region response
        mock_region = MagicMock()
        mock_region.name = 'us-central1'
        mock_region.description = 'Central US region'
        mock_region.status = 'UP'
        mock_region.quotas = []
        
        # Mock the zones response
        mock_zone = MagicMock()
        mock_zone.name = 'us-central1-a'
        mock_zone.region = 'projects/test-project/regions/us-central1'
        
        mock_client.return_value.get.return_value = mock_region
        
        with patch('gcp_tools.compute_v1.ZonesClient') as mock_zones:
            mock_zones.return_value.list.return_value = [mock_zone]
            
            from gcp_tools import get_gcp_region_info
            result = get_gcp_region_info.func('us-central1')
            
            data = json.loads(result)
            self.assertEqual(data['region'], 'us-central1')
            self.assertEqual(data['description'], 'Central US region')
            self.assertIn('zones', data)

    def test_get_gcp_region_info_no_project(self):
        """Test GCP region info when PROJECT_ID is not set"""
        del os.environ['PROJECT_ID']
        
        from gcp_tools import get_gcp_region_info
        result = get_gcp_region_info.func('us-central1')
        
        data = json.loads(result)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'PROJECT_ID not configured')

    def test_get_gcp_services_in_region_major(self):
        """Test GCP services info for major region"""
        from gcp_tools import get_gcp_services_in_region
        result = get_gcp_services_in_region.func('us-central1')
        
        data = json.loads(result)
        self.assertEqual(data['region'], 'us-central1')
        self.assertIn('available_services', data)
        self.assertIn('compute', data['available_services'])
        self.assertGreater(data['service_count'], 5)

    def test_get_gcp_services_in_region_minor(self):
        """Test GCP services info for minor region"""
        from gcp_tools import get_gcp_services_in_region
        result = get_gcp_services_in_region.func('us-west4')
        
        data = json.loads(result)
        self.assertEqual(data['region'], 'us-west4')
        self.assertIn('available_services', data)
        self.assertLessEqual(data['service_count'], 5)

class TestWeatherTools(unittest.TestCase):
    
    def test_get_current_weather_no_api_key(self):
        """Test weather API when no API key is configured"""
        # Ensure no API key is set
        if 'OPENWEATHER_API_KEY' in os.environ:
            del os.environ['OPENWEATHER_API_KEY']
        
        from weather_tools import get_current_weather
        result = get_current_weather.func('Mountain View, CA')
        
        data = json.loads(result)
        self.assertEqual(data['location'], 'Mountain View, CA')
        self.assertIn('note', data)
        self.assertIn('mock data', data['note'])

    @patch('weather_tools.requests.get')
    def test_get_current_weather_with_api(self, mock_get):
        """Test weather API with mocked successful response"""
        os.environ['OPENWEATHER_API_KEY'] = 'test-key'
        
        # Mock the geocoding response
        geo_response = MagicMock()
        geo_response.json.return_value = [{
            'name': 'Mountain View',
            'country': 'US',
            'lat': 37.4419,
            'lon': -122.1430
        }]
        geo_response.raise_for_status.return_value = None
        
        # Mock the weather response
        weather_response = MagicMock()
        weather_response.json.return_value = {
            'main': {
                'temp': 20,
                'feels_like': 18,
                'humidity': 65,
                'pressure': 1013
            },
            'weather': [{'description': 'clear sky'}],
            'wind': {'speed': 3.5},
            'clouds': {'all': 10},
            'visibility': 10000
        }
        weather_response.raise_for_status.return_value = None
        
        # Configure mock to return different responses for different URLs
        def side_effect(url, **kwargs):
            if 'geo' in url:
                return geo_response
            else:
                return weather_response
        
        mock_get.side_effect = side_effect
        
        from weather_tools import get_current_weather
        result = get_current_weather.func('Mountain View, CA')
        
        data = json.loads(result)
        self.assertIn('Mountain View', data['location'])
        self.assertEqual(data['temperature']['celsius'], 20)
        self.assertIn('clear sky', data['condition'].lower())

    def test_get_weather_forecast_no_api_key(self):
        """Test weather forecast when no API key is configured"""
        if 'OPENWEATHER_API_KEY' in os.environ:
            del os.environ['OPENWEATHER_API_KEY']
        
        from weather_tools import get_weather_forecast
        result = get_weather_forecast.func('London, UK', 3)
        
        data = json.loads(result)
        self.assertEqual(data['location'], 'London, UK')
        self.assertIn('note', data)
        self.assertEqual(data['forecast'], [])

if __name__ == '__main__':
    unittest.main()