#!/bin/bash
# model_names=("openai/gpt-4.1" "openai/gpt-4.1-mini" "deepseek/deepseek-chat-v3-0324" "deepseek/deepseek-r1-0528" "qwen/qwen3-235b-a22b" "qwen/qwen3-32b" "google/gemini-2.5-flash")
# model_names=("claude-opus-4-20250514" "claude-sonnet-4-20250514")
# model_names=("models/gemini-2.5-pro")
# model_names=("qwen25_72b_int4_instruct")
trajectory_path="./baseline/output/claude-sonnet-4-20250514_Qwen3-Embedding-0.6B.json"

for model in "${model_names[@]}"; do
  echo "Running Evaluator with model_name=$model"
  MODEL="$model" uv run -m evaluator.llm_as_judge_baseline \
    --trajectory_path "$trajectory_path" \
    --model_name "$model"
done
