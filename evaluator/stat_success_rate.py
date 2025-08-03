import json
import argparse
from collections import defaultdict
import os
import pandas as pd


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--result_path",
        type=str,
        default="./evaluator/output/deepseek_deepseek-chat-v3-0324",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()
    res = defaultdict(dict)
    for file in os.listdir(args.result_path):
        if not file.endswith(".json") or "example" in file:
            continue
        name = file.removesuffix(".json")
        single_result_path = os.path.join(args.result_path, file)
        with open(single_result_path, "r") as f:
            results = json.load(f)
        res_dict = defaultdict(dict)
        for result in results:
            task_id = result["task_id"]
            category = result["category"]
            reward = result["reward"]
            res_dict[category][task_id] = reward
        for category in res_dict:
            success_count = sum(
                1 for reward in res_dict[category].values() if reward > 0
            )
            total_count = len(res_dict[category])
            success_rate = success_count / total_count if total_count > 0 else 0
            res[name][category] = round(100 * success_rate, 2)
            print(
                f"Category: {category}, Success Rate: {success_rate * 100:.2f}, Count: {total_count}, Success Count: {success_count}"
            )
        all_success_count = sum(
            1
            for category in res_dict
            for reward in res_dict[category].values()
            if reward > 0
        )
        all_total_count = sum(len(res_dict[category]) for category in res_dict)
        all_success_rate = (
            all_success_count / all_total_count if all_total_count > 0 else 0
        )
        res[name]["overall"] = round(100 * all_success_rate, 2)
        print(
            f"Overall Success Rate: {all_success_rate * 100:.2f}, Count: {all_total_count}, Success Count: {all_success_count}"
        )
    df = pd.DataFrame(res).T
    df.index.name = "Model"
    # sort by overall success rate
    df = df.sort_values(by="overall", ascending=False)
    df.to_csv(os.path.join(args.result_path, "success_rate.csv"), sep="\t")
    print("Success rates saved to success_rate.csv")
