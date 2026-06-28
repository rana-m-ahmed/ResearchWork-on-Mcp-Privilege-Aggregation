
from client.phase3_grader import map_to_logical, grade_sequence

def test_logical_id_grading():
    assert map_to_logical("get_weather_v2") == "get_local_weather"
    success, seq = grade_sequence(["get_local_weather"], ["get_weather_v2"])
    assert success
