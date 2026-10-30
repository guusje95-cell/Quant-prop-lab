"""Hyro platform (HyroTrader's own terminal, live Bybit data) via the HyroTrader MCP server and an agent token.

Step 1 (now): PROBE. Connects with a READ-ONLY agent token, lists the server's tools (names, descriptions, input schemas) and writes them
to paper_trading/hyro_probe/tools.json. It calls NO tool, so it can neither read nor change anything in the account. With that list
the execution adapter (step 2, dry-run first, live only after the paper GO and your explicit OK) can be written against the real tools.

    hyro_probe.bat   (asks for the MCP server URL and the token; both stay in that window only)

Environment: HYRO_MCP_URL (shown in HyroTrader -> Settings -> Agent tokens / the MCP setup guide), HYRO_AGENT_TOKEN (never in a file or
in chat), optional HYRO_AUTH_HEADER (default 'Authorization', value 'Bearer <token>')."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "paper_trading" / "hyro_probe"


async def _probe(url: str, token: str, header: str) -> dict:
    from mcp import ClientSession
    from mcp.client import streamable_http as sh
    hdr = {header: f"Bearer {token}" if header.lower() == "authorization" else token}
    if hasattr(sh, "streamablehttp_client"):                              # mcp 1.x
        ctx = sh.streamablehttp_client(url, headers=hdr)
    else:                                                                  # mcp 2.x: headers via the SDK's own http client factory
        ctx = sh.streamable_http_client(url, http_client=sh.create_mcp_http_client(headers=hdr))
    async with ctx as streams:
        read, write = streams[0], streams[1]
        async with ClientSession(read, write) as s:
            init = await s.initialize()
            tools = (await s.list_tools()).tools
            return {"server": str(getattr(init, "serverInfo", None) or getattr(init, "server_info", None)),
                    "tools": [{"name": t.name, "description": t.description, "input_schema": getattr(t, "inputSchema", None) or getattr(t, "input_schema", None)} for t in tools]}


def main():
    url, token = os.environ.get("HYRO_MCP_URL"), os.environ.get("HYRO_AGENT_TOKEN")
    if not url or not token:
        sys.exit("Set HYRO_MCP_URL and HYRO_AGENT_TOKEN first (hyro_probe.bat asks for them). Never paste the token in chat or a file.")
    res = asyncio.run(_probe(url, token, os.environ.get("HYRO_AUTH_HEADER", "Authorization")))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "tools.json").write_text(json.dumps({"url_host": url.split("/")[2] if "//" in url else url, **res}, indent=1, default=str))
    print(f"{len(res['tools'])} tools:"); [print("  -", t["name"], "|", (t["description"] or "")[:90]) for t in res["tools"]]
    print(f"saved {OUT / 'tools.json'} (no token inside). No tool was called.")


if __name__ == "__main__":
    main()
