from typing import Sequence, Optional, Mapping, Any, AsyncGenerator, Union
import asyncio
import inspect
import json
import logging
import math
import os
import re
import warnings
from asyncio import Task
from importlib.metadata import PackageNotFoundError, version
from ._utils import assert_valid_name
import tiktoken
from typing_extensions import Self, Unpack
from dataclasses import dataclass
from . import _deepseek_model_info
from autogen_core.logging import LLMCallEvent, LLMStreamEndEvent, LLMStreamStartEvent
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Type,
    Union,
    cast,
)
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    ChatCompletionTokenLogprob,
    CreateResult,
    LLMMessage,
    ModelCapabilities,  # type: ignore
    ModelFamily,
    ModelInfo,
    RequestUsage,
    SystemMessage,
    TopLogprob,
    UserMessage,
    validate_model_info,
)
from openai.types.chat.chat_completion import Choice
from openai.types.shared_params import (
    FunctionDefinition,
    FunctionParameters,
    ResponseFormatJSONObject,
    ResponseFormatText, ResponseFormatJSONSchema,
)
from openai import NOT_GIVEN, AsyncAzureOpenAI, AsyncOpenAI
from autogen_core import (
    EVENT_LOGGER_NAME,
    TRACE_LOGGER_NAME,
    CancellationToken,
    Component,
    FunctionCall,
    Image,
)
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionContentPartParam,
    ChatCompletionMessageParam,
    ChatCompletionRole,
    ChatCompletionToolParam,
    ParsedChatCompletion,
    ParsedChoice,
    completion_create_params,
)

from autogen_core import CancellationToken
from autogen_core.models import ChatCompletionClient, ModelInfo, ModelCapabilities, LLMMessage, RequestUsage, \
    CreateResult
from autogen_core.tools import Tool, ToolSchema
from pydantic import BaseModel
import asyncio
from ._transformation import (
    get_transformer,
)
from .config import (
    AzureOpenAIClientConfiguration,
    AzureOpenAIClientConfigurationConfigModel,
    OpenAIClientConfiguration,
    OpenAIClientConfigurationConfigModel,
)

from autogen_ext.models._utils.normalize_stop_reason import normalize_stop_reason
from autogen_ext.models._utils.parse_r1_content import parse_r1_content

logger = logging.getLogger(EVENT_LOGGER_NAME)
trace_logger = logging.getLogger(TRACE_LOGGER_NAME)

openai_init_kwargs = set(inspect.getfullargspec(AsyncOpenAI.__init__).kwonlyargs)
aopenai_init_kwargs = set(inspect.getfullargspec(AsyncAzureOpenAI.__init__).kwonlyargs)

create_kwargs = set(completion_create_params.CompletionCreateParamsBase.__annotations__.keys()) | set(
    ("timeout", "stream")
)
# Only single choice allowed
disallowed_create_args = set(["stream", "messages", "function_call", "functions", "n"])
required_create_args: Set[str] = set(["model"])

USER_AGENT_HEADER_NAME = "User-Agent"

try:
    version_info = version("autogen-ext")
except PackageNotFoundError:
    version_info = "dev"


def _openai_client_from_config(config: Mapping[str, Any]) -> AsyncOpenAI:
    # Shave down the config to just the OpenAI kwargs
    openai_config = {k: v for k, v in config.items() if k in openai_init_kwargs}
    return AsyncOpenAI(**openai_config)


def _create_args_from_config(config: Mapping[str, Any]) -> Dict[str, Any]:
    create_args = {k: v for k, v in config.items() if k in create_kwargs}
    create_args_keys = set(create_args.keys())
    if not required_create_args.issubset(create_args_keys):
        raise ValueError(f"Required create args are missing: {required_create_args - create_args_keys}")
    if disallowed_create_args.intersection(create_args_keys):
        raise ValueError(f"Disallowed create args are present: {disallowed_create_args.intersection(create_args_keys)}")
    return create_args


# TODO check types
# oai_system_message_schema = type2schema(ChatCompletionSystemMessageParam)
# oai_user_message_schema = type2schema(ChatCompletionUserMessageParam)
# oai_assistant_message_schema = type2schema(ChatCompletionAssistantMessageParam)
# oai_tool_message_schema = type2schema(ChatCompletionToolMessageParam)


