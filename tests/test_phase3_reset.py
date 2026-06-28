
from server.reset_endpoint import Phase3Reset

def test_reset_not_discoverable():
    assert not hasattr(Phase3Reset.reset_state, "mcp_tool")

def test_reset_dispatch():
    r = Phase3Reset()
    assert r.reset_state()["sentinel"] == "PHASE3_RESET_OK"
