from pathlib import Path
from typing import Type, Any

from .json_bound_model import JSONBoundModel, _T

class FileModelRegistry:
    """Registry for managing JSONBoundModel instances backed by JSON files.

    This class helps load and save multiple JSON-based models
    from a specified root directory.

    Attributes:
        _rootdir (Path): Root directory where model JSON files are stored.
        _models (dict[str, JSONBoundModel]): Cached model instances loaded from disk.

    Examples:
        >>> from pydantic import BaseModel
        >>> from pathlib import Path
        >>> class Config(BaseModel):
        ...     theme: str = "dark"
        >>> reg = FileModelRegistry(Path("config"))
        >>> cfg_model = reg.load(name="settings", schema=Config)
        >>> cfg_model.data.theme = "light"
        >>> reg.save("settings")
        >>> reg.save_all()
    """

    def __init__(self, rootdir : Path):
        """Initialize the registry

        Args:
            rootdir (Path): The base directory where JSON files will be stored.
        """
        rootdir.mkdir(parents = True, exist_ok = True)  # Ensure the root directory exists
        self._rootdir = rootdir

        self._models: dict[str, JSONBoundModel[Any]] = {}

    def save_all(self):
        """Save all currently registered models to their respective JSON files.

        If saving any individual model fails, the error is printed but not raised.
        """
        for model in self._models.values():
            try:
                model.save()
            except Exception as e:
                print(f"Failed to save {model._jsonpath}: {e}")

    def save(self, name : str):
        """Save a specific registered model by name.

        Args:
            name (str): The identifier used to register the model.

        Raises:
            ValueError: If the model name has not been registered via `load`.
        """
        if name not in self._models.keys():
            raise ValueError(f"{name} is not registered with the FileModelRegistory.")

        model = self._models[name]
        try:
            model.save()
        except Exception as e:
            print(f"Failed to save {model._jsonpath}: {e}")

    def load(self, name : str, schema : Type[_T], subdir : Path = None) -> JSONBoundModel[_T]:
        """Load a model from file or retrieve a cached instance.

        Args:
            name (str): The identifier for the model (used as filename).
            schema (Type[_T]): Pydantic model class to parse the JSON data.
            subdir (Path, optional): Optional subdirectory under rootdir to load from.

        Returns:
            JSONBoundModel[_T]: The loaded or cached model instance.
        """
        if name in self._models.keys():
            return self._models[name]

        jsonpath = self._rootdir / (subdir if subdir is not None else "") / Path(f"{name}.json")
        jsonmodel = JSONBoundModel(
            jsonfilename = jsonpath,
            schema = schema
        )
        jsonmodel.load()
        self._models[name] = jsonmodel

        return jsonmodel
