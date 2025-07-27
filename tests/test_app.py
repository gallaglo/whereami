#!/usr/bin/env python3
"""
Unit tests for the main Flask application
"""

import unittest
import json
import os
import sys
from unittest.mock import patch, MagicMock

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestApp(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Set required environment variables
        os.environ['PROJECT_ID'] = 'test-project'
        
        # Mock the app import to avoid issues with missing dependencies
        with patch('app.ChatService'), \
             patch('app.genai'), \
             patch('app.whereami_payload'):
            from app import app
            self.app = app
            self.client = app.test_client()
            app.config['TESTING'] = True

    def test_health_endpoint(self):
        """Test the health check endpoint"""
        response = self.client.get('/healthz')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.decode(), 'OK')

    def test_api_endpoint_without_path(self):
        """Test the API endpoint without specific path"""
        with patch('app.whereami_payload') as mock_payload:
            mock_payload.build_payload.return_value = {
                'zone': 'us-central1-a',
                'region': 'us-central1',
                'cluster_name': 'test-cluster'
            }
            
            response = self.client.get('/api/')
            self.assertEqual(response.status_code, 200)
            
            # Should return JSON
            data = json.loads(response.data)
            self.assertIn('zone', data)
            self.assertIn('region', data)

    def test_api_endpoint_with_specific_value(self):
        """Test the API endpoint requesting a specific value"""
        with patch('app.whereami_payload') as mock_payload:
            mock_payload.build_payload.return_value = {
                'zone': 'us-central1-a',
                'region': 'us-central1'
            }
            
            response = self.client.get('/api/zone')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data.decode(), 'us-central1-a')

    def test_home_endpoint_without_prompt(self):
        """Test the home endpoint without a prompt"""
        with patch('app.whereami_payload') as mock_payload, \
             patch('app._get_location_from_json_list') as mock_location:
            
            mock_payload.build_payload.return_value = {
                'region': 'us-central1'
            }
            mock_location.return_value = 'Iowa'
            
            response = self.client.get('/')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Hello from us-central1', response.data)

    def test_generate_endpoint_without_prompt(self):
        """Test the generate endpoint without a prompt parameter"""
        response = self.client.get('/generate')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'No prompt provided')

    def test_region_extraction_from_zone(self):
        """Test the _get_region helper function"""
        from app import _get_region
        
        self.assertEqual(_get_region('us-central1-a'), 'us-central1')
        self.assertEqual(_get_region('europe-west1-b'), 'europe-west1')
        self.assertEqual(_get_region('asia-east1-c'), 'asia-east1')

if __name__ == '__main__':
    unittest.main()