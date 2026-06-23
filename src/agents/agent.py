import json
import logging
import os
from pathlib import Path
from typing import Annotated

from coze_coding_utils.runtime_ctx.context import default_headers
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_tool_call
from langchain_core.messages import AnyMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages

from storage.memory.memory_saver import get_memory_saver
from tools.difficulty_adapter import get_difficulty_level, update_difficulty_level
from tools.error_notebook import get_wrong_answers, mark_error_reviewed, record_wrong_answer
from tools.knowledge_graph import check_prerequisites, get_learning_path
from tools.learning_tracker import get_exercise_history, get_learning_progress, record_exercise_result
from tools.python_executor import execute_python_code
from tools.report_generator import generate_learning_report
from tools.web_search_tool import search_python_resources

logger = logging.getLogger(__name__)

LLM_CONFIG = "config/agent_llm_config.json"
MAX_MESSAGES = 60


def _windowed_messages(old, new):
    """Keep only the latest messages in the LangGraph state."""
    return add_messages(old, new)[-MAX_MESSAGES:]  # type: ignore


class AgentState(MessagesState):
    messages: Annotated[list[AnyMessage], _windowed_messages]


@wrap_tool_call
def handle_tool_errors(request, handler):
    """Handle tool execution errors."""
    try:
        return handler(request)
    except Exception as e:
        logger.warning(f"Tool '{request.tool_call.get('name', 'unknown')}' failed: {e}")
        return ToolMessage(
            content=f"Tool execution failed: {str(e)}\nPlease check the arguments and retry.",
            tool_call_id=request.tool_call["id"],
        )


def build_agent(ctx=None):
    workspace_path = os.getenv("COZE_WORKSPACE_PATH")
    if not workspace_path:
        workspace_path = str(Path(__file__).resolve().parents[2])

    config_path = os.path.join(workspace_path, LLM_CONFIG)
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    api_key = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("COZE_INTEGRATION_MODEL_BASE_URL") or os.getenv("OPENAI_BASE_URL")

    llm = ChatOpenAI(
        model=cfg["config"].get("model"),
        api_key=api_key,
        base_url=base_url,
        temperature=cfg["config"].get("temperature", 0.7),
        streaming=True,
        timeout=cfg["config"].get("timeout", 600),
        extra_body={
            "thinking": {
                "type": cfg["config"].get("thinking", "disabled"),
            },
        },
        default_headers=default_headers(ctx) if ctx else {},
    )

    tools = [
        execute_python_code,
        record_exercise_result,
        get_learning_progress,
        get_exercise_history,
        generate_learning_report,
        search_python_resources,
        record_wrong_answer,
        get_wrong_answers,
        mark_error_reviewed,
        get_difficulty_level,
        update_difficulty_level,
        check_prerequisites,
        get_learning_path,
    ]

    return create_agent(
        model=llm,
        system_prompt=cfg.get("sp"),
        tools=tools,
        middleware=[handle_tool_errors],
        checkpointer=get_memory_saver(),
        state_schema=AgentState,
    )