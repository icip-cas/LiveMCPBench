import argparse
import json
import logging
import os
import pathlib
from collections import defaultdict
import re

import dotenv
from tqdm import tqdm

from utils.clogger import _set_logger
from utils.llm_api import ChatModel

dotenv.load_dotenv()
_set_logger(
    exp_dir=pathlib.Path("./logs"),
    logging_level_stdout=logging.INFO,
    logging_level=logging.DEBUG,
    file_name="llm_as_judge_baseline.log",
)
logger = logging.getLogger(__name__)


def identify_key_points(task, model: ChatModel, retry=0):
    system_msg = """You are an expert tasked with analyzing a given task to identify the key points explicitly stated in the task description.

**Objective**: Carefully analyze the task description and extract the critical elements explicitly mentioned in the task for achieving its goal.

**Instructions**:
1. Read the task description carefully.
2. Identify and extract **key points** directly stated in the task description.
   - A **key point** is a critical element, condition, or step explicitly mentioned in the task description.
   - Do not infer or add any unstated elements.

**Respond with**:
- **Key Points**: A numbered list of the explicit key points for completing this task, one per line, without explanations or additional details."""
    prompt = """Task: {task}"""
    text = prompt.format(task=task)
    messages = [
        {"role": "system", "content": system_msg},
        {
            "role": "user",
            "content": [{"type": "text", "text": text}],
        },
    ]
    responses = model.chat_with_retry(message=messages, retry=retry)
    return responses.choices[0].message.content


def livemcp_eval(
    task, response, tool_calls, steps, tool_descriptions, model: ChatModel
):
    system_msg = """You are an expert in evaluating the performance of a tool-use agent. The agent is designed to help a human user use multi-tools to complete a task. Given the user's task, the agent's final response, key points for task completion, and tool call history, your goal is to determine whether the agent has completed the task and achieved all requirements.

Your response must strictly follow the following evaluation criteria!
*Important Evaluation Criteria*:
1. You must carefully check whether the information (e.g. the coordinates of the addresses) comes from the tool call, if the agent get it from the internal knowledge, it should be considered failed.
2: Some tasks require to create files to be considered successful.

*IMPORTANT*
Format your response into two lines as shown below:

Thoughts: <your thoughts and reasoning process based on double-checking each key points and the evaluation criteria>
Status: "success" or "failure"
"""
    prompt = """\
User Task: 
{task}

Key Points: 
{key_points}

Final Response: 
{response}

Tool Call History:
{tool_calls}

Tool Descriptions:
{tool_descriptions}
"""
    if not steps:
        key_points = identify_key_points(task, model)
        key_points = key_points.replace("\n\n", "\n")

        try:
            key_points = key_points.split("**Key Points**:")[1]
            key_points = "\n".join(line.lstrip() for line in key_points.splitlines())
        except Exception:
            key_points = key_points.split("Key Points:")[-1]
            key_points = "\n".join(line.lstrip() for line in key_points.splitlines())
    else:
        key_points = steps

    text = prompt.format(
        task=task,
        tool_calls="\n".join(
            f"{i + 1}. {tool_call}" for i, tool_call in enumerate(tool_calls)
        ),
        response=response,
        key_points=key_points,
        tool_descriptions=tool_descriptions,
    )

    messages = [
        {"role": "system", "content": system_msg},
        {
            "role": "user",
            "content": [{"type": "text", "text": text}],
        },
    ]
    return messages, text, system_msg


def format_tool_descriptions(tool_map, server_name, tool_name):
    if server_name not in tool_map or tool_name not in tool_map[server_name]:
        return f"Tool {tool_name} not found in server {server_name}."
    tool_descriptions = ""
    tool_descriptions += f"Server: {server_name}\n"
    tool_descriptions += f"Tool: {tool_name}\n"
    tool_info = tool_map[server_name][tool_name]
    tool_descriptions += f"Description: {tool_info['description']}\n"
    tool_descriptions += "\n"

    return tool_descriptions.strip()


