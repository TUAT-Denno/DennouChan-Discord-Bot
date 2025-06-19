from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable

from .token_usage_tracker import TokenUsage, update_token_usage

class Summarizer:
    def __init__(self, google_api_key : str):
        self._tokusage = TokenUsage()

        # LLMの準備
        self._llm = ChatGoogleGenerativeAI(
            model = "gemini-1.5-pro",
            google_api_key = google_api_key
        )

        # プロンプト設定
        self._prompt = PromptTemplate.from_template(
            "次の内容を要約してください：\n{text}"
        )

        self._chain : Runnable = self._llm | self._prompt

    async def summarize(self, text : str) -> str:
        response = self._chain.ainvoke(
            {"text" : text}
        )

        # TODO: Add exception handling

        update_token_usage(self._tokusage, response)

        return response.content
    
    @property
    def token_usage(self) -> TokenUsage:
        return self._tokusage
