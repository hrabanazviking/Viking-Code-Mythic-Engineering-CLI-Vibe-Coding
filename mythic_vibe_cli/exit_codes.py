from __future__ import annotations

SUCCESS = 0
OPERATIONAL_FAILURE = 1
USER_INPUT_ERROR = 2
VERIFICATION_FAILURE = 3
UNSAFE_OPERATION_BLOCKED = 4

EXIT_CODE_POLICY = {
    SUCCESS: "success",
    OPERATIONAL_FAILURE: "operational failure",
    USER_INPUT_ERROR: "user input or configuration error",
    VERIFICATION_FAILURE: "verification failure",
    UNSAFE_OPERATION_BLOCKED: "unsafe operation blocked",
}
