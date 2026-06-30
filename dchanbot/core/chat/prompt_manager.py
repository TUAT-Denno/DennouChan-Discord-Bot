import json

from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path

class PromptLoadError(RuntimeError):
    """ Exception when the prompt settings could not be loaded. """

@dataclass(frozen=True)
class PromptDefinition:
    name: str
    version: int
    system_prompt: str

class PromptManager:
    def __init__(self, prompt_dir : str | Path):
        self._prompt_dir = Path(prompt_dir)
        self._cache: dict[str, PromptDefinition] = {}

    def get(self, prompt_name: str) -> PromptDefinition:
        if prompt_name not in self._cache:
            self._cache[prompt_name] = self._load(prompt_name)

        return self._cache[prompt_name]
    
    def reload(self, prompt_name: str) -> PromptDefinition:
        prompt = self._load(prompt_name)
        self._cache[prompt_name] = prompt
        return prompt
    
    def _load(self, prompt_name: str) -> PromptDefinition:
        path = self._prompt_dir / f"{prompt_name}.json"

        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError as exc:
            raise PromptLoadError(
                f"Prompt file not found: {path}"
            ) from exc
        except JSONDecodeError as exc:
            raise PromptLoadError(
                f"Invalid JSON in prompt file: {path}"
            ) from exc
        except OSError as exc:
            raise PromptLoadError(
                f"Failed to read prompt file: {path}"
            ) from exc

        if not isinstance(data, dict):
            raise PromptLoadError(
                f"Prompt file root must be an object: {path}"
            )

        name = data.get("name")
        version = data.get("version")
        system_prompt = data.get("system_prompt")

        if not isinstance(name, str) or not name.strip():
            raise PromptLoadError(
                f"'name' must be a non-empty string: {path}"
            )

        if not isinstance(version, int) or isinstance(version, bool):
            raise PromptLoadError(
                f"'version' must be an integer: {path}"
            )

        if not isinstance(system_prompt, str) or not system_prompt.strip():
            raise PromptLoadError(
                f"'system_prompt' must be a non-empty string: {path}"
            )

        return PromptDefinition(
            name=name,
            version=version,
            system_prompt=system_prompt.strip(),
        )
