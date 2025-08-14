import logging
import os
import json
import requests
from typing import Dict, Optional
from langchain_core.tools import tool

class WeatherTools:
    """Tools for getting weather information for locations"""
    
    def __init__(self):
        # Using OpenWeatherMap API (free tier available)
        # You can also use other weather APIs like WeatherAPI, etc.
        self.api_key = os.environ.get("OPENWEATHER_API_KEY")
        self.base_url = "http://api.openweathermap.org/data/2.5"
        
        # Validate API key on initialization
        self._validate_api_key()
        
    def _validate_api_key(self):
        """Validate the API key and log warnings for invalid configurations"""
        invalid_keys = ["placeholder", "your-api-key-here", "test", "demo", "example"]
        
        if not self.api_key:
            logging.warning("OPENWEATHER_API_KEY environment variable is not set. Weather tools will use mock data.")
        elif self.api_key.lower() in invalid_keys:
            logging.warning(
                f"OPENWEATHER_API_KEY is set to an invalid placeholder value: '{self.api_key}'. "
                "Please update the secret in Google Secret Manager with your actual OpenWeather API key. "
                "Weather tools will use mock data until a valid API key is provided."
            )
            # Set to None to trigger mock data behavior
            self.api_key = None
        elif len(self.api_key) < 10:
            logging.warning(
                f"OPENWEATHER_API_KEY appears to be too short ({len(self.api_key)} characters). "
                "OpenWeather API keys are typically 32 characters long. "
                "Weather tools will attempt to use this key but may return errors."
            )
        else:
            logging.info("OPENWEATHER_API_KEY is configured and appears valid.")
    
    def _is_api_key_valid(self) -> bool:
        """Check if the API key is configured and not a placeholder value"""
        return self.api_key is not None and len(self.api_key) >= 10
        
    @tool
    def get_current_weather(location: str) -> str:
        """
        Get current weather information for a specific location.
        
        Args:
            location: The location name (city, city+country, etc.) e.g., "Mountain View, CA" or "London, UK"
            
        Returns:
            JSON string with current weather data including temperature, conditions, humidity
        """
        try:
            api_key = os.environ.get("OPENWEATHER_API_KEY")
            
            # Enhanced validation logic
            weather_tools_instance = WeatherTools()
            
            if not weather_tools_instance._is_api_key_valid():
                logging.info(f"Using mock weather data for location: {location}")
                # Enhanced mock response with more realistic data
                return json.dumps({
                    "location": location,
                    "note": "Weather API key not configured or invalid. Using mock data.",
                    "mock_data": True,
                    "temperature": {
                        "celsius": 20.5,
                        "fahrenheit": 68.9,
                        "feels_like_celsius": 22.0
                    },
                    "condition": "Partly Cloudy",
                    "humidity": "45%",
                    "pressure": "1013 hPa",
                    "wind_speed": "10 km/h",
                    "visibility": "10000 meters",
                    "cloud_cover": "25%",
                    "coordinates": {"lat": 0.0, "lon": 0.0}
                }, indent=2)
            
            # Get coordinates first
            geo_url = f"http://api.openweathermap.org/geo/1.0/direct"
            geo_params = {
                "q": location,
                "limit": 1,
                "appid": api_key
            }
            
            geo_response = requests.get(geo_url, params=geo_params, timeout=10)
            
            # Check for API key authentication errors
            if geo_response.status_code == 401:
                logging.error("OpenWeather API returned 401 Unauthorized. Please check your API key.")
                return json.dumps({
                    "error": "Invalid API key. Please check your OpenWeather API key configuration.",
                    "location": location,
                    "api_error": True
                })
            
            geo_response.raise_for_status()
            geo_data = geo_response.json()
            
            if not geo_data:
                return json.dumps({"error": f"Location '{location}' not found"})
            
            lat = geo_data[0]["lat"]
            lon = geo_data[0]["lon"]
            
            # Get weather data
            weather_url = f"http://api.openweathermap.org/data/2.5/weather"
            weather_params = {
                "lat": lat,
                "lon": lon,
                "appid": api_key,
                "units": "metric"
            }
            
            weather_response = requests.get(weather_url, params=weather_params, timeout=10)
            
            # Check for API key authentication errors on weather request too
            if weather_response.status_code == 401:
                logging.error("OpenWeather API returned 401 Unauthorized on weather request. Please check your API key.")
                return json.dumps({
                    "error": "Invalid API key for weather request. Please check your OpenWeather API key configuration.",
                    "location": location,
                    "api_error": True
                })
            
            weather_response.raise_for_status()
            weather_data = weather_response.json()
            
            result = {
                "location": f"{geo_data[0]['name']}, {geo_data[0].get('country', '')}",
                "coordinates": {"lat": lat, "lon": lon},
                "temperature": {
                    "celsius": weather_data["main"]["temp"],
                    "fahrenheit": round(weather_data["main"]["temp"] * 9/5 + 32, 1),
                    "feels_like_celsius": weather_data["main"]["feels_like"]
                },
                "condition": weather_data["weather"][0]["description"].title(),
                "humidity": f"{weather_data['main']['humidity']}%",
                "pressure": f"{weather_data['main']['pressure']} hPa",
                "wind_speed": f"{weather_data['wind']['speed']} m/s",
                "visibility": f"{weather_data.get('visibility', 'N/A')} meters" if weather_data.get('visibility') else "N/A",
                "cloud_cover": f"{weather_data['clouds']['all']}%",
                "mock_data": False
            }
            
            logging.info(f"Successfully retrieved weather data for {location}")
            return json.dumps(result, indent=2)
            
        except requests.RequestException as e:
            logging.error(f"Error fetching weather for {location}: {str(e)}")
            if "401" in str(e) or "unauthorized" in str(e).lower():
                return json.dumps({
                    "error": "API key authentication failed. Please verify your OpenWeather API key.",
                    "location": location,
                    "api_error": True
                })
            return json.dumps({"error": f"Failed to fetch weather data: {str(e)}"})
        except Exception as e:
            logging.error(f"Unexpected error getting weather for {location}: {str(e)}")
            return json.dumps({"error": f"Unexpected error: {str(e)}"})
    
    @tool 
    def get_weather_forecast(location: str, days: int = 3) -> str:
        """
        Get weather forecast for a specific location.
        
        Args:
            location: The location name (city, city+country, etc.)
            days: Number of days for forecast (1-5, default 3)
            
        Returns:
            JSON string with weather forecast data
        """
        try:
            api_key = os.environ.get("OPENWEATHER_API_KEY")
            
            # Enhanced validation logic
            weather_tools_instance = WeatherTools()
            
            if not weather_tools_instance._is_api_key_valid():
                logging.info(f"Using mock forecast data for location: {location}")
                # Generate mock forecast data
                mock_forecast = []
                for i in range(min(days, 3)):  # Limit mock data to 3 days
                    mock_forecast.append({
                        "date": f"2025-08-{15+i:02d}",  # Mock future dates
                        "temperature_range": {
                            "min_celsius": 15.0 + i,
                            "max_celsius": 25.0 + i,
                            "min_fahrenheit": round((15.0 + i) * 9/5 + 32, 1),
                            "max_fahrenheit": round((25.0 + i) * 9/5 + 32, 1)
                        },
                        "conditions": ["Clear", "Partly Cloudy"],
                        "main_condition": "Clear" if i % 2 == 0 else "Partly Cloudy"
                    })
                
                return json.dumps({
                    "location": location,
                    "note": "Weather API key not configured or invalid. Using mock forecast data.",
                    "mock_data": True,
                    "forecast_days": len(mock_forecast),
                    "forecast": mock_forecast
                }, indent=2)
            
            # Limit days to reasonable range
            days = max(1, min(days, 5))
            
            # Get coordinates first
            geo_url = f"http://api.openweathermap.org/geo/1.0/direct"
            geo_params = {
                "q": location,
                "limit": 1,
                "appid": api_key
            }
            
            geo_response = requests.get(geo_url, params=geo_params, timeout=10)
            
            # Check for API key authentication errors
            if geo_response.status_code == 401:
                logging.error("OpenWeather API returned 401 Unauthorized for forecast request. Please check your API key.")
                return json.dumps({
                    "error": "Invalid API key for forecast request. Please check your OpenWeather API key configuration.",
                    "location": location,
                    "api_error": True
                })
            
            geo_response.raise_for_status()
            geo_data = geo_response.json()
            
            if not geo_data:
                return json.dumps({"error": f"Location '{location}' not found"})
            
            lat = geo_data[0]["lat"]
            lon = geo_data[0]["lon"]
            
            # Get forecast data
            forecast_url = f"http://api.openweathermap.org/data/2.5/forecast"
            forecast_params = {
                "lat": lat,
                "lon": lon,
                "appid": api_key,
                "units": "metric",
                "cnt": days * 8  # 8 forecasts per day (every 3 hours)
            }
            
            forecast_response = requests.get(forecast_url, params=forecast_params, timeout=10)
            
            # Check for API key authentication errors on forecast request
            if forecast_response.status_code == 401:
                logging.error("OpenWeather API returned 401 Unauthorized on forecast data request. Please check your API key.")
                return json.dumps({
                    "error": "Invalid API key for forecast data request. Please check your OpenWeather API key configuration.",
                    "location": location,
                    "api_error": True
                })
            
            forecast_response.raise_for_status()
            forecast_data = forecast_response.json()
            
            # Process forecast data by day
            daily_forecasts = {}
            for item in forecast_data["list"]:
                date = item["dt_txt"].split(" ")[0]
                if date not in daily_forecasts:
                    daily_forecasts[date] = []
                daily_forecasts[date].append(item)
            
            # Create daily summaries
            forecast_summary = []
            for date, forecasts in list(daily_forecasts.items())[:days]:
                temps = [f["main"]["temp"] for f in forecasts]
                conditions = [f["weather"][0]["description"] for f in forecasts]
                
                forecast_summary.append({
                    "date": date,
                    "temperature_range": {
                        "min_celsius": round(min(temps), 1),
                        "max_celsius": round(max(temps), 1),
                        "min_fahrenheit": round(min(temps) * 9/5 + 32, 1),
                        "max_fahrenheit": round(max(temps) * 9/5 + 32, 1)
                    },
                    "conditions": list(set(conditions)),
                    "main_condition": max(set(conditions), key=conditions.count)
                })
            
            result = {
                "location": f"{geo_data[0]['name']}, {geo_data[0].get('country', '')}",
                "forecast_days": days,
                "forecast": forecast_summary,
                "mock_data": False
            }
            
            logging.info(f"Successfully retrieved forecast data for {location}")
            return json.dumps(result, indent=2)
            
        except requests.RequestException as e:
            logging.error(f"Error fetching forecast for {location}: {str(e)}")
            if "401" in str(e) or "unauthorized" in str(e).lower():
                return json.dumps({
                    "error": "API key authentication failed for forecast. Please verify your OpenWeather API key.",
                    "location": location,
                    "api_error": True
                })
            return json.dumps({"error": f"Failed to fetch forecast data: {str(e)}"})
        except Exception as e:
            logging.error(f"Unexpected error getting forecast for {location}: {str(e)}")
            return json.dumps({"error": f"Unexpected error: {str(e)}"})

# Create instances of the tools for easy import
weather_tools = WeatherTools()
get_current_weather = weather_tools.get_current_weather
get_weather_forecast = weather_tools.get_weather_forecast