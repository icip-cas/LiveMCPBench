#!/bin/bash
SRC_DIR="/outside"
DST_DIR="/LiveMCPBench"

EXCLUDES=(".venv" "logs")

exclude_args=()
for ex in "${EXCLUDES[@]}"; do
    exclude_args+=(! -name "$ex")
done

find "$SRC_DIR" -mindepth 1 -maxdepth 1 "${exclude_args[@]}" | while read -r item; do
    name=$(basename "$item")
    target="$DST_DIR/$name"

    if [ -e "$target" ]; then
        rm -rf "$target"
    fi

    cp -r "$item" "$target"
done

echo "LiveMCPBench workspace has been updated from $SRC_DIR (excluding: ${EXCLUDES[*]})."