import json


def create_clean_config(
    input_file="./tools/LiveMCPTool/all_config.json",
    output_file="./tools/LiveMCPTool/clean_config.json",
):
    with open(input_file, "r", encoding="utf-8") as infile:
        data = json.load(infile)
    clean_data = {"mcpServers": {}}
    name_set=set()
    for entry in data:
        config = entry.get("config", {}).get("mcpServers", {})
        if not config:
            continue
        name = list(config.keys())[0]
        if name not in name_set:
            name_set.add(name)
        else:
            print(f"Duplicate MCP server name found: {name}.")
        command = config[name].get("command", "")
        args = config[name].get("args", [])
        env = config[name].get("env", {})
        clean_data["mcpServers"][name] = {"command": command, "args": args, "env": env}
    with open(output_file, "w", encoding="utf-8") as outfile:
        json.dump(clean_data, outfile, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    create_clean_config()
