#!/bin/bash

OUTPUT_DIR="./baseline/output"

for file in "$OUTPUT_DIR"/*.json; do
  echo "Running evaluator on: $file"
  uv run -m evaluator.llm_as_judge_baseline \
    --trajectory_path "$file" \
    --output_dir "./evaluator/output_auto_key_points/" \
    --auto_key_points
done
