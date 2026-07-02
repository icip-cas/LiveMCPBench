import re


def parse_judge_response(res_text):
    thoughts_match = re.search(r"Thoughts:\s*([\s\S]*?)\s*Status\s*:", res_text)
    status_match = re.search(
        r'^\s*Status\s*:\s*["\']?(success|failure)["\']?\s*$',
        res_text,
        re.IGNORECASE | re.MULTILINE,
    )
    thoughts = (
        thoughts_match.group(1).strip()
        if thoughts_match
        else "Thoughts extract failed."
    )
    judge = status_match.group(1).lower() if status_match else "unknown"
    reward = 1 if judge == "success" else 0
    return {"judge": judge, "thoughts": thoughts, "reward": reward}
