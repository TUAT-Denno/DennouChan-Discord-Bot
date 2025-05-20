from pathlib import Path
from typing import Type, Any

from .json_bound_model import JSONBoundModel, _T

class FileModelRegistry:
    def __init__(self, rootdir : Path):
        rootdir.mkdir(parents = True, exist_ok = True)
        self._rootdir = rootdir

        self._models: dict[str, JSONBoundModel[Any]] = {}

    def save_all(self):
        for model in self._models.values():
            try:
                model.save()
            except Exception as e:
                print(f"Failed to save {model._jsonpath}: {e}")

    def save(self, name : str):
        if name not in self._models.keys():
            raise ValueError(f"{name} is not registered with the FileModelRegistory.")

        model = self._models[name]
        try:
            model.save()
        except Exception as e:
            print(f"Failed to save {model._jsonpath}: {e}")

    def load(self, name : str, schema : Type[_T], subdir : Path = None) -> JSONBoundModel[_T]:
        if name in self._models.keys():
            return self._models[name]

        # まだロードされていない場合は、ファイルから読み込む
        jsonpath = self._rootdir / (subdir if subdir is not None else "") / Path(f"{name}.json")
        jsonmodel = JSONBoundModel(
            jsonfilename = jsonpath,
            schema = schema
        )
        jsonmodel.load()
        self._models[name] = jsonmodel

        return jsonmodel
