"""MCP Server exposing Tasker actions as tools for AI assistants."""

import os
from typing import Literal

from dotenv import load_dotenv
import httpx
from fastmcp import FastMCP

load_dotenv()

PHONE_HOST = os.getenv("TASKER_PHONE_HOST", "100.123.253.113")
PHONE_PORT = int(os.getenv("TASKER_PHONE_PORT", "1821"))
REQUEST_TIMEOUT = float(os.getenv("TASKER_TIMEOUT", "5.0"))

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
async def toggle_torch(state: Literal["on", "off"]) -> dict:
    """Toggle the phone's flashlight/torch on or off.

    Args:
        state: Either "on" or "off"
    """
    return await _call_tasker(f"/torch/{state}")


@mcp.tool()
async def set_brightness(level: int) -> dict:
    """Set the phone's screen brightness.

    Args:
        level: Brightness level from 0 (minimum) to 255 (maximum)
    """
    level = max(0, min(255, level))
    return await _call_tasker(f"/brightness/{level}")


@mcp.tool()
async def set_volume(stream: Literal["media", "ring", "alarm", "notification"], level: int) -> dict:
    """Set volume for a specific audio stream.

    Args:
        stream: Audio stream type (media, ring, alarm, notification)
        level: Volume level from 0 to 15
    """
    level = max(0, min(15, level))
    return await _call_tasker(f"/volume/{stream}/{level}")


@mcp.tool()
async def send_notification(title: str, text: str) -> dict:
    """Send a notification to the phone.

    Args:
        title: Notification title
        text: Notification body text
    """
    import urllib.parse
    encoded_title = urllib.parse.quote(title)
    encoded_text = urllib.parse.quote(text)
    return await _call_tasker(f"/notify/{encoded_title}/{encoded_text}")


@mcp.tool()
async def vibrate(duration_ms: int = 500) -> dict:
    """Vibrate the phone.

    Args:
        duration_ms: Vibration duration in milliseconds (default: 500)
    """
    duration_ms = max(100, min(5000, duration_ms))
    return await _call_tasker(f"/vibrate/{duration_ms}")


@mcp.tool()
async def say_text(text: str) -> dict:
    """Use text-to-speech to speak text on the phone.

    Args:
        text: The text to speak aloud
    """
    import urllib.parse
    encoded_text = urllib.parse.quote(text)
    return await _call_tasker(f"/say/{encoded_text}")


@mcp.tool()
async def get_battery_status() -> dict:
    """Get the phone's current battery level and charging status."""
    return await _call_tasker("/battery/status")


@mcp.tool()
async def launch_app(package_name: str) -> dict:
    """Launch an app on the phone by its package name.

    Args:
        package_name: Android package name (e.g., com.spotify.music)
    """
    return await _call_tasker(f"/app/launch/{package_name}")


@mcp.tool()
async def take_photo() -> dict:
    """Take a photo using the phone's camera."""
    return await _call_tasker("/camera/photo")


@mcp.tool()
async def phone_ping() -> dict:
    """Ping the phone to check if it's reachable and Tasker is responding."""
    return await _call_tasker("/ping")


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
