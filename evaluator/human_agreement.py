import json
import os
import pandas as pd
from tqdm import tqdm

if __name__ == "__main__":
    human_annotation_path = (
        "./baseline/annotation/claude-sonnet-4-20250514_Qwen3-Embedding-0.6B.json"
    )
    evalautor_output = "./evaluator/output/"
    with open(human_annotation_path, "r") as f:
        human_annotation = json.load(f)
    human_judge = {}
    for item in human_annotation:
        human_judge[item["task_id"]] = item["task_success"]
    human_agreement_table = {}
    human_success_count = 0
    for task_id in human_judge:
        if "success" in human_judge[task_id].lower():
            human_judge[task_id] = "success"
            human_success_count += 1
    human_agreement_table["human"] = {
        "human_agreement": 100.0,
        "success_rate": round(100 * human_success_count / len(human_judge), 2),
    }
    for file in tqdm(os.listdir(evalautor_output)):
        evaluator_path = os.path.join(
            evalautor_output, file, f"{human_annotation_path.split('/')[-1]}"
        )
        if not os.path.exists(evaluator_path):
            continue
        with open(evaluator_path, "r") as f:
            evaluator_annotation = json.load(f)
        evaluator_judge = {}
        for item in evaluator_annotation:
            evaluator_judge[item["task_id"]] = item["judge"]
        human_agreement = 0
        success_count = 0
        for task_id in human_judge:
            if task_id in evaluator_judge:
                if "success" in human_judge[task_id].lower():
                    h_judge = "success"
                else:
                    h_judge = "failure"
                if "success" in evaluator_judge[task_id].lower():
                    e_judge = "success"
                    success_count += 1
                else:
                    e_judge = "failure"
                if e_judge == h_judge:
                    human_agreement += 1

        human_agreement_rate = human_agreement / len(human_judge)
        success_rate = success_count / len(human_judge)
        human_agreement_table[file] = {
            "human_agreement": round(100 * human_agreement_rate, 2),
            "success_rate": round(100 * success_rate, 2),
        }

    df = pd.DataFrame(human_agreement_table).T
    df.index.name = "Model"
    df = df.sort_values(by="human_agreement", ascending=False)
    df.to_csv(os.path.join(evalautor_output, f"human_agreement_{human_annotation_path.split('/')[-1].removesuffix('.json')}.csv"))