def type_to_role(message: LLMMessage) -> ChatCompletionRole:
    if isinstance(message, SystemMessage):
        return "system"
    elif isinstance(message, UserMessage):
        return "user"
    elif isinstance(message, AssistantMessage):
        return "assistant"
    else:
        return "tool"


def to_oai_type(
        message: LLMMessage, prepend_name: bool = False, model: str = "unknown", model_family: str = ModelFamily.UNKNOWN
) -> Sequence[ChatCompletionMessageParam]:
    context = {
        "prepend_name": prepend_name,
    }
    transformers = get_transformer("openai", model, model_family)

    def raise_value_error(message: LLMMessage, context: Dict[str, Any]) -> Sequence[ChatCompletionMessageParam]:
        raise ValueError(f"Unknown message type: {type(message)}")

    transformer: Callable[[LLMMessage, Dict[str, Any]], Sequence[ChatCompletionMessageParam]] = transformers.get(
        type(message), raise_value_error
    )
    result = transformer(message, context)
    return result


def calculate_vision_tokens(image: Image, detail: str = "auto") -> int:
    MAX_LONG_EDGE = 2048
    BASE_TOKEN_COUNT = 85
    TOKENS_PER_TILE = 170
    MAX_SHORT_EDGE = 768
    TILE_SIZE = 512

    if detail == "low":
        return BASE_TOKEN_COUNT

    width, height = image.image.size

    # Scale down to fit within a MAX_LONG_EDGE x MAX_LONG_EDGE square if necessary

    if width > MAX_LONG_EDGE or height > MAX_LONG_EDGE:
        aspect_ratio = width / height
        if aspect_ratio > 1:
            # Width is greater than height
            width = MAX_LONG_EDGE
            height = int(MAX_LONG_EDGE / aspect_ratio)
        else:
            # Height is greater than or equal to width
            height = MAX_LONG_EDGE
            width = int(MAX_LONG_EDGE * aspect_ratio)

    # Resize such that the shortest side is MAX_SHORT_EDGE if both dimensions exceed MAX_SHORT_EDGE
    aspect_ratio = width / height
    if width > MAX_SHORT_EDGE and height > MAX_SHORT_EDGE:
        if aspect_ratio > 1:
            # Width is greater than height
            height = MAX_SHORT_EDGE
            width = int(MAX_SHORT_EDGE * aspect_ratio)
        else:
            # Height is greater than or equal to width
            width = MAX_SHORT_EDGE
            height = int(MAX_SHORT_EDGE / aspect_ratio)

    # Calculate the number of tiles based on TILE_SIZE

    tiles_width = math.ceil(width / TILE_SIZE)
    tiles_height = math.ceil(height / TILE_SIZE)
    total_tiles = tiles_width * tiles_height
    # Calculate the total tokens based on the number of tiles and the base token count

    total_tokens = BASE_TOKEN_COUNT + TOKENS_PER_TILE * total_tiles

    return total_tokens


def _add_usage(usage1: RequestUsage, usage2: RequestUsage) -> RequestUsage:
    return RequestUsage(
        prompt_tokens=usage1.prompt_tokens + usage2.prompt_tokens,
        completion_tokens=usage1.completion_tokens + usage2.completion_tokens,
    )


def convert_tools(
        tools: Sequence[Tool | ToolSchema],
) -> List[ChatCompletionToolParam]:
    result: List[ChatCompletionToolParam] = []
    for tool in tools:
        if isinstance(tool, Tool):
            tool_schema = tool.schema
        else:
            assert isinstance(tool, dict)
            tool_schema = tool

        result.append(
            ChatCompletionToolParam(
                type="function",
                function=FunctionDefinition(
                    name=tool_schema["name"],
                    description=(tool_schema["description"] if "description" in tool_schema else ""),
                    parameters=(
                        cast(FunctionParameters, tool_schema["parameters"]) if "parameters" in tool_schema else {}
                    ),
                    strict=(tool_schema["strict"] if "strict" in tool_schema else False),
                ),
            )
        )
    # Check if all tools have valid names.
    for tool_param in result:
        assert_valid_name(tool_param["function"]["name"])
    return result


def normalize_name(name: str) -> str:
    """
    LLMs sometimes ask functions while ignoring their own format requirements, this function should be used to replace invalid characters with "_".

    Prefer _assert_valid_name for validating user configuration or input
    """
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)[:64]


