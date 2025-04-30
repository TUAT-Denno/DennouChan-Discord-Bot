import json
from pathlib import Path
from typing import Type, TypeVar, Generic, Any

from pydantic import BaseModel

_T = TypeVar('T', bound = BaseModel)

class Config(Generic[_T]):
    def __init__(self, filename : Path, schema : Type[_T]):
        abspath = filename.resolve()

        self._confpath = abspath
        self._schema = schema
        self.data : _T = schema()    # 設定データのメモリキャッシュ

    # 設定をファイルから読み込む
    def load(self):
        if self._confpath.exists():
            with self._confpath.open(mode="r", encoding="utf-8") as f:
                raw = json.load(f)
                self.data = self._schema(**raw)
        else:
            self.data = self._schema()

    # 設定をファイルに保存
    def save(self):
        with self._confpath.open(mode = 'w', encoding="utf-8") as f:
            json.dump(self.data.model_dump(), f, indent = 4)

    def get(self, *keys: str) -> Any:
        obj = self.data
        for key in keys:
            obj = getattr(obj, key)
        return obj

    def set(self, *keys: str, value: Any) -> None:
        obj = self.data
        for key in keys[:-1]:
            obj = getattr(obj, key)
        setattr(obj, keys[-1], value)
