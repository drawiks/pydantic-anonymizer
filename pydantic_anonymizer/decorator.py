from typing import Any, Callable

from pydantic import BaseModel
from pydantic.fields import FieldInfo


def Anonymize(**field_strategies: bool | str) -> Callable:
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
            cls.model_fields[field_name] = FieldInfo(
                annotation=field_info.annotation,
                default=field_info.default,
                default_factory=field_info.default_factory,
                alias=field_info.alias,
                alias_priority=field_info.alias_priority,
                validation_alias=field_info.validation_alias,
                serialization_alias=field_info.serialization_alias,
                title=field_info.title,
                description=field_info.description,
                json_schema_extra=extra,
            )

        from pydantic_anonymizer.anonymizer import Anonymizer

        if Anonymizer not in cls.__bases__:
            cls.__bases__ = (Anonymizer,) + cls.__bases__

        return cls

    return decorator
