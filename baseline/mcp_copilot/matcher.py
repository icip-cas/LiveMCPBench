# from mcp zero
# https://github.com/xfey/MCP-Zero/blob/master/MCP-zero/matcher.py
import json
import numpy as np
import re
import time
from dotenv import load_dotenv
from typing import List, Dict, Any, Tuple, Optional
from openai import OpenAI

load_dotenv()


class ToolMatcher:
    def __init__(
        self,
        embedding_model: str,
        dimensions: int,
        top_servers: int = 5,
        top_tools: int = 3,
    ):
        self.embedding_model = embedding_model
        self.dimensions = dimensions
        self.top_servers = top_servers
        self.top_tools = top_tools
        self.servers_data = None
        self.tool_assistant_pattern = re.compile(
            r"<tool_assistant>\s*server:\s*(.*?)\s*tool:\s*(.*?)\s*</tool_assistant>",
            re.DOTALL,
        )
        self.openai_client = None

    def load_data(self, data_path: str) -> None:
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                self.servers_data = json.load(f)
            print(f"Loaded {len(self.servers_data)} servers from {data_path}")
        except Exception as e:
            raise ValueError(f"Error loading tool data: {e}")

    def setup_openai_client(self, base_url: str, api_key: str) -> None:
        self.openai_client = OpenAI(
            base_url=base_url,
            api_key=api_key,
        )

    def extract_tool_assistant(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        match = self.tool_assistant_pattern.search(text)
        if match:
            server_desc = match.group(1).strip()
            tool_desc = match.group(2).strip()
            return server_desc, tool_desc
        return None, None

    def get_embedding(self, text: str, max_retries: int = 3) -> Optional[List[float]]:
        if not self.openai_client:
            raise ValueError(
                "OpenAI client not initialized. Call setup_openai_client first."
            )

        for attempt in range(max_retries):
            try:
                time.sleep(0.05)
                response = self.openai_client.embeddings.create(
                    input=[text],
                    model=self.embedding_model,
                    # dimensions=self.dimensions,
                    encoding_format="float",
                )
                return response.data[0].embedding
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    print(f"Error getting embedding, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    print(f"Failed to get embedding after {max_retries} attempts: {e}")
                    return None

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0
        return np.dot(vec1, vec2) / (norm1 * norm2)

    def match_servers(self, server_desc: str) -> List[Dict[str, Any]]:
        if not self.servers_data:
            raise ValueError("No server data loaded. Call load_data first.")
        query_embedding = self.get_embedding(server_desc)
        if not query_embedding:
            raise ValueError("Failed to get embedding for server description")
        server_scores = []
        for server in self.servers_data:
            if "description_embedding" not in server:
                continue
            desc_similarity = self.cosine_similarity(
                query_embedding, server["description_embedding"]
            )
            summary_similarity = 0
            if "summary_embedding" in server:
                summary_similarity = self.cosine_similarity(
                    query_embedding, server["summary_embedding"]
                )
            final_score = max(desc_similarity, summary_similarity)
            server_scores.append({"server": server, "score": final_score})
        server_scores.sort(key=lambda x: x["score"], reverse=True)
        return server_scores[: self.top_servers]

    def match_tools(
        self, server_list: List[Dict[str, Any]], tool_desc: str
    ) -> List[Dict[str, Any]]:
        query_embedding = self.get_embedding(tool_desc)
        if not query_embedding:
            raise ValueError("Failed to get embedding for tool description")
        tool_scores = []
        for server_info in server_list:
            server = server_info["server"]
            server_score = server_info["score"]
            if "tools" not in server or not server["tools"]:
                continue
            for tool in server["tools"]:
                if "description_embedding" not in tool:
                    continue
                tool_similarity = self.cosine_similarity(
                    query_embedding, tool["description_embedding"]
                )
                final_score = (server_score * tool_similarity) * max(
                    server_score, tool_similarity
                )
                tool_scores.append(
                    {
                        "server_name": server["server_name"],
                        "tool_name": tool["name"],
                        "tool_description": tool.get("description", ""),
                        "inputschema": tool.get("parameter", {}),
                        "server_score": server_score,
                        "tool_score": tool_similarity,
                        "final_score": final_score,
                    }
                )
        tool_scores.sort(key=lambda x: x["final_score"], reverse=True)
        return tool_scores[: self.top_tools]

    def match(self, input_text: str) -> Dict[str, Any]:
        server_desc, tool_desc = self.extract_tool_assistant(input_text)
        if not server_desc or not tool_desc:
            return {
                "success": False,
                "error": "No tool_assistant tag found or invalid format",
                "matched_servers": [],
                "matched_tools": [],
            }
        try:
            matched_servers = self.match_servers(server_desc)
            matched_tools = self.match_tools(matched_servers, tool_desc)
            simplified_tools = []
            for tool in matched_tools:
                simplified_tools.append(
                    {
                        "server_name": tool["server_name"],
                        "tool_name": tool["tool_name"],
                        "tool_description": tool["tool_description"],
                        "inputschema": tool["inputschema"],
                    }
                )

            return {"success": True, "matched_tools": simplified_tools}
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "server_description": server_desc,
                "tool_description": tool_desc,
                "matched_servers": [],
                "matched_tools": [],
            }
