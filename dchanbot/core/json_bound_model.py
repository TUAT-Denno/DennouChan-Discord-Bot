import json
from pathlib import Path
from typing import Type, TypeVar, Generic, Any, Dict

from pydantic import BaseModel

_T = TypeVar('T', bound = BaseModel)


def dict_to_json(dic : Dict[str, _T], jsonfilename : Path):
    jsonpath = jsonfilename.resolve()
    jsonpath.parent.mkdir(parents = True, exist_ok = True)

    serializable = {k: v.model_dump() for k, v in dic.items()}
    with jsonpath.open("w", encoding = "utf-8") as file:
        json.dump(serializable, file, indent = 4)

def dict_from_json(jsonfilename : Path, model_class : Type[_T]) -> Dict[str, _T]:
    jsonpath = jsonfilename.resolve()
    if not jsonpath.exists():
        return {}

    with jsonpath.open("r", encoding = "utf-8") as file:
        raw_data = json.load(file)
    return {k: model_class(**v) for k, v in raw_data.items()}


class JSONBoundModel(Generic[_T]):
    def __init__(self, jsonfilename : Path, schema : Type[_T]):
        self._jsonpath = jsonfilename.resolve()
        self._schema = schema
        self.data : _T = schema()    # データのメモリキャッシュ

    # データをJSONファイルから読み込む
    def load(self):
        if self._jsonpath.exists():
            with self._jsonpath.open(mode="r", encoding="utf-8") as f:
                raw = json.load(f)
                self.data = self._schema(**raw)
        else:
            self.data = self._schema()

    # データをJSONファイルに保存
    def save(self):
        self._jsonpath.parent.mkdir(parents = True, exist_ok = True)
        with self._jsonpath.open(mode = 'w', encoding="utf-8") as f:
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
