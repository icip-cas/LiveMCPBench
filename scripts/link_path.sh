#!/bin/bash
# --- Configuration ---
# Set the source directory where the original directories are located.
SOURCE_DIR="/LiveMCPBench/annotated_data"
# Set the destination directory where the symbolic links will be created.
DEST_DIR="/root"

# --- Safety Checks ---

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

# Check for write permissions in the destination directory.
# Since the destination is /root, this script will likely need to be run with root privileges (e.g., using sudo).
if [ ! -w "$DEST_DIR" ]; then
  echo "Error: No write permission for destination directory '$DEST_DIR'. Try running this script with 'sudo'."
  exit 1
fi
# --- Main Logic ---

echo "Creating symbolic links from '$SOURCE_DIR' to '$DEST_DIR'..."

# Loop through all items (files and directories) in the source directory.
# Using quotes around "$SOURCE_DIR"/* ensures that names with spaces are handled correctly.
for item in "$SOURCE_DIR"/*; do
  # Check if the current item is a directory.
  # The -d flag tests if the path points to a directory.
  if [ -d "$item" ]; then
    # If it is a directory, create a symbolic link to it in the destination directory.
    # The -s option for the 'ln' command creates a symbolic (soft) link.
    # The last argument to 'ln' is the target directory where the link is placed. [12]
    ln -s "$item" "$DEST_DIR"

    # Get the base name of the directory for a more user-friendly output message.
    BASENAME=$(basename "$item")
    echo "  -> Link created for '$BASENAME'."
  fi
done

echo "Script execution finished."