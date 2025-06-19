"""Utility module for binding Pydantic models to JSON file.

Provides functions and a helper class for loading/saving dictionaries or single
instances of Pydantic models to and from JSON files.
"""

import json
from pathlib import Path
from typing import Type, TypeVar, Generic, Any, Dict

from pydantic import BaseModel


_T = TypeVar('T', bound = BaseModel)


def dict_to_json(dic : Dict[str, _T], jsonfilename : Path):
    """Serialize a dictionary of Pydantic models to a JSON file.

    Args:
        dic (Dict[str, _T]): Dictionary where values are Pydantic model instances.
        jsonfilename (Path): Path to the output JSON file.
    """
    jsonpath = jsonfilename.resolve()
    jsonpath.parent.mkdir(parents = True, exist_ok = True)

    serializable = {k: v.model_dump() for k, v in dic.items()}
    with jsonpath.open("w", encoding = "utf-8") as file:
        json.dump(serializable, file, indent = 4)

def dict_from_json(jsonfilename : Path, model_class : Type[_T]) -> Dict[str, _T]:
    """Load a dictionary of Pydantic models from a JSON file.

    Args:
        jsonfilename (Path): Path to the input JSON file.
        model_class (Type[_T]): The Pydantic model class to instantiate.

    Returns:
        Dict[str, _T]: Dictionary of instantiated models.
    """
    jsonpath = jsonfilename.resolve()
    if not jsonpath.exists():
        return {}

    with jsonpath.open("r", encoding = "utf-8") as file:
        raw_data = json.load(file)
    return {k: model_class(**v) for k, v in raw_data.items()}


class JSONBoundModel(Generic[_T]):
    """Binds a Pydantic model to a JSON file for simple persistent storage.
    
    Attributes:
        data (_T): In-memory instance of the model, initialized from file or default.

    Examples:
        >>> from pydantic import BaseModel
        >>> from pathlib import Path
        >>> class Person(BaseModel):
        ...     name: str = ""
        ...     age: int = 0
        ...     id: int = 0
        >>> model = JSONBoundModel(Path("persons.json"), Person)
        >>> model.data.name = "John Smith"
        >>> model.data.age = 20
        >>> model.data.id = 1234567
        >>> model.save()  # Save to file
    """

    def __init__(self, jsonfilename : Path, schema : Type[_T]):
        """Initialize the JSONBoundModel.

        Args:
            jsonfilename (Path): Path to the JSON file for persistence.
            schema (Type[_T]): Pydantic model class to use as schema.
        """
        self._jsonpath = jsonfilename.resolve()
        self._schema = schema
        self.data : _T = schema()    # In-memory cache of the data

    def load(self):
        """Load the model data from the JSON file."""
        if self._jsonpath.exists():
            with self._jsonpath.open(mode="r", encoding="utf-8") as f:
                raw = json.load(f)
                self.data = self._schema(**raw)
        else:
            self.data = self._schema()

    def save(self):
        """Save the current model data to the JSON file."""
        self._jsonpath.parent.mkdir(parents = True, exist_ok = True)
        with self._jsonpath.open(mode = 'w', encoding="utf-8") as f:
            json.dump(self.data.model_dump(), f, indent = 4)

    def get(self, *keys: str) -> Any:
        """Retrieve a nested attribute from the model.

        Args:
            *keys (str): Sequence of attribute names to access nested fields.

        Returns:
            Any: The value of the requested nested attribute.
        """
        obj = self.data
        for key in keys:
            obj = getattr(obj, key)
        return obj

    def set(self, *keys: str, value: Any) -> None:
        """Set a value for a nested attribute in the model.

        Args:
            *keys (str): Sequence of attribute names to access nested fields.
            value (Any): The value to assign.
        """
        obj = self.data
        for key in keys[:-1]:
            obj = getattr(obj, key)
        setattr(obj, keys[-1], value)