def count_tokens_openai(
        messages: Sequence[LLMMessage],
        model: str,
        *,
        add_name_prefixes: bool = False,
        tools: Sequence[Tool | ToolSchema] = [],
        model_family: str = ModelFamily.UNKNOWN,
) -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        trace_logger.warning(f"Model {model} not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    tokens_per_message = 3
    tokens_per_name = 1
    num_tokens = 0

    # Message tokens.
    for message in messages:
        num_tokens += tokens_per_message
        oai_message = to_oai_type(message, prepend_name=add_name_prefixes, model=model, model_family=model_family)
        for oai_message_part in oai_message:
            for key, value in oai_message_part.items():
                if value is None:
                    continue

                if isinstance(message, UserMessage) and isinstance(value, list):
                    typed_message_value = cast(List[ChatCompletionContentPartParam], value)

                    assert len(typed_message_value) == len(
                        message.content
                    ), "Mismatch in message content and typed message value"

                    # We need image properties that are only in the original message
                    for part, content_part in zip(typed_message_value, message.content, strict=False):
                        if isinstance(content_part, Image):
                            # TODO: add detail parameter
                            num_tokens += calculate_vision_tokens(content_part)
                        elif isinstance(part, str):
                            num_tokens += len(encoding.encode(part))
                        else:
                            try:
                                serialized_part = json.dumps(part)
                                num_tokens += len(encoding.encode(serialized_part))
                            except TypeError:
                                trace_logger.warning(f"Could not convert {part} to string, skipping.")
                else:
                    if not isinstance(value, str):
                        try:
                            value = json.dumps(value)
                        except TypeError:
                            trace_logger.warning(f"Could not convert {value} to string, skipping.")
                            continue
                    num_tokens += len(encoding.encode(value))
                    if key == "name":
                        num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>

    # Tool tokens.
    oai_tools = convert_tools(tools)
    for tool in oai_tools:
        function = tool["function"]
        tool_tokens = len(encoding.encode(function["name"]))
        if "description" in function:
            tool_tokens += len(encoding.encode(function["description"]))
        tool_tokens -= 2
        if "parameters" in function:
            parameters = function["parameters"]
            if "properties" in parameters:
                assert isinstance(parameters["properties"], dict)
                for propertiesKey in parameters["properties"]:  # pyright: ignore
                    assert isinstance(propertiesKey, str)
                    tool_tokens += len(encoding.encode(propertiesKey))
                    v = parameters["properties"][propertiesKey]  # pyright: ignore
                    for field in v:  # pyright: ignore
                        if field == "type":
                            tool_tokens += 2
                            tool_tokens += len(encoding.encode(v["type"]))  # pyright: ignore
                        elif field == "description":
                            tool_tokens += 2
                            tool_tokens += len(encoding.encode(v["description"]))  # pyright: ignore
                        elif field == "enum":
                            tool_tokens -= 3
                            for o in v["enum"]:  # pyright: ignore
                                tool_tokens += 3
                                tool_tokens += len(encoding.encode(o))  # pyright: ignore
                        else:
                            trace_logger.warning(f"Not supported field {field}")
                tool_tokens += 11
                if len(parameters["properties"]) == 0:  # pyright: ignore
                    tool_tokens -= 2
        num_tokens += tool_tokens
    num_tokens += 12
    return num_tokens


@dataclass
class CreateParams:
    messages: List[ChatCompletionMessageParam]
    tools: List[ChatCompletionToolParam]
    response_format: Optional[Type[BaseModel]]
    create_args: Dict[str, Any]


class MyDeepSeekClient(ChatCompletionClient, Component[OpenAIClientConfigurationConfigModel]):
    component_type = "model"
    component_config_schema = OpenAIClientConfigurationConfigModel
    component_provider_override = "deepseek_adapter.MyDeepSeekClient"

    def __init__(self, **kwargs: Unpack[OpenAIClientConfiguration]):
        if "model" not in kwargs:
            raise ValueError("model is required for OpenAIChatCompletionClient")
        self._raw_config: Dict[str, Any] = dict(kwargs).copy()
        copied_args = dict(kwargs).copy()

        model_info: Optional[ModelInfo] = None
        if "model_info" in kwargs:
            model_info = kwargs["model_info"]
            del copied_args["model_info"]

        add_name_prefixes: bool = False
        if "add_name_prefixes" in kwargs:
            add_name_prefixes = kwargs["add_name_prefixes"]

        # Special handling for Gemini model.
        assert "model" in copied_args and isinstance(copied_args["model"], str)
        if copied_args["model"].startswith("deepseek"):
            if "base_url" not in copied_args:
                copied_args["base_url"] = _deepseek_model_info.DEEPSEEK_OPENAI_BASE_URL
            if "api_key" not in copied_args and "DEEPSEEK_API_KEY" in os.environ:
                copied_args["api_key"] = os.environ["DEEPSEEK_API_KEY"]
        client = _openai_client_from_config(copied_args)
        create_args = _create_args_from_config(copied_args)

        self._client = client
        self._add_name_prefixes = add_name_prefixes

        if  model_info is None:
            try:
                self._model_info = _deepseek_model_info.get_info(create_args["model"])
            except KeyError as err:
                raise ValueError("model_info is required when model name is not a valid OpenAI model") from err
        # Validate model_info, check if all required fields are present
        validate_model_info(self._model_info)

        self._resolved_model: Optional[str] = None
        if "model" in create_args:
            self._resolved_model = _deepseek_model_info.resolve_model(create_args["model"])

        if (
                not self._model_info["json_output"]
                and "response_format" in create_args
                and (
                isinstance(create_args["response_format"], dict)
                and create_args["response_format"]["type"] == "json_object"
        )
        ):
            raise ValueError("Model does not support JSON output.")

        self._create_args = create_args
        self._total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self._actual_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

    async def create(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = [],
                     json_output: Optional[bool | type[BaseModel]] = None, extra_create_args: Mapping[str, Any] = {},
                     cancellation_token: Optional[CancellationToken] = None) -> CreateResult:
        create_params = self._process_create_args(
            messages,
            tools,
            json_output,
            extra_create_args,
        )
        future: Union[Task[ParsedChatCompletion[BaseModel]], Task[ChatCompletion]]
        if create_params.response_format is not None:
            # Use beta client if response_format is not None
            future = asyncio.ensure_future(
                self._client.chat.completions.create(
                    model=self._resolved_model,
                    messages=create_params.messages,
                    tools=(create_params.tools if len(create_params.tools) > 0 else NOT_GIVEN),
                    response_format={"type": "json_object"},
                )
            )
        else:
            # Use the regular client
            future = asyncio.ensure_future(
                self._client.chat.completions.create(
                    messages=create_params.messages,
                    stream=False,
                    tools=(create_params.tools if len(create_params.tools) > 0 else NOT_GIVEN),
                    **create_params.create_args,
                )
            )

        if cancellation_token is not None:
            cancellation_token.link_future(future)
        result: Union[ParsedChatCompletion[BaseModel], ChatCompletion] = await future
        if create_params.response_format is not None:
            result = cast(ParsedChatCompletion[Any], result)

        usage = RequestUsage(
            # TODO backup token counting
            prompt_tokens=result.usage.prompt_tokens if result.usage is not None else 0,
            completion_tokens=(result.usage.completion_tokens if result.usage is not None else 0),
        )

        logger.info(
            LLMCallEvent(
                messages=cast(List[Dict[str, Any]], create_params.messages),
                response=result.model_dump(),
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
            )
        )

        if self._resolved_model is not None:
            if self._resolved_model != result.model:
                warnings.warn(
                    f"Resolved model mismatch: {self._resolved_model} != {result.model}. "
                    "Model mapping in autogen_ext.models.openai may be incorrect. "
                    f"Set the model to {result.model} to enhance token/cost estimation and suppress this warning.",
                    stacklevel=2,
                )

        # Limited to a single choice currently.
        choice: Union[ParsedChoice[Any], ParsedChoice[BaseModel], Choice] = result.choices[0]

        # Detect whether it is a function call or not.
        # We don't rely on choice.finish_reason as it is not always accurate, depending on the API used.
        content: Union[str, List[FunctionCall]]
        thought: str | None = None
        if choice.message.function_call is not None:
            raise ValueError("function_call is deprecated and is not supported by this model client.")
        elif choice.message.tool_calls is not None and len(choice.message.tool_calls) > 0:
            if choice.finish_reason != "tool_calls":
                warnings.warn(
                    f"Finish reason mismatch: {choice.finish_reason} != tool_calls "
                    "when tool_calls are present. Finish reason may not be accurate. "
                    "This may be due to the API used that is not returning the correct finish reason.",
                    stacklevel=2,
                )
            if choice.message.content is not None and choice.message.content != "":
                # Put the content in the thought field.
                thought = choice.message.content
            # NOTE: If OAI response type changes, this will need to be updated
            content = []
            for tool_call in choice.message.tool_calls:
                if not isinstance(tool_call.function.arguments, str):
                    warnings.warn(
                        f"Tool call function arguments field is not a string: {tool_call.function.arguments}."
                        "This is unexpected and may due to the API used not returning the correct type. "
                        "Attempting to convert it to string.",
                        stacklevel=2,
                    )
                    if isinstance(tool_call.function.arguments, dict):
                        tool_call.function.arguments = json.dumps(tool_call.function.arguments)
                content.append(
                    FunctionCall(
                        id=tool_call.id,
                        arguments=tool_call.function.arguments,
                        name=normalize_name(tool_call.function.name),
                    )
                )
            finish_reason = "tool_calls"
        else:
            # if not tool_calls, then it is a text response and we populate the content and thought fields.
            finish_reason = choice.finish_reason
            content = choice.message.content or ""
            # if there is a reasoning_content field, then we populate the thought field. This is for models such as R1 - direct from deepseek api.
            if choice.message.model_extra is not None:
                reasoning_content = choice.message.model_extra.get("reasoning_content")
                if reasoning_content is not None:
                    thought = reasoning_content

        logprobs: Optional[List[ChatCompletionTokenLogprob]] = None
        if choice.logprobs and choice.logprobs.content:
            logprobs = [
                ChatCompletionTokenLogprob(
                    token=x.token,
                    logprob=x.logprob,
                    top_logprobs=[TopLogprob(logprob=y.logprob, bytes=y.bytes) for y in x.top_logprobs],
                    bytes=x.bytes,
                )
                for x in choice.logprobs.content
            ]

        #   This is for local R1 models.
        if isinstance(content, str) and self._model_info["family"] == ModelFamily.R1 and thought is None:
            thought, content = parse_r1_content(content)

        response = CreateResult(
            finish_reason=normalize_stop_reason(finish_reason),
            content=content,
            usage=usage,
            cached=False,
            logprobs=logprobs,
            thought=thought,
        )

        self._total_usage = _add_usage(self._total_usage, usage)
        self._actual_usage = _add_usage(self._actual_usage, usage)

        # TODO - why is this cast needed?
        return response

    def create_stream(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = [],
                      json_output: Optional[bool | type[BaseModel]] = None, extra_create_args: Mapping[str, Any] = {},
                      cancellation_token: Optional[CancellationToken] = None) -> AsyncGenerator[
        Union[str, CreateResult], None]:
        pass

    async def close(self) -> None:
        pass

    def actual_usage(self) -> RequestUsage:
        pass

    def total_usage(self) -> RequestUsage:
        pass

    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        pass

    def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        pass

    @property
    def capabilities(self) -> ModelCapabilities:
        pass

    @property
    def model_info(self) -> ModelInfo:
        return self._model_info

    def _rstrip_last_assistant_message(self, messages: Sequence[LLMMessage]) -> Sequence[LLMMessage]:
        """
        Remove the last assistant message if it is empty.
        """
        # When Claude models last message is AssistantMessage, It could not end with whitespace
        if isinstance(messages[-1], AssistantMessage):
            if isinstance(messages[-1].content, str):
                messages[-1].content = messages[-1].content.rstrip()

        return messages

    def _process_create_args(
            self,
            messages: Sequence[LLMMessage],
            tools: Sequence[Tool | ToolSchema],
            json_output: Optional[bool | type[BaseModel]],
            extra_create_args: Mapping[str, Any],
    ) -> CreateParams:
        # Make sure all extra_create_args are valid
        extra_create_args_keys = set(extra_create_args.keys())
        if not create_kwargs.issuperset(extra_create_args_keys):
            raise ValueError(f"Extra create args are invalid: {extra_create_args_keys - create_kwargs}")

        # Copy the create args and overwrite anything in extra_create_args
        create_args = self._create_args.copy()
        create_args.update(extra_create_args)

        # The response format value to use for the beta client.
        response_format_value: Optional[Type[BaseModel]] = None

        if "response_format" in create_args:
            # Legacy support for getting beta client mode from response_format.
            value = create_args["response_format"]
            if isinstance(value, type) and issubclass(value, BaseModel):
                if self.model_info["structured_output"] is False:
                    raise ValueError("Model does not support structured output.")
                warnings.warn(
                    "Using response_format to specify the BaseModel for structured output type will be deprecated. "
                    "Use json_output in create and create_stream instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                response_format_value = value
                # Remove response_format from create_args to prevent passing it twice.
                del create_args["response_format"]
            # In all other cases when response_format is set to something else, we will
            # use the regular client.

        if json_output is not None:
            create_args["response_format"] = ResponseFormatJSONObject(type="json_object")
            if isinstance(json_output, type) and issubclass(json_output, BaseModel):
                if self.model_info["structured_output"] is False:
                    raise ValueError("Model does not support structured output.")
                if response_format_value is not None:
                    raise ValueError(
                        "response_format and json_output cannot be set to a Pydantic model class at the same time."
                    )
                # Beta client mode with Pydantic model class.
                response_format_value = json_output
            else:
                raise ValueError(f"json_output must be a boolean or a Pydantic model class, got {type(json_output)}")

        if response_format_value is not None and "response_format" in create_args:
            warnings.warn(
                "response_format is found in extra_create_args while json_output is set to a Pydantic model class. "
                "Skipping the response_format in extra_create_args in favor of the json_output. "
                "Structured output will be used.",
                UserWarning,
                stacklevel=2,
            )
            # If using beta client, remove response_format from create_args to prevent passing it twice
            del create_args["response_format"]

        # TODO: allow custom handling.
        # For now we raise an error if images are present and vision is not supported
        if self.model_info["vision"] is False:
            for message in messages:
                if isinstance(message, UserMessage):
                    if isinstance(message.content, list) and any(isinstance(x, Image) for x in message.content):
                        raise ValueError("Model does not support vision and image was provided")

        if self.model_info["json_output"] is False and json_output is True:
            raise ValueError("Model does not support JSON output.")

        if not self.model_info.get("multiple_system_messages", False):
            # Some models accept only one system message(or, it will read only the last one)
            # So, merge system messages into one (if multiple and continuous)
            system_message_content = ""
            _messages: List[LLMMessage] = []
            _first_system_message_idx = -1
            _last_system_message_idx = -1
            # Index of the first system message for adding the merged system message at the correct position
            for idx, message in enumerate(messages):
                if isinstance(message, SystemMessage):
                    if _first_system_message_idx == -1:
                        _first_system_message_idx = idx
                    elif _last_system_message_idx + 1 != idx:
                        # That case, system message is not continuous
                        # Merge system messages only contiues system messages
                        raise ValueError(
                            "Multiple and Not continuous system messages are not supported if model_info['multiple_system_messages'] is False"
                        )
                    system_message_content += message.content + "\n"
                    _last_system_message_idx = idx
                else:
                    _messages.append(message)
            system_message_content = system_message_content.rstrip()
            if system_message_content != "":
                system_message = SystemMessage(content=system_message_content)
                _messages.insert(_first_system_message_idx, system_message)
            messages = _messages

        # in that case, for ad-hoc, we using startswith instead of model_family for code consistency
        if create_args.get("model", "unknown").startswith("claude-"):
            # When Claude models last message is AssistantMessage, It could not end with whitespace
            messages = self._rstrip_last_assistant_message(messages)

        oai_messages_nested = [
            to_oai_type(
                m,
                prepend_name=self._add_name_prefixes,
                model=create_args.get("model", "unknown"),
                model_family=self._model_info["family"],
            )
            for m in messages
        ]

        oai_messages = [item for sublist in oai_messages_nested for item in sublist]

        if self.model_info["function_calling"] is False and len(tools) > 0:
            raise ValueError("Model does not support function calling")

        converted_tools = convert_tools(tools)

        return CreateParams(
            messages=oai_messages,
            tools=converted_tools,
            response_format=response_format_value,
            create_args=create_args,
        )
