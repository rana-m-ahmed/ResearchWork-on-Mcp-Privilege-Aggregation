
from phase3.scripts.validate_phase3_logs import validate_logs

def test_metadata_validation():
    assert validate_logs(dry_run=True)
