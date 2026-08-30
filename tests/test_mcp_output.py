import json

from family_activity_mcp.server import output
from family_activity_agent.agent import stringify_tool_result


def test_mcp_output_is_json_text_for_model_tool_messages():
    result = output({"events": [], "count": 0})
    assert isinstance(result, str)
    assert json.loads(result) == {"events": [], "count": 0}


def test_langchain_content_blocks_are_flattened_for_model():
    blocks = [{"type": "text", "text": "[]", "id": "example"}]
    assert stringify_tool_result(blocks) == "[]"
