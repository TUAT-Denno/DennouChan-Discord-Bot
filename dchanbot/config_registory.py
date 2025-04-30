from typing import Any

from config import Config


class ConfigRegistry:
    def __init__(self):
        self._configs: list[Config[Any]] = []

    def register(self, config: Config[Any]):
        self._configs.append(config)

    def save_all(self):
        for config in self._configs:
            try:
                config.save()
            except Exception as e:
                print(f"Failed to save {config.path}: {e}")

    def load_all(self):
        for config in self._configs:
            try:
                config.load()
            except Exception as e:
                print(f"Failed to load {config.path}: {e}")
