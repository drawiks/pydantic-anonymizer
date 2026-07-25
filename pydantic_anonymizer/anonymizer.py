import json
import warnings
from collections.abc import Callable
from inspect import iscoroutinefunction
from typing import Any

from pydantic import BaseModel

from pydantic_anonymizer.registry import MaskRegistry


class Anonymizer:
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not any(
            isinstance(base, type) and issubclass(base, BaseModel)
            for base in cls.__bases__
            if base is not Anonymizer
        ):
            if any(base is Anonymizer for base in cls.__bases__):
                raise TypeError(
                    f"Anonymizer must be used together with a BaseModel subclass"
                )

    def model_dump_anonymized(self) -> dict[str, Any]:
        result = {}
        for field_name, field_info in self.__class__.model_fields.items():
            value = getattr(self, field_name)
            anonymize_config = self._get_anonymize_config(field_info)
            if anonymize_config is not None:
                result[field_name] = self._anonymize_value(value, anonymize_config)
            elif isinstance(value, BaseModel) and isinstance(value, Anonymizer):
                result[field_name] = value.model_dump_anonymized()
            elif isinstance(value, list):
                result[field_name] = self._anonymize_list(value)
            else:
                result[field_name] = value
        return result

    def model_dump_json_anonymized(self) -> str:
        data = self.model_dump_anonymized()
        return json.dumps(data, ensure_ascii=False, default=str)

    async def model_dump_anonymized_async(self) -> dict[str, Any]:
        result = {}
        for field_name, field_info in self.__class__.model_fields.items():
            value = getattr(self, field_name)
            anonymize_config = self._get_anonymize_config(field_info)
            if anonymize_config is not None:
                result[field_name] = await self._anonymize_value_async(value, anonymize_config)
            elif isinstance(value, BaseModel) and isinstance(value, Anonymizer):
                result[field_name] = await value.model_dump_anonymized_async()
            elif isinstance(value, list):
                result[field_name] = await self._anonymize_list_async(value)
            else:
                result[field_name] = value
        return result

    async def model_dump_json_anonymized_async(self) -> str:
        data = await self.model_dump_anonymized_async()
        return json.dumps(data, ensure_ascii=False, default=str)

    def _get_anonymize_config(self, field_info: Any) -> str | bool | None:
        json_schema_extra = getattr(field_info, "json_schema_extra", None)
        if json_schema_extra and isinstance(json_schema_extra, dict):
            return json_schema_extra.get("anonymize")
        return None

    def _anonymize_value(self, value: Any, config: str | bool) -> Any:
        if isinstance(value, BaseModel) and isinstance(value, Anonymizer):
            return value.model_dump_anonymized()

        if isinstance(value, BaseModel):
            warnings.warn(
                f"Field with anonymize config holds a non-Anonymizer BaseModel. "
                f"Add Anonymizer mixin to {type(value).__name__} for proper anonymization.",
                stacklevel=2,
            )
            return value.model_dump()

        if isinstance(value, list):
            return [self._anonymize_value(item, config) for item in value]

        if isinstance(value, str):
            mask_func = MaskRegistry.get(config)
            if mask_func:
                if iscoroutinefunction(mask_func):
                    raise TypeError(
                        f"Mask '{config}' is an async function. "
                        f"Use model_dump_anonymized_async() instead."
                    )
                return mask_func(value)
            return value

        if isinstance(value, (int, float)):
            warnings.warn(
                f"Anonymize config '{config}' is set but value is {type(value).__name__}, not str. "
                f"Value will not be anonymized.",
                stacklevel=2,
            )

        return value

    async def _anonymize_value_async(self, value: Any, config: str | bool) -> Any:
        if isinstance(value, BaseModel) and isinstance(value, Anonymizer):
            return await value.model_dump_anonymized_async()

        if isinstance(value, BaseModel):
            warnings.warn(
                f"Field with anonymize config holds a non-Anonymizer BaseModel. "
                f"Add Anonymizer mixin to {type(value).__name__} for proper anonymization.",
                stacklevel=2,
            )
            return value.model_dump()

        if isinstance(value, list):
            return [await self._anonymize_value_async(item, config) for item in value]

        if isinstance(value, str):
            mask_func = MaskRegistry.get(config)
            if mask_func:
                if iscoroutinefunction(mask_func):
                    return await mask_func(value)
                return mask_func(value)
            return value

        if isinstance(value, (int, float)):
            warnings.warn(
                f"Anonymize config '{config}' is set but value is {type(value).__name__}, not str. "
                f"Value will not be anonymized.",
                stacklevel=2,
            )

        return value

    def _anonymize_list(self, items: list[Any]) -> list[Any]:
        result = []
        for item in items:
            if isinstance(item, BaseModel) and isinstance(item, Anonymizer):
                result.append(item.model_dump_anonymized())
            elif isinstance(item, BaseModel):
                result.append(item.model_dump())
            elif isinstance(item, list):
                result.append(self._anonymize_list(item))
            else:
                result.append(item)
        return result

    async def _anonymize_list_async(self, items: list[Any]) -> list[Any]:
        result = []
        for item in items:
            if isinstance(item, BaseModel) and isinstance(item, Anonymizer):
                result.append(await item.model_dump_anonymized_async())
            elif isinstance(item, BaseModel):
                result.append(item.model_dump())
            elif isinstance(item, list):
                result.append(await self._anonymize_list_async(item))
            else:
                result.append(item)
        return result
