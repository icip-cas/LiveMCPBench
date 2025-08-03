import json
import re
import requests
import os
from tqdm import tqdm


def extract_raw_readme_url(github_url: str) -> str:
    """
    将 GitHub 仓库页面链接转换为对应的 raw README.md 地址
    """
    # 匹配带路径的格式
    pattern_tree = r"https://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.*)"
    # 匹配主页面（不带路径）
    pattern_root = r"https://github\.com/([^/]+)/([^/]+)$"

    m1 = re.match(pattern_tree, github_url)
    if m1:
        user, repo, branch, path = m1.groups()
        return (
            f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{path}/README.md"
        )

    m2 = re.match(pattern_root, github_url)
    if m2:
        user, repo = m2.groups()
        return f"https://raw.githubusercontent.com/{user}/{repo}/main/README.md"  # 默认分支是 main

    raise ValueError("Invalid GitHub URL format.")


if __name__ == "__main__":
    with open("./tools/LiveMCPTool/all_config.json", "r") as f:
        data = json.load(f)
    print(len(data))
    wrong_entry = []
    for entry in tqdm(data):
        url = entry["web"]
        try:
            if os.path.exists(f"./tools/LiveMCPTool/readme/{entry['name']}.md"):
                print(f"Skipping {entry['name']}, already exists.")
                continue
            raw_url = extract_raw_readme_url(url)
            response = requests.get(raw_url)
            if response.status_code == 404:
                response = requests.get(raw_url.replace("main", "master"))
            if response.status_code == 404:
                response = requests.get(
                    raw_url.replace("main", "master").replace("README.md", "readme.md")
                )
            response.raise_for_status()
            readme_content = response.text
            with open(
                f"./tools/fillter/readme/{entry['name']}.md", "w", encoding="utf-8"
            ) as f:
                f.write(readme_content)
        except Exception as e:
            print(f"Error processing {url}: {e}")
            wrong_entry.append(entry)
    print(f"Total entries processed: {len(data)}")
    print(f"Entries with errors: {len(wrong_entry)}")
