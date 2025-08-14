if [ ! -d "./annotated_data/git" ]; then
  echo "unzip git data..."
  bash ./utils/get_git_dir.sh
fi
mkdir -p logs
nohup uv run -m baseline.run_conversation --input_path ./annotated_data/all_annotations.json > ./logs/run.log 2>&1 &
sleep 5

pid=$(pgrep -f "uv run -m baseline.run_conversation")
if [ -z "$pid" ]; then
  echo "baseline.run_conversation not running, please check the logs."
  exit 1
fi
echo "PID: $pid"
nohup uv run -m utils.watchdog_lark --pid "$pid" > logs/lark.log 2>&1 &
