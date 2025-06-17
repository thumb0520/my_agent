import asyncio
import os
import sys
import time
from typing import AsyncGenerator, Awaitable, Callable, Dict, List, Optional, TypeVar, Union, cast

from autogen_core import CancellationToken
from autogen_core.models import RequestUsage

from autogen_agentchat.base import Response, TaskResult
from autogen_agentchat.messages import (
    BaseAgentEvent,
    BaseChatMessage,
    ModelClientStreamingChunkEvent,
    MultiModalMessage,
    ToolCallRequestEvent,
    TextMessage,
    ToolCallExecutionEvent,
    ToolCallSummaryMessage,
)
from autogen_ext.agents.openai._openai_agent import ImageMessage

from .WebResponse import WebResponse


def _is_running_in_iterm() -> bool:
    return os.getenv("TERM_PROGRAM") == "iTerm.app"


def _is_output_a_tty() -> bool:
    return sys.stdout.isatty()


SyncInputFunc = Callable[[str], str]
AsyncInputFunc = Callable[[str, Optional[CancellationToken]], Awaitable[str]]
InputFuncType = Union[SyncInputFunc, AsyncInputFunc]

T = TypeVar("T", bound=TaskResult | Response)


def aprint(output: str, end: str = "\n", flush: bool = False) -> Awaitable[None]:
    return asyncio.to_thread(print, output, end=end, flush=flush)


async def WebUiResponseConsole(
        stream: AsyncGenerator[BaseAgentEvent | BaseChatMessage | T, None],
        *,
        no_inline_images: bool = False,
        output_stats: bool = False,
):
    """
    Consumes the message stream from :meth:`~autogen_agentchat.base.TaskRunner.run_stream`
    or :meth:`~autogen_agentchat.base.ChatAgent.on_messages_stream` and renders the messages to the console.
    Returns the last processed TaskResult or Response.

    .. note::

        `output_stats` is experimental and the stats may not be accurate.
        It will be improved in future releases.

    Args:
        stream (AsyncGenerator[BaseAgentEvent | BaseChatMessage | TaskResult, None] | AsyncGenerator[BaseAgentEvent | BaseChatMessage | Response, None]): Message stream to render.
            This can be from :meth:`~autogen_agentchat.base.TaskRunner.run_stream` or :meth:`~autogen_agentchat.base.ChatAgent.on_messages_stream`.
        no_inline_images (bool, optional): If terminal is iTerm2 will render images inline. Use this to disable this behavior. Defaults to False.
        output_stats (bool, optional): (Experimental) If True, will output a summary of the messages and inline token usage info. Defaults to False.

    Returns:
        last_processed: A :class:`~autogen_agentchat.base.TaskResult` if the stream is from :meth:`~autogen_agentchat.base.TaskRunner.run_stream`
            or a :class:`~autogen_agentchat.base.Response` if the stream is from :meth:`~autogen_agentchat.base.ChatAgent.on_messages_stream`.
    """
    render_image_iterm = _is_running_in_iterm() and _is_output_a_tty() and not no_inline_images
    start_time = time.time()
    total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

    streaming_chunks: List[str] = []

    async for message in stream:
        if isinstance(message, TaskResult):
            duration = time.time() - start_time
            if output_stats:
                output = {
                    "number_of_messages": len(message.messages),
                    "finish_reason": message.stop_reason,
                    "total_prompt_tokens": total_usage.prompt_tokens,
                    "total_completion_tokens": total_usage.completion_tokens,
                    "duration": duration,
                    "source": message.source,
                }
                yield WebResponse("task_result", output)

        elif isinstance(message, Response):
            duration = time.time() - start_time
            # Print final response.
            if isinstance(message.chat_message, MultiModalMessage):
                final_content = message.chat_message.to_text(iterm=render_image_iterm)
            else:
                final_content = message.chat_message.to_text()
            output = f"{'-' * 10} {message.chat_message.source} {'-' * 10}\n{final_content}\n"
            if message.chat_message.models_usage:
                if output_stats:
                    output += f"[Prompt tokens: {message.chat_message.models_usage.prompt_tokens}, Completion tokens: {message.chat_message.models_usage.completion_tokens}]\n"
                total_usage.completion_tokens += message.chat_message.models_usage.completion_tokens
                total_usage.prompt_tokens += message.chat_message.models_usage.prompt_tokens
            # Print summary.
            if output_stats:
                if message.inner_messages is not None:
                    num_inner_messages = len(message.inner_messages)
                else:
                    num_inner_messages = 0
                output = {
                    "number_of_inner_messages": num_inner_messages,
                    "total_prompt_tokens": total_usage.prompt_tokens,
                    "total_completion_tokens": total_usage.completion_tokens,
                    "duration": duration,
                }
                yield WebResponse("response", output)
        else:
            # Cast required for mypy to be happy
            message = cast(BaseAgentEvent | BaseChatMessage, message)  # type: ignore
            if isinstance(message, ModelClientStreamingChunkEvent):
                output = {
                    "message": message.to_text(),
                    "source": message.source,
                }
                yield WebResponse("model_client_stream_chunk", output)
                streaming_chunks.append(message.content)
            else:
                if streaming_chunks:
                    streaming_chunks.clear()
                elif isinstance(message, MultiModalMessage):
                    output = {
                        "message": message.to_text(iterm=render_image_iterm),
                        "source": message.source,
                    }
                    yield WebResponse("multi_model_message", output)
                elif isinstance(message, ToolCallRequestEvent):
                    output = {
                        "message": message.to_text(),
                        "source": message.source,
                    }
                    yield WebResponse("tool_call_request", output)
                elif isinstance(message, ToolCallExecutionEvent):
                    output = {
                        "message": message.to_text(),
                        "source": message.source,
                    }
                    yield WebResponse("tool_call_execute", output)
                elif isinstance(message, TextMessage):
                    output = {
                        "message": message.to_text(),
                        "source": message.source,
                    }
                    yield WebResponse("text_message", output)
                elif isinstance(message, ToolCallSummaryMessage):
                    output = {
                        "message": message.to_text(),
                        "source": message.source,
                    }
                    yield WebResponse("tool_call_summary", output)
                else:
                    print(f"Unhandled message type: {type(message)}")
                    print(f"Unhandled message: {message.to_text()}")
                    output = {
                        "message": message.to_text(),
                        "source": message.source,
                    }
                    yield WebResponse("unknown", output)
                if message.models_usage:
                    if output_stats:
                        await aprint(
                            f"[Prompt tokens: {message.models_usage.prompt_tokens}, Completion tokens: {message.models_usage.completion_tokens}]",
                            end="\n",
                            flush=True,
                        )
                    total_usage.completion_tokens += message.models_usage.completion_tokens
                    total_usage.prompt_tokens += message.models_usage.prompt_tokens


def default_output(message: BaseAgentEvent | BaseChatMessage | TaskResult):
    output = {
        "message": message.to_text(),
        "source": message.source,
    }
    return output
