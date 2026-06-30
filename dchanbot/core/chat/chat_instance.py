import logging

from dataclasses import dataclass
from typing import TypedDict, Annotated

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages


logger = logging.getLogger(__name__)


class ChatState(TypedDict):
    messages: Annotated[list, add_messages]

@dataclass(frozen = True)
class ChatRequest:
    content: str

@dataclass(frozen = True)
class ChatResponse:
    content: str
class ChatInstance:
    def __init__(self, model: BaseChatModel):
        self._model = model

        graph_builder = StateGraph(ChatState)

        # Add nodes
        graph_builder.add_node("chat", self._generate)

        # Add edges to connect nodes
        graph_builder.add_edge(START, "chat")
        graph_builder.add_edge("chat", END)

        # Compile the graph
        self._graph = graph_builder.compile()

    async def _generate(self, state: ChatState) -> dict:
        response = await self._model.ainvoke(state["messages"])

        return {
            "messages": [response],
        }

    async def chat(self, request : ChatRequest) -> ChatResponse:
        result = await self._graph.ainvoke(
            {
                "messages": [
                    HumanMessage(content=request.content),
                ]
            }
        )

        message = result["messages"][-1]

        logger.debug(
            "AI response: type=%s content=%r blocks=%r",
            type(message).__name__,
            message.content,
            message.content_blocks,
        )

        content = str(message.text)
        if not isinstance(content, str):
            raise TypeError(
                f"Expected string response content, got {type(content).__name__}"
            )

        return ChatResponse(content=content)
