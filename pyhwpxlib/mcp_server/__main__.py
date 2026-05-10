"""Allow ``python -m pyhwpxlib.mcp_server`` to launch the MCP stdio server.

Equivalent to running ``server.py`` directly. Convenient for use in
``claude_desktop_config.json`` / ``mcp.json`` style client configs.
"""
from .server import mcp

if __name__ == "__main__":
    mcp.run()
