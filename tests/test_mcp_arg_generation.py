import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from baseline.mcp_copilot.arg_generation import McpArgGenerator


class FakeMcpArgGenerator(McpArgGenerator):
    def __init__(self, config, output_file):
        self.config = config
        self.output_file = Path(output_file)
        self.embedding_inputs = []

    async def _get_embedding(self, text, model=None):
        self.embedding_inputs.append(text)
        return [float(len(self.embedding_inputs))]

    async def _generate_summary(self, server_name, server_desc, tools, model=None):
        return ""


class McpArgGenerationTest(unittest.IsolatedAsyncioTestCase):
    async def test_generate_uses_non_empty_embedding_text_for_blank_descriptions(self):
        config = [
            {
                "description": "   ",
                "config": {"mcpServers": {"blank-server": {"command": "echo"}}},
                "tools": {
                    "blank-server": {
                        "tools": [
                            {
                                "name": "lookup_user",
                                "description": "",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "user_id": {
                                            "type": "string",
                                            "description": "User identifier",
                                        }
                                    },
                                    "required": ["user_id"],
                                },
                            }
                        ]
                    }
                },
            }
        ]

        with TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "mcp_args.json"
            generator = FakeMcpArgGenerator(config, output_file)

            await generator.generate()

            self.assertNotIn("   ", generator.embedding_inputs)
            self.assertNotIn("", generator.embedding_inputs)
            self.assertTrue(
                any("blank-server" in text for text in generator.embedding_inputs)
            )
            self.assertTrue(
                any("lookup_user" in text for text in generator.embedding_inputs)
            )

            indexed = json.loads(output_file.read_text(encoding="utf-8"))
            self.assertEqual(indexed[0]["description_embedding"], [1.0])
            self.assertEqual(indexed[0]["summary_embedding"], [2.0])
            self.assertEqual(indexed[0]["tools"][0]["description_embedding"], [3.0])


if __name__ == "__main__":
    unittest.main()
