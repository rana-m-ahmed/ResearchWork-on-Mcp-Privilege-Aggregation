
import pytest
from client.tool_call_parser import parse_phase3_tool_call, ModelOutputFailure

def test_invalid_json_fails():
    with pytest.raises(ModelOutputFailure):
        parse_phase3_tool_call("not json")

def test_no_retry_on_failure():
    pass
