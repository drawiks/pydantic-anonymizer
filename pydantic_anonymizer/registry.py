from collections.abc import Callable

from pydantic_anonymizer.masks import mask_birthdate, mask_card, mask_email, mask_iban, mask_ip, mask_name, mask_phone


class MaskRegistry:
    _strategies: dict[str, Callable[[str], str]] = {}

    @classmethod
    def register(cls, name: str, func: Callable[[str], str]) -> None:
        cls._strategies[name] = func

    @classmethod
    def unregister(cls, name: str) -> None:
        cls._strategies.pop(name, None)

    @classmethod
    def get(cls, name: str | bool) -> Callable[[str], str] | None:
        if name is True:
            name = "generic"
        return cls._strategies.get(name)

    @classmethod
    def list_strategies(cls) -> list[str]:
        return list(cls._strategies.keys())


MaskRegistry.register("generic", mask_email)
MaskRegistry.register("email", mask_email)
MaskRegistry.register("card", mask_card)
MaskRegistry.register("phone", mask_phone)
MaskRegistry.register("ip", mask_ip)
MaskRegistry.register("birthdate", mask_birthdate)
MaskRegistry.register("name", mask_name)
MaskRegistry.register("iban", mask_iban)
