#!/bin/bash
SRC_DIR="/outside"
DST_DIR="/LiveMCPBench"

find "$SRC_DIR" -mindepth 1 -maxdepth 1 | while read -r item; do
    name=$(basename "$item")
    target="$DST_DIR/$name"

    if [ -e "$target" ]; then
        rm -rf "$target"
    fi

    cp -r "$item" "$target"
done

echo "LiveMCPBench workspace has been updated from $SRC_DIR."