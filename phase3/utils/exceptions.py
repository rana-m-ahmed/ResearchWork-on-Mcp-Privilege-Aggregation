class Phase3Exception(Exception):
    """Base exception for Phase 3."""
    pass

class ConfigurationError(Phase3Exception):
    pass

class ExecutionError(Phase3Exception):
    pass