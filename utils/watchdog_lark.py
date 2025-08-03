from utils.lark_reporter import LarkReporter
import argparse
import time
import psutil
import datetime
import os
import dotenv

dotenv.load_dotenv()

def get_process_info(pid):
    try:
        p = psutil.Process(pid)
        time_str = datetime.datetime.fromtimestamp(p.create_time()).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        info = {
            "pid": p.pid,
            "name": p.name(),
            "exe": p.exe(),
            "cwd": p.cwd(),
            "create_time": time_str,
            "memory_info": p.memory_info(),
            "cpu_times": p.cpu_times(),
            "status": p.status(),
        }
        return info
    except psutil.NoSuchProcess:
        return None


def is_process_running(pid):
    try:
        with open(f"/proc/{pid}/status", "r") as f:
            return True
    except FileNotFoundError:
        return False


def parse_args():
    parser = argparse.ArgumentParser(description="Lark bot reporter")
    parser.add_argument(
        "--url",
        type=str,
        default=os.getenv("LARK_WEBHOOK_URL", ""),
    )
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--interval", type=int, default=10)
    parser.add_argument(
        "--name",
        type=str,
        default=f"{os.getenv('MODEL')}_{os.getenv('EMBEDDING_MODEL')}",
    )

    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    pid = args.pid
    check_interval = args.interval
    if args.url:
        lark = LarkReporter(args.url)
        if is_process_running(pid):
            process_info = get_process_info(pid)
            lark.post(f"{args.name} {process_info}", "Watchdog started")
        while is_process_running(pid):
            print(f"PID {pid} is running, waiting {check_interval}s ...")
            time.sleep(check_interval)
        lark.post(f"{args.name} PID {pid} Stopped", "Watchdog stopped")
