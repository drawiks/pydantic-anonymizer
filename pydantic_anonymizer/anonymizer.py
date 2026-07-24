from typing import Any

from pydantic import BaseModel

from pydantic_anonymizer.registry import MaskRegistry


class Anonymizer:
    def model_dump_anonymized(self, **kwargs: Any) -> dict[str, Any]:
        result = {}
        for field_name, field_info in self.__class__.model_fields.items():
            value = getattr(self, field_name)
            anonymize_config = self._get_anonymize_config(field_info)
            if anonymize_config is not None:
                result[field_name] = self._anonymize_value(value, anonymize_config)
            elif isinstance(value, BaseModel) and isinstance(value, Anonymizer):
                result[field_name] = value.model_dump_anonymized(**kwargs)
            elif isinstance(value, list):
                result[field_name] = self._anonymize_list(value, kwargs)
            else:
                result[field_name] = value
        return result

    def model_dump_json_anonymized(self, **kwargs: Any) -> str:
        import json
        data = self.model_dump_anonymized(**kwargs)
        return json.dumps(data, ensure_ascii=False, default=str)

    def _anonymize_list(self, items: list[Any], kwargs: dict[str, Any]) -> list[Any]:
        result = []
        for item in items:
            if isinstance(item, BaseModel) and isinstance(item, Anonymizer):
                result.append(item.model_dump_anonymized(**kwargs))
            elif isinstance(item, list):
                result.append(self._anonymize_list(item, kwargs))
            else:
                result.append(item)
        return result

    def _get_anonymize_config(self, field_info: Any) -> bool | str | None:
        json_schema_extra = getattr(field_info, "json_schema_extra", None)
        if json_schema_extra and isinstance(json_schema_extra, dict):
            return json_schema_extra.get("anonymize")
        return None

    def _anonymize_value(self, value: Any, config: bool | str) -> Any:
        if isinstance(value, BaseModel) and isinstance(value, Anonymizer):
            return value.model_dump_anonymized()

        if isinstance(value, list):
            return [self._anonymize_value(item, config) for item in value]

        if isinstance(value, str):
            mask_func = MaskRegistry.get(config)
            if mask_func:
                return mask_func(value)
            return value

        return value
