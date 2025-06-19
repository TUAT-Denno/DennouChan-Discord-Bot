import asyncio
from typing import Dict
from pathlib import Path
from datetime import datetime

from pydantic import BaseModel

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.prompts.chat import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import BaseChatMessageHistory

from .history import ChatHistory
from .token_usage_tracker import TokenUsage, update_token_usage

from .summarizer import Summarizer
from core.json_bound_model import dict_to_json, dict_from_json


class ChatStatistic(BaseModel):
    chat_count : int = 0
    tokusage : TokenUsage = TokenUsage()


class ChatInstances:
    def __init__(self, api_key : str, data_dir : Path):
        self._data_dir = data_dir.resolve()
        self._data_dir.mkdir(parents = True, exist_ok = True)

        # Chat用LLMの準備
        self._llm = ChatGoogleGenerativeAI(
            model = "gemini-2.0-flash",
            google_api_key = api_key,
        )

        # 要約の準備
        self._summarizer = Summarizer(
            google_api_key = api_key
        )

        self._runnables : Dict[str, RunnableWithMessageHistory] = {}
        self._prompts   : Dict[str, ChatPromptTemplate] = {}
        self._histories : Dict[str, ChatHistory] = {}

        # 前回までのChat統計データの読み込み
        stats_path = self._data_dir / "stats.json"
        self._stats = dict_from_json(stats_path, ChatStatistic)

    async def create_instance(self, session_id : str):
        if session_id in self._runnables.keys():
            return
        
        #retriever = generate_retriever()

        if session_id not in self._stats.keys():
            self._stats[session_id] = ChatStatistic()

        prompt = self._init_prompt(session_id)
        await self._init_history(session_id)

        # Runnableの構築
        chain = (
            {
                "input"   : lambda x: x["input"],
                "history" : lambda x: x["history"],
                #"context" : lambda x: retriever.get_relevant_documents(x["input"])
            }
            | prompt
            | self._llm
        )
        self._runnables[session_id] = RunnableWithMessageHistory(
            runnable = chain,
            get_session_history = lambda session_id: self._get_session_history(session_id),
            input_messages_key = "input",
            history_messages_key = "history"            
        )

    async def chat(self, session_id : str, user_input : str) -> str:
        if session_id not in self._runnables.keys():
            await self.create_instance(session_id)

        runnable = self._runnables[session_id]
        now = datetime.now().timestamp()

        try:
            response = await runnable.ainvoke(
                {"input" : user_input},
                config = {
                    "configurable" : {"session_id" : session_id},
                    "metadata" : {
                        "timestamp" : now
                    }
                }
            )
        except Exception as e:
            # 暫定的処理
            return (
                "内部エラーが発生しました。しばらくしてからもう一度お試しください。\n"
                f"{e}"
            )

        response.additional_kwargs["timestamp"] = now

        self._stats[session_id].chat_count += 1
        update_token_usage(self._stats[session_id].tokusage, response)

        return response.content
    
    async def save_all_session(self):
        # Historyの保存
        asyncio.gather(*[
            history.flush_to_db()
            for history in self._histories.values()
        ])
        
        # Chat統計データの保存
        stats_path = self._data_dir / "stats.json"
        dict_to_json(self._stats, stats_path)

    def get_statistic(self, session_id : str) -> ChatStatistic:
        if session_id in self._stats.keys():
            return self._stats[session_id]
        else:
            return ChatStatistic()
        
    def get_all_token_usage(self) -> TokenUsage:
        all_usages = TokenUsage()
        for stat in self._stats.values():
            all_usages.input_tokens  += stat.tokusage.input_tokens
            all_usages.output_tokens += stat.tokusage.output_tokens
            all_usages.total_tokens  += stat.tokusage.total_tokens

        if isinstance(self._summarizer, Summarizer):
            usage = self._summarizer.token_usage
            all_usages.input_tokens  += usage.input_tokens
            all_usages.output_tokens += usage.output_tokens
            all_usages.total_tokens  += usage.total_tokens

        return all_usages

    def _init_prompt(self, session_id : str) -> ChatPromptTemplate:
        if session_id in self._prompts.keys():
            return self._prompts[session_id]

        sys_prompt = SystemMessagePromptTemplate.from_template("""
"あなたは{circle_name}"という{univ_name}大学のサークルのマスコット「{character_name}」です。
性別：{sex}
一人称：{first_person}
性格：{personality}
口調：{speaking_style}
特徴：{characteristic}                                                
与えられた情報を活用して、親しみやすく返答してください。
""")        

        character_config = {
            "circle_name": "電脳サークル",
            "univ_name": "東京農工",
            "character_name": "電脳ちゃん",
            "sex": "女性",
            "first_person": "私",
            "personality": "無愛想、無表情でかつ毒舌家だが、主人のことはそれなりに慕っている。",
            "speaking_style": "丁寧で落ち着いた口調",
            "characteristic": "頭に2本のコンデンサーが生えている。"
        }

        human_prompt = HumanMessagePromptTemplate.from_template("{input}")
        prompt_template = ChatPromptTemplate.from_messages([
            sys_prompt,
            MessagesPlaceholder(variable_name = "history"),
            human_prompt
        ])
    
        self._prompts[session_id] = prompt_template.partial(**character_config)

        return self._prompts[session_id]
    
    async def _init_history(self, session_id : str):
        if session_id in self._histories.keys():
            return self._histories[session_id]
        
        db_path = self._data_dir / "history" / f"chat_history_{session_id}.db"
        self._histories[session_id] = ChatHistory(
            session_id = session_id,
            db_path = db_path,
            summarizer = self._summarizer
        )
        await self._histories[session_id].load_all_messages()

    def _get_session_history(self, session_id : str) -> BaseChatMessageHistory:
        return self._histories[session_id]
