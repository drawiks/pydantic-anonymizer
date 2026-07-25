from collections.abc import Callable
from typing import Any

from pydantic import BaseModel


def Anonymize(**field_strategies: str | bool) -> Callable:
    def decorator(cls: type) -> type:
        if not (isinstance(cls, type) and issubclass(cls, BaseModel)):
            raise TypeError(f"@Anonymize can only be applied to BaseModel subclasses, got {cls}")

        for field_name, strategy in field_strategies.items():
            if field_name not in cls.model_fields:
                raise ValueError(f"Field '{field_name}' not found in model {cls.__name__}")

        for field_name, strategy in field_strategies.items():
            field_info = cls.model_fields[field_name]
            extra = dict(field_info.json_schema_extra) if field_info.json_schema_extra else {}
            extra["anonymize"] = strategy
            field_info.json_schema_extra = extra

        from pydantic_anonymizer.anonymizer import Anonymizer

        if not issubclass(cls, Anonymizer):
            cls.__bases__ = (Anonymizer,) + cls.__bases__

        return cls

    return decorator
