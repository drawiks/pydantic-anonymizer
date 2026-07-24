from typing import Callable

from pydantic_anonymizer.masks import mask_card, mask_generic, mask_phone


class MaskRegistry:
    _strategies: dict[str, Callable[[str], str]] = {}

    @classmethod
    def register(cls, name: str, func: Callable[[str], str]) -> None:
        cls._strategies[name] = func

    @classmethod
    def get(cls, name: str) -> Callable[[str], str] | None:
        return cls._strategies.get(name)

    @classmethod
    def list_strategies(cls) -> list[str]:
        return list(cls._strategies.keys())


MaskRegistry.register(True, mask_generic)
MaskRegistry.register("card", mask_card)
MaskRegistry.register("phone", mask_phone)
