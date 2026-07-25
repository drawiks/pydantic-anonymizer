from importlib.metadata import PackageNotFoundError, version

from pydantic_anonymizer.anonymizer import Anonymizer
from pydantic_anonymizer.decorator import Anonymize
from pydantic_anonymizer.formatter import AnonymizedFormatter
from pydantic_anonymizer.registry import MaskRegistry

try:
    __version__ = version("pydantic-anonymizer")
except PackageNotFoundError:
    __version__ = "0.3.0"

__all__ = ["Anonymizer", "Anonymize", "AnonymizedFormatter", "MaskRegistry"]
