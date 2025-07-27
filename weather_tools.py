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
            
            if not api_key:
                # Fallback to a mock response if no API key is configured
                return json.dumps({
                    "location": location,
                    "note": "Weather API key not configured. Using mock data.",
                    "temperature": "20°C (68°F)",
                    "condition": "Clear",
                    "humidity": "45%",
                    "wind_speed": "10 km/h"
                })
            
            # Get coordinates first
            geo_url = f"http://api.openweathermap.org/geo/1.0/direct"
            geo_params = {
                "q": location,
                "limit": 1,
                "appid": api_key
            }
            
            geo_response = requests.get(geo_url, params=geo_params, timeout=10)
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
                "cloud_cover": f"{weather_data['clouds']['all']}%"
            }
            
            return json.dumps(result, indent=2)
            
        except requests.RequestException as e:
            logging.error(f"Error fetching weather for {location}: {str(e)}")
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
            
            if not api_key:
                return json.dumps({
                    "location": location,
                    "note": "Weather API key not configured. Forecast unavailable.",
                    "forecast": []
                })
            
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
                "forecast": forecast_summary
            }
            
            return json.dumps(result, indent=2)
            
        except requests.RequestException as e:
            logging.error(f"Error fetching forecast for {location}: {str(e)}")
            return json.dumps({"error": f"Failed to fetch forecast data: {str(e)}"})
        except Exception as e:
            logging.error(f"Unexpected error getting forecast for {location}: {str(e)}")
            return json.dumps({"error": f"Unexpected error: {str(e)}"})

# Create instances of the tools for easy import
weather_tools = WeatherTools()
get_current_weather = weather_tools.get_current_weather
get_weather_forecast = weather_tools.get_weather_forecast