from typing import Dict

from pydantic import BaseModel


class TokenUsage(BaseModel):
    input_tokens : int = 0
    output_tokens : int = 0
    total_tokens : int = 0


#
#  渡されたresponseデータをもとにトークン使用量を更新する
#  Geminiにおけるトークンのカウント方法については次のURLを参照：
#    https://ai.google.dev/gemini-api/docs/tokens?hl=ja&lang=python
#
def update_token_usages(
    usages : Dict[str, TokenUsage],
    response,
    session_id : str
):
    usage_dat : dict = response.usage_metadata
    if session_id in usages.keys():
        tokusage = usages[session_id]
        tokusage.input_tokens += int(usage_dat['input_tokens'])
        tokusage.output_tokens += int(usage_dat['output_tokens'])
        tokusage.total_tokens += int(usage_dat['total_tokens'])
    else:
        usages[session_id] = TokenUsage(
            input_tokens = int(usage_dat['input_tokens']),
            output_tokens = int(usage_dat['output_tokens']),
            total_tokens = int(usage_dat['total_tokens'])
        )

def update_token_usage(
    usage : TokenUsage,
    response,
):
    usage_dat : dict = response.usage_metadata
    usage.input_tokens  += int(usage_dat['input_tokens'])
    usage.output_tokens += int(usage_dat['output_tokens'])
    usage.total_tokens  += int(usage_dat['total_tokens'])