def get_args():
    parser = argparse.ArgumentParser(description="LLM as Judge Baseline")
    parser.add_argument("--tools_path", type=str, default="./tools/LiveMCPTool/tools.json")
    parser.add_argument(
        "--trajectory_path",
        type=str,
        default="./baseline/output/example_results.json",
    )
    parser.add_argument("--output_dir", type=str, default="./evaluator/output/")
    parser.add_argument("--model_name", type=str, default=os.getenv("MODEL", "None"))
    parser.add_argument(
        "--auto_key_points",
        action="store_true",
        default=False,
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()
    output_name = args.trajectory_path.split("/")[-1]
    output_name = output_name.removesuffix(".json")
    output_path = os.path.join(
        args.output_dir,
        f"{args.model_name.replace('/', '_')}",
        f"{output_name}.json",
    )
    chat_model = ChatModel(
        model_name=args.model_name,
        model_url=os.getenv("BASE_URL"),
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    with open(args.trajectory_path, "r") as f:
        trajectory = json.load(f)
    with open(args.tools_path, "r") as f:
        tool_servers = json.load(f)
    tool_map = defaultdict(dict)
    for tool_server in tool_servers:
        tools = tool_server["tools"]
        for tool in tools.values():
            server_name = tool["server_name"]
            for tl in tool["tools"]:
                tool_map[server_name][tl["name"]] = {
                    "description": tl["description"],
                    "inputSchema": tl["inputSchema"],
                }
    if os.path.exists(output_path):
        with open(output_path, "r") as f:
            judge_results = json.load(f)
            exisiting_ids = {entry["task_id"] for entry in judge_results}
    else:
        judge_results = []
        exisiting_ids = set()
    for entry in tqdm(trajectory):
        try:
            task_id = entry["task_id"]
            if task_id in exisiting_ids:
                continue
            messages = entry["messages"]
            response = ""
            tool_calls = []
            if not args.auto_key_points:
                steps = entry["Annotator Metadata"]["Steps"]
            else:
                steps = None
            tool_descriptions = ""
            for message in messages:
                if message["role"] == "assistant":
                    message_content = message.get("content", None)
                    message_tool_calls = message.get("tool_calls", None)
                    message_function_call = message.get("function_call", None)
                    if (
                        message_content
                        and not message_tool_calls
                        and not message_function_call
                    ):
                        response = message_content
                    elif message_tool_calls or message_function_call:
                        # Extract tool calls or function calls
                        message_tool_calls = message.get(
                            "tool_calls", []
                        ) or message.get("function_call", [])
                        for tool_call in message_tool_calls:
                            function = tool_call["function"]
                            if function.get("name") == "execute-tool":
                                tool_calls.append(function["arguments"])
                                try:
                                    tool_config = json.loads(function["arguments"])
                                except json.JSONDecodeError:
                                    tool_config = {}
                                tool_descriptions += format_tool_descriptions(
                                    tool_map,
                                    tool_config.get("server_name", "not_given"),
                                    tool_config.get("tool_name", "not_given"),
                                )
            messages, text, system_msg = livemcp_eval(
                entry["Question"],
                response,
                tool_calls,
                steps,
                tool_descriptions,
                chat_model,
            )
            res = chat_model.chat_with_retry(message=messages)
            res_text = res.choices[0].message.content
            pattern = r"Thoughts:\s*(.+?)\s*Status:\s*(\w+)"
            match = re.search(pattern, res_text, re.DOTALL)
            if match:
                thoughts = match.group(1).strip()
                judge = match.group(2).strip()
            else:
                thoughts = "Thoughts extract failed."
                judge = res_text
            reward = 1
            if "success" in judge.lower():
                reward *= 1
            elif "failure" in judge.lower():
                reward *= 0
            else:
                reward *= 0
            judge_results.append(
                {
                    "task_id": task_id,
                    "question": entry["Question"],
                    "judge": judge,
                    "judge_reason": thoughts,
                    "reward": reward,
                    "category": entry["category"],
                    "response": response,
                    "messages": entry["messages"],
                }
            )
        except Exception as e:
            logger.error(f"Error processing entry {task_id}: {e}")
            continue
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(judge_results, f, indent=4, ensure_ascii=False)
