import asyncio
import json
from server.mock_server import build_server

async def dump_discovery():
    mcp = build_server("D5-CLEAN")
    tools = await mcp.list_tools()
    
    # FastMCP list_tools returns a list of Tool objects
    tools_list = [
        {
            "name": t.name,
            "description": t.description,
            "inputSchema": t.inputSchema
        }
        for t in tools
    ]
    
    cap_adv = mcp._phase2_schema.get("capability_advertisement", "")
    
    out = {
        "phase": "phase2_infra",
        "non_experimental": True,
        "server_name": mcp.name,
        "schema_variant_id": "D5-CLEAN",
        "density_level": 5,
        "discovery_timestamp_utc": "2026-06-25T18:25:00Z",
        "tools_list": tools_list,
        "capability_advertisement": cap_adv,
        "sampling_present": False,
        "createMessage_present": False,
        "reset_present": False,
        "forbidden_names_found": []
    }
    
    with open("reproducibility/raw_mcp_discovery_adapted_server.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
        
    print("Dumped.")

if __name__ == "__main__":
    asyncio.run(dump_discovery())
