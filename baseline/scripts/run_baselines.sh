if [ ! -d "./annotated_data/git" ]; then
  echo "unzip git data..."
  bash ./utils/get_git_dir.sh
fi
uv run -m baseline.run_conversation --input_path ./annotated_data/all_annotations.json