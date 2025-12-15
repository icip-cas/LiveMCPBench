#!/usr/bin/env python3
"""Remove bing-cn-mcp from all config and source files."""
import json
from pathlib import Path

def remove_from_json_list(filepath):
    """Remove bing-cn-mcp from a JSON list of servers."""
    try:
        print(f"\nProcessing {filepath}...")
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            print(f"  Skipping (not a list)")
            return False
            
        original_count = len(data)
        # Filter out bing-cn-mcp - check both server_name and config keys
        def is_bing_cn_mcp(server):
            if server.get("server_name") == "bing-cn-mcp":
                return True
            config = server.get("config", {}).get("mcpServers", {})
            if "bing-cn-mcp" in config:
                return True
            return False
        
        data = [server for server in data if not is_bing_cn_mcp(server)]
        new_count = len(data)
        
        if original_count == new_count:
            print(f"  No bing-cn-mcp found")
            return False
            
        print(f"  Removed {original_count - new_count} bing-cn-mcp entries")
        print(f"  Writing {new_count} servers back to file...")
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  Done!")
        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False

# Process embeddings files in config directory
config_dir = Path("baseline/mcp_copilot/config")
for json_file in config_dir.rglob("*.json"):
    if json_file.name == "clean_config.json":
        continue
    remove_from_json_list(json_file)

# Process source tools file
tools_file = Path("tools/LiveMCPTool/tools.json")
if tools_file.exists():
    remove_from_json_list(tools_file)

print("\nAll files processed!")
