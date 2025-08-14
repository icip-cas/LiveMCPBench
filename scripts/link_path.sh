#!/bin/bash
SOURCE_DIR="/LiveMCPBench/annotated_data"
DEST_DIR="/root"


# Check if the source directory exists.
if [ ! -d "$SOURCE_DIR" ]; then
  echo "Error: Source directory '$SOURCE_DIR' does not exist."
  exit 1
fi

# Check if the destination directory exists.
if [ ! -d "$DEST_DIR" ]; then
  echo "Error: Destination directory '$DEST_DIR' does not exist."
  exit 1
fi

if [ ! -w "$DEST_DIR" ]; then
  echo "Error: No write permission for destination directory '$DEST_DIR'. Try running this script with 'sudo'."
  exit 1
fi

echo "Creating symbolic links from '$SOURCE_DIR' to '$DEST_DIR'..."

for item in "$SOURCE_DIR"/* "$SOURCE_DIR/git"; do
  BASENAME=$(basename "$item")
  TARGET_PATH="$DEST_DIR/$BASENAME"

  if [ -e "$TARGET_PATH" ] || [ -L "$TARGET_PATH" ]; then
    rm -rf "$TARGET_PATH"
    echo "  -> Removed existing '$BASENAME'."
  fi

  if [ -d "$item" ] || [ "$BASENAME" = "git" ]; then
    ln -s "$item" "$TARGET_PATH"
    echo "  -> Link created for '$BASENAME'."
  fi
done
echo "Script execution finished."