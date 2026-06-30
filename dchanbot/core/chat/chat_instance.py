import logging

from dataclasses import dataclass
from typing import TypedDict, Annotated

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from core.chat.prompt_manager import PromptManager


logger = logging.getLogger(__name__)


class ChatState(TypedDict):
    request_content: str
    messages: Annotated[list[BaseMessage], add_messages]

@dataclass(frozen = True)
class ChatRequest:
    content: str

@dataclass(frozen = True)
class ChatResponse:
    content: str
class ChatInstance:
    def __init__(
        self,
        model: BaseChatModel,
        prompt_manager: PromptManager
    ):
        self._model = model
        self._prompt_manager = prompt_manager

        graph_builder = StateGraph(ChatState)

        # Add nodes
        graph_builder.add_node("prepare", self._prepare)
        graph_builder.add_node("generate", self._generate)

        # Add edges to connect nodes
        graph_builder.add_edge(START, "prepare")
        graph_builder.add_edge("prepare", "generate")
        graph_builder.add_edge("generate", END)

        # Compile the graph
        self._graph = graph_builder.compile()

    async def _prepare(self, state: ChatState) -> dict:
        prompt = self._prompt_manager.get("denno_chan")

        return {
            "messages": [
                SystemMessage(content = prompt.system_prompt),
                HumanMessage(content = state["request_content"]),
            ],
        }

    async def _generate(self, state: ChatState) -> dict:
        logger.debug(
            "Invoking model with messages: %s",
            [type(message).__name__ for message in state["messages"]],
        )

        response = await self._model.ainvoke(state["messages"])

        return {
            "messages": [response],
        }

    async def chat(self, request : ChatRequest) -> ChatResponse:
        result = await self._graph.ainvoke(
            {
                "request_content": request.content,
                "messages": [],
            }
        )

        message = result["messages"][-1]

        logger.debug(
            "AI response: type=%s content=%r blocks=%r",
            type(message).__name__,
            message.content,
            message.content_blocks,
        )

        content = message.text
        if not isinstance(content, str):
            raise TypeError(
                f"Expected string response content, got {type(content).__name__}"
            )

        return ChatResponse(content=content)
