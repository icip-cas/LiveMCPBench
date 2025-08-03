#!/bin/bash

SRC_DIR="/outside"
DST_DIR="/LiveMCPBench"

DIRS=("annotated_data" "baseline" "evaluator" "tools" "utils")

for dir in "${DIRS[@]}"; do
    rm -rf "${DST_DIR}/${dir}"
done

for dir in "${DIRS[@]}"; do
    cp -r "${SRC_DIR}/${dir}" "${DST_DIR}/"
done

echo "LiveMCPBench workspace has been reset."