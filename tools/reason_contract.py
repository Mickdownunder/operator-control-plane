from __future__ import annotations

VALID_FAILURE_CLASSES = {
    "contract_failure",
    "execution_failure",
    "protocol_failure",
    "routing_failure",
    "state_conflict",
    "validation_failure",
    "resource_contention",
    "timeout",
}


def validate_failure_class(failure_class: str) -> str:
    if failure_class not in VALID_FAILURE_CLASSES:
        raise ValueError(f"unsupported failure class: {failure_class}")
    return failure_class
