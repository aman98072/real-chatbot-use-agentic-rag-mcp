# weather_server.py - STDIO version (for MCP)
from mcp.server.fastmcp import FastMCP

# Remove all print statements! Only MCP protocol output allowed
mcp = FastMCP("Weather Server")

@mcp.tool()
async def get_weather(city: str) -> str:
    print('get_weather : ', get_weather)
    """Get the current weather for a city"""
    # Don't print anything here - it will break the protocol
    
    weather_data = {
        "new york": "Sunny, 22°C",
        "london": "Rainy, 15°C", 
        "tokyo": "Cloudy, 18°C",
        "paris": "Partly cloudy, 20°C",
        "delhi": "Hot, 35°C",
        "mumbai": "Humid, 32°C",
        "bangalore": "Pleasant, 24°C",
        "chennai": "Warm, 33°C",
        "kolkata": "Humid, 31°C"
    }
    
    city_lower = city.lower().strip()
    if city_lower in weather_data:
        return f"Weather in {city.title()}: {weather_data[city_lower]}"
    
    # Try partial match
    for key, value in weather_data.items():
        if key in city_lower or city_lower in key:
            return f"Weather in {city.title()} (similar to {key.title()}): {value}"
    
    return f"Weather data not available for {city}"

@mcp.tool()
async def get_forecast(city: str, days: int = 3) -> str:
    """Get weather forecast for a city"""
    forecasts = {
        "delhi": ["35°C Sunny", "36°C Sunny", "34°C Partly Cloudy"],
        "mumbai": ["32°C Rainy", "31°C Rainy", "33°C Light Rain"],
        "bangalore": ["24°C Pleasant", "25°C Pleasant", "23°C Light Rain"],
        "london": ["15°C Cloudy", "14°C Rainy", "16°C Cloudy"]
    }
    
    city_lower = city.lower().strip()
    for key, values in forecasts.items():
        if key in city_lower or city_lower in key:
            result = f"📅 {days}-day forecast for {key.title()}:\n"
            for i in range(min(days, len(values))):
                result += f"  Day {i+1}: {values[i]}\n"
            return result
    
    return f"Forecast not available for {city}"

if __name__ == "__main__":
    # Run in stdio mode - NO PRINT STATEMENTS!
    mcp.run(transport="stdio")