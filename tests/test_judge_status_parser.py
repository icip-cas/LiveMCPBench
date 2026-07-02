import unittest

from evaluator.judge_parser import parse_judge_response


class JudgeStatusParserTest(unittest.TestCase):
    def test_uses_explicit_failure_status_when_reasoning_mentions_successfully(self):
        response = (
            "Thoughts: The agent did not provide the required train departure time "
            "or ticket price. Because none of the required outputs were produced "
            "from tool data, the task was not completed successfully.\n"
            'Status: "failure"'
        )

        parsed = parse_judge_response(response)

        self.assertEqual(parsed["judge"], "failure")
        self.assertEqual(parsed["reward"], 0)

    def test_assigns_reward_for_explicit_success_status(self):
        response = (
            "Thoughts: The tool calls returned the required data and the final "
            "answer includes all requested fields.\n"
            'Status: "success"'
        )

        parsed = parse_judge_response(response)

        self.assertEqual(parsed["judge"], "success")
        self.assertEqual(parsed["reward"], 1)

    def test_does_not_score_success_without_explicit_status(self):
        response = (
            "Thoughts: The agent says it successfully finished the task, but the "
            "judge response omitted the required Status line."
        )

        parsed = parse_judge_response(response)

        self.assertEqual(parsed["judge"], "unknown")
        self.assertEqual(parsed["reward"], 0)


if __name__ == "__main__":
    unittest.main()
