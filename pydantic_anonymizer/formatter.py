import copy
import logging
from typing import Any


class AnonymizedFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record = copy.copy(record)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: self._anonymize(v) for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(self._anonymize(a) for a in record.args)
            else:
                record.args = (self._anonymize(record.args),)
        return super().format(record)

    def _anonymize(self, obj: Any) -> Any:
        if hasattr(obj, "model_dump_anonymized"):
            return obj.model_dump_anonymized()
        if isinstance(obj, list):
            return [self._anonymize(item) for item in obj]
        if isinstance(obj, dict):
            return {k: self._anonymize(v) for k, v in obj.items()}
        return obj
