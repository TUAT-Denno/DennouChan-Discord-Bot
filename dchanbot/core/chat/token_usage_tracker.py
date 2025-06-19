from typing import Dict

from pydantic import BaseModel


class TokenUsage(BaseModel):
    """Stores token usage statistics.

    Attributes:
        input_tokens (int): Number of tokens in the user's input.
        output_tokens (int): Number of tokens in the model's output.
        total_tokens (int): Sum of input and output tokens.
    """
    input_tokens : int = 0
    output_tokens : int = 0
    total_tokens : int = 0


def update_token_usages(
    usages : Dict[str, TokenUsage],
    response,
    session_id : str
):
    """Update token usage statistics for a specific session ID.

    This function updates the input, output, and total token counts for the
    given session based on the response metadata provided by the Gemini API.

    Args:
        usages (Dict[str, TokenUsage]): Dictionary of session ID to usage data.
        response: The response object returned from the LLM, containing token usage metadata.
        session_id (str): The session ID for which the stats should be updated.

    Note:
        Token counting behavior depends on the Gemini API specification.
        See: https://ai.google.dev/gemini-api/docs/tokens?hl=ja&lang=python
    """
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
    """Update a single TokenUsage instance based on the response.

    Args:
        usage (TokenUsage): The usage object to update.
        response: The response object returned from the LLM, containing token usage metadata.
    """
    usage_dat : dict = response.usage_metadata
    usage.input_tokens  += int(usage_dat['input_tokens'])
    usage.output_tokens += int(usage_dat['output_tokens'])
    usage.total_tokens  += int(usage_dat['total_tokens'])
