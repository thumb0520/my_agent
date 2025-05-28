import logging
from typing import Dict

from autogen_core import EVENT_LOGGER_NAME, TRACE_LOGGER_NAME
from autogen_core.models import ModelFamily, ModelInfo

logger = logging.getLogger(EVENT_LOGGER_NAME)
trace_logger = logging.getLogger(TRACE_LOGGER_NAME)

# This is a moving target, so correctness is checked by the model value returned by openai against expected values at runtime``
_MODEL_POINTERS = {
    # deepseek models
    "deepseek-chat": "deepseek-chat",
}

_MODEL_INFO: Dict[str, ModelInfo] = {
    "deepseek-chat": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.R1,
        "structured_output": True,
        "multiple_system_messages": False,
    },
    "deepseek-reasoner": {
        "vision": False,
        "function_calling": False,
        "json_output": False,
        "family": ModelFamily.R1,
        "structured_output": False,
        "multiple_system_messages": False,
    }
}

_MODEL_TOKEN_LIMITS: Dict[str, int] = {
    "deepseek-chat": 200000,
    "deepseek-reasoner": 200000,
}

DEEPSEEK_OPENAI_BASE_URL = "https://api.deepseek.com/v1"


def resolve_model(model: str) -> str:
    if model in _MODEL_POINTERS:
        return _MODEL_POINTERS[model]
    return model


def get_info(model: str) -> ModelInfo:
    # If call it, that mean is that the config does not have cumstom model_info
    resolved_model = resolve_model(model)
    model_info: ModelInfo = _MODEL_INFO.get(
        resolved_model,
        {
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "family": "FAILED",
            "structured_output": False,
        },
    )
    if model_info.get("family") == "FAILED":
        raise ValueError("model_info is required when model name is not a valid OpenAI model")
    if model_info.get("family") == ModelFamily.UNKNOWN:
        trace_logger.warning(f"Model info not found for model: {model}")

    return model_info


def get_token_limit(model: str) -> int:
    resolved_model = resolve_model(model)
    return _MODEL_TOKEN_LIMITS[resolved_model]
