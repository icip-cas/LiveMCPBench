<a id="readme-top"></a>

<!-- PROJECT -->
<br />
<div align="center">
  <h3 align="center">LiveMCPBench: Can Agents Navigate an Ocean of MCP Tools?</h3>

  <p align="center">
    Benchmarking the agent in real-world tasks within a large-scale MCP toolset.
  </p>
</div>
<p align="center">
<a href="https://www.python.org/downloads/release/python-31113/"><img src="https://img.shields.io/badge/python-3.11-blue.svg" alt="Python 3.11"></a>
<a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/badge/code%20style-ruff-000000.svg" alt="Code style: ruff"></a>
</p>

<p align="center">
  🌐 <a href="https://icip-cas.github.io/LiveMCPBench" target="_blank">Website</a> &nbsp; | &nbsp;
  📄 <a href="https://arxiv.org/abs/2508.01780" target="_blank">Paper</a> &nbsp; | &nbsp;
  🤗 <a href="https://huggingface.co/datasets/ICIP/LiveMCPBench" target="_blank">Dataset</a> &nbsp; | &nbsp;
  🐳 <a href="https://hub.docker.com/r/hysdhlx/livemcpbench" target="_blank">Docker</a> &nbsp; | &nbsp;
  🏆 <a href="https://docs.google.com/spreadsheets/d/1EXpgXq1VKw5A7l7-N2E9xt3w0eLJ2YPVPT-VrRxKZBw/edit?usp=sharing" target="_blank">Leaderboard</a> 
  &nbsp; | &nbsp;
  🙏 <a href="#citation" target="_blank">Citation</a>
</p>


![Overview](media/LiveMCPBench.png)
## News
* [8/18/2025] We releas [Docker images](https://hub.docker.com/r/hysdhlx/livemcpbench) and add evaluation results in [leaderboard](https://docs.google.com/spreadsheets/d/1EXpgXq1VKw5A7l7-N2E9xt3w0eLJ2YPVPT-VrRxKZBw/edit?usp=sharing) for three new models: GLM 4.5, GPT-5-Mini, and Kimi-K2.
* [8/3/2025] We release the LiveMCPBench.
## Getting Started

### Prerequisites
We recommend using our docker image, but if you want to run the code locally, you will need to install the following tools:
* npm
* uv
### Installation
1. Pull the docker image

   ```bash
   docker pull hysdhlx/livemcpbench:latest
   ```
2. Git the repo and run the docker image

   ```bash
   git clone https://github.com/icip-cas/LiveMCPBench.git
   cd LiveMCPBench

   docker run -itd \
   -v "$(pwd):/outside" \
   --gpus all \
   --ipc=host \
   --net=host \
   --name LiveMCPBench_container \
   hysdhlx/livemcpbench:latest \
   bash
   ```
3. Prepare the .env file

   ```bash
   cp .env_template .env
   ```
   You can modify the .env file to set your own environment variables.
   ```bash
   # MCP Copilot Agent Configuration
    BASE_URL=
    OPENAI_API_KEY=
    MODEL=

    # Tool Retrieval Configuration
    EMBEDDING_MODEL=
    EMBEDDING_BASE_URL=
    EMBEDDING_API_KEY=
    EMBEDDING_DIMENSIONS=1024
    TOP_SERVERS=5
    TOP_TOOLS=3
    # Abstract API Configuration (optional)
    ABSTRACT_MODEL=
    ABSTRACT_API_KEY=
    ABSTRACT_BASE_URL=

    # Proxy Configuration (optional)
    http_proxy=
    https_proxy=
    no_proxy=127.0.0.1,localhost
    HTTP_PROXY=
    HTTPS_PROXY=
    NO_PROXY=127.0.0.1,localhost

    # lark report (optional)
    LARK_WEBHOOK_URL=
   ```
4. Enter the container & Reset the environment

   As we have mounted the code repo to `/outside`, you can access the code repo in the container at `/outside/`. 


   ```bash
   docker exec -it LiveMCPBench_container bash
   ```
   Because the agent may change the environment, we recommend resetting the environment before running the agent. To reset the environment, you can run the following command:

   ```bash
   cd /LiveMCPBench/
   bash scripts/env_reset.sh 
   ```
   This will copy the repo code in `/outside` to `/LiveMCPBench` and link the `annotated_data` to `/root/`.
5. Check the MCP tools

   ```bash
   bash ./tools/scripts/tool_check.sh
   ```
   After running this command, you can check `./tools/test/tools.json` to see the tools.
   > You could run this script multiple times if you find some tools are not working.

6. Index the servers

   The MCP Copilot Agent requires you have indexed the servers before running. You can run the following command to warm up the agent:

   ```bash
   uv run -m baseline.mcp_copilot.arg_generation
   ```

## Quick Start
### MCP Copilot Agent
#### Example Run

```bash
bash ./baseline/scripts/run_example.sh
```
This will run the agent with a simple example and save the results in `./baseline/output/`.

#### Full Run
We default use /root dir to store our data that the agent will access. If you want to run locally, you need to ensure the file in the right path.

1. Run the MCP Copilot Agent

    Be sure you have set the environment variables in the .env file.

    ````bash
    bash ./baseline/scripts/run_baselines.sh
    ````
2. Check the results

    After running the agent, you can check the trajectories  in `./baseline/output`.

### Evaluation using the LiveMCPEval
1. Modify the `MODEL` in .env to change evluation models

2. Run the evaluation script

   ```bash
   bash ./evaluator/scripts/run_baseline.sh
   ```

3. Check the results

    After running the evaluation, you can check the results in `./evaluator/output`.

4. Calculate the success rate

   ```bash
   uv run ./evaluator/stat_success_rate.py --result_path /path/to/evaluation/
   ```

## Project Structure
```
LiveMCPBench/
├── annotated_data/      # Tasks and task files
├── baseline/            # MCP Copilot Agent
│   ├── scripts/         # Scripts for running the agent
│   ├── output/          # Output for the agent
│   └── mcp_copilot/     # Source code for the agent
├── evaluator/           # LiveMCPEval
│   ├── scripts/         # Scripts for evaluation
│   └── output/          # Output for evaluation
├── tools/               # LiveMCPTool
│   ├── LiveMCPTool/     # Tool data
│   └── scripts/         # Scripts for the tools
├── scripts/             # Path prepare scripts
├── utils/               # Utility functions
└── .env_template        # Template for environment
```
## Citation

If you find this project helpful, please use the following to cite it:
```bibtex
@misc{mo2025livemcpbenchagentsnavigateocean,
      title={LiveMCPBench: Can Agents Navigate an Ocean of MCP Tools?}, 
      author={Guozhao Mo and Wenliang Zhong and Jiawei Chen and Xuanang Chen and Yaojie Lu and Hongyu Lin and Ben He and Xianpei Han and Le Sun},
      year={2025},
      eprint={2508.01780},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2508.01780}, 
}
```