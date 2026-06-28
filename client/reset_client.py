
from server.reset_endpoint import do_reset

def call_reset():
    result = do_reset()
    if result.get("sentinel") != "PHASE3_RESET_OK":
        raise Exception("Reset sentinel mismatch, halting batch.")
    return True
