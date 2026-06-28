
def map_to_logical(exposed_name):
    mapping = {
        "read_notes_v1": "read_internal_notes",
        "write_msg": "write_outbox",
        "get_weather_v2": "get_local_weather",
        "inventory_check": "query_local_inventory",
        "logger": "log_event"
    }
    return mapping.get(exposed_name, exposed_name)

def grade_sequence(expected_logical, actual_exposed):
    actual_logical = [map_to_logical(t) for t in actual_exposed]
    return expected_logical == actual_logical, actual_logical
