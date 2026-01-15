"""MCP Server exposing Tasker actions as tools for AI assistants."""

import os

from dotenv import load_dotenv
import httpx
from fastmcp import FastMCP

load_dotenv()

PHONE_HOST = os.getenv("TASKER_PHONE_HOST", "100.123.253.113")
PHONE_PORT = int(os.getenv("TASKER_PHONE_PORT", "1821"))
REQUEST_TIMEOUT = float(os.getenv("TASKER_TIMEOUT", "5.0"))
WOL_SERVICE_URL = os.getenv("WOL_SERVICE_URL", "http://localhost:3000")

mcp = FastMCP("Tasker Phone Control")


def _tasker_url(path: str) -> str:
    """Build URL for Tasker HTTP endpoint."""
    return f"http://{PHONE_HOST}:{PHONE_PORT}{path}"


async def _call_tasker(path: str) -> dict:
    """Make HTTP request to Tasker endpoint."""
    url = _tasker_url(path)
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            response = await client.get(url)
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response": response.text or "OK",
            }
        except httpx.TimeoutException:
            return {"success": False, "error": "Request timed out"}
        except httpx.ConnectError:
            return {"success": False, "error": f"Cannot connect to phone at {PHONE_HOST}:{PHONE_PORT}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


@mcp.tool()
async def torch_on() -> dict:
    """Turn on the phone's flashlight/torch."""
    return await _call_tasker("/torch/on")


@mcp.tool()
async def torch_off() -> dict:
    """Turn off the phone's flashlight/torch."""
    return await _call_tasker("/torch/off")


@mcp.tool()
async def launch_app(app_name: str) -> dict:
    """Launch an app on the phone by its name.

    Args:
        app_name: The name of the app as it appears on the phone (e.g., Spotify, Chrome, Camera, Settings)
    """
    import urllib.parse
    encoded_name = urllib.parse.quote(app_name)
    return await _call_tasker(f"/app/launch/{encoded_name}")


@mcp.tool()
async def volume_up() -> dict:
    """Increase the phone's media volume by one step."""
    return await _call_tasker("/volume/up")


@mcp.tool()
async def volume_down() -> dict:
    """Decrease the phone's media volume by one step."""
    return await _call_tasker("/volume/down")


@mcp.tool()
async def media_play_pause() -> dict:
    """Toggle play/pause for the currently active media player."""
    return await _call_tasker("/media/playpause")


@mcp.tool()
async def media_next() -> dict:
    """Skip to the next track in the currently active media player."""
    return await _call_tasker("/media/next")


@mcp.tool()
async def media_previous() -> dict:
    """Go back to the previous track in the currently active media player."""
    return await _call_tasker("/media/previous")


WEATHER_CODES = {
    0: "Klart vejr", 1: "Hovedsageligt klart", 2: "Delvist skyet", 3: "Overskyet",
    45: "Tåge", 48: "Rimtåge", 51: "Let støvregn", 53: "Støvregn", 55: "Tæt støvregn",
    61: "Let regn", 63: "Regn", 65: "Kraftig regn", 66: "Let isregn", 67: "Isregn",
    71: "Let sne", 73: "Sne", 75: "Kraftig sne", 77: "Snebyger",
    80: "Lette regnbyger", 81: "Regnbyger", 82: "Kraftige regnbyger",
    85: "Lette snebyger", 86: "Kraftige snebyger",
    95: "Tordenvejr", 96: "Tordenvejr med hagl", 99: "Kraftigt tordenvejr med hagl"
}


@mcp.tool()
async def get_weather(city: str = "Copenhagen") -> dict:
    """Get current weather and forecast for a city.

    Args:
        city: City name (e.g., Copenhagen, Aarhus, Odense)
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=da"
            geo_response = await client.get(geo_url)
            geo_data = geo_response.json()

            if not geo_data.get("results"):
                return {"success": False, "error": f"Could not find city: {city}"}

            location = geo_data["results"][0]
            lat, lon = location["latitude"], location["longitude"]
            city_name = location.get("name", city)

            weather_url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m,relative_humidity_2m"
                f"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
                f"&timezone=Europe/Copenhagen&forecast_days=3"
            )
            weather_response = await client.get(weather_url)
            weather_data = weather_response.json()

            current = weather_data.get("current", {})
            daily = weather_data.get("daily", {})

            forecast = []
            for i in range(len(daily.get("time", []))):
                forecast.append({
                    "date": daily["time"][i],
                    "condition": WEATHER_CODES.get(daily["weather_code"][i], "Ukendt"),
                    "temp_max": daily["temperature_2m_max"][i],
                    "temp_min": daily["temperature_2m_min"][i],
                    "precipitation_chance": daily["precipitation_probability_max"][i]
                })

            return {
                "success": True,
                "city": city_name,
                "current": {
                    "temperature": current.get("temperature_2m"),
                    "feels_like": current.get("apparent_temperature"),
                    "condition": WEATHER_CODES.get(current.get("weather_code"), "Ukendt"),
                    "humidity": current.get("relative_humidity_2m"),
                    "wind_speed": current.get("wind_speed_10m")
                },
                "forecast": forecast
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


@mcp.tool()
async def wake_computer(mac: str = "18:c0:4d:66:71:23") -> dict:
    """Wake up a computer using Wake-on-LAN.

    Args:
        mac: MAC address of the computer to wake (default: Williams PC)
    """
    import asyncio
    try:
        proc = await asyncio.create_subprocess_exec(
            "wakeonlan", mac,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return {
            "success": proc.returncode == 0,
            "response": stdout.decode().strip() or "Wake signal sent",
            "error": stderr.decode().strip() if proc.returncode != 0 else None
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    """Run the MCP server with SSE transport for container deployment."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", default="sse", choices=["stdio", "sse"])
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.run(transport="sse", port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
