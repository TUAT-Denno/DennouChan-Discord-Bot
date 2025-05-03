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
        self._confpath.parent.mkdir(parents = True, exist_ok = True)
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


class ConfigRegistry:
    def __init__(self, rootdir : Path):
        rootdir.mkdir(parents = True, exist_ok = True)
        self._rootdir = rootdir

        self._configs: dict[str, Config[Any]] = {}

    def save_all(self):
        for config in self._configs.values():
            try:
                config.save()
            except Exception as e:
                print(f"Failed to save {config._confpath}: {e}")

    def load(self, name : str, schema : Type[_T], subdir : Path = None) -> Config[_T]:
        if name in self._configs.keys():
            return self._configs[name]

        # まだロードされていない場合は、ファイルから読み込む
        confpath = self._rootdir / (subdir if subdir is not None else "") / Path(f"{name}.json")
        config = Config(
            filename = confpath,
            schema = schema
        )
        config.load()
        self._configs[name] = config

        return config
