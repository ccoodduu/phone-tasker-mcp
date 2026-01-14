"""MCP Server exposing Tasker actions as tools for AI assistants."""

import os

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
async def launch_app(app_name: str) -> dict:
    """Launch an app on the phone by its name.

    Args:
        app_name: The name of the app as it appears on the phone (e.g., Spotify, Chrome, Camera, Settings)
    """
    import urllib.parse
    encoded_name = urllib.parse.quote(app_name)
    return await _call_tasker(f"/app/launch/{encoded_name}")


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
