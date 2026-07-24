import pytest
from pydantic import BaseModel, Field

from pydantic_anonymizer import Anonymizer, MaskRegistry
from pydantic_anonymizer.masks import mask_card, mask_generic, mask_phone


class TestMasks:
    def test_generic_email(self):
        assert mask_generic("ivan@mail.com") == "i***@***.com"

    def test_generic_short_email(self):
        assert mask_generic("a@b.com") == "a***@***.com"

    def test_generic_no_at(self):
        assert mask_generic("hello") == "h***"

    def test_generic_single_char(self):
        assert mask_generic("a") == "*"

    def test_generic_empty(self):
        assert mask_generic("") == ""

    def test_card_standard(self):
        assert mask_card("4242111122223333") == "4242-****-****-3333"

    def test_card_with_dashes(self):
        assert mask_card("4242-1111-2222-3333") == "4242-****-****-3333"

    def test_card_short(self):
        assert mask_card("42421111") == "4242-1111"

    def test_card_very_short(self):
        assert mask_card("4242") == "****"

    def test_phone_standard(self):
        result = mask_phone("+380500223785")
        assert result == "+380 (***) ***-**-85"

    def test_phone_usa(self):
        assert mask_phone("+14155552671") == "+1 (***) ***-**-71"

    def test_phone_uk(self):
        assert mask_phone("+447911123456") == "+44 (***) ***-**-56"

    def test_phone_russia(self):
        assert mask_phone("+79161234567") == "+7 (***) ***-**-67"

    def test_phone_germany(self):
        assert mask_phone("+4915112345678") == "+49 (***) ***-**-78"

    def test_phone_china(self):
        assert mask_phone("+8613812345678") == "+86 (***) ***-**-78"

    def test_phone_short(self):
        result = mask_phone("+1234")
        assert "*" in result

    def test_phone_empty(self):
        assert mask_phone("") == ""

    def test_phone_invalid(self):
        result = mask_phone("not a phone")
        assert result == "not a phone"


class TestRegistry:
    def test_custom_strategy(self):
        def mask_ssn(value: str) -> str:
            return "***-**-" + value[-4:]

        MaskRegistry.register("ssn", mask_ssn)
        assert MaskRegistry.get("ssn") == mask_ssn
        assert "ssn" in MaskRegistry.list_strategies()

    def test_unknown_strategy(self):
        assert MaskRegistry.get("unknown") is None


class TestAnonymizerMixin:
    def test_model_dump_anonymized(self):
        class UserProfile(BaseModel, Anonymizer):
            username: str
            email: str = Field(json_schema_extra={"anonymize": True})
            card_number: str = Field(json_schema_extra={"anonymize": "card"})
            phone_number: str = Field(json_schema_extra={"anonymize": "phone"})

        user = UserProfile(
            username="ivan_dev",
            email="ivan@mail.com",
            card_number="4242111122223333",
            phone_number="+380500223785",
        )

        result = user.model_dump_anonymized()
        assert result["username"] == "ivan_dev"
        assert result["email"] == "i***@***.com"
        assert result["card_number"] == "4242-****-****-3333"
        assert "+380" in result["phone_number"]

    def test_model_dump_not_anonymized(self):
        class UserProfile(BaseModel, Anonymizer):
            email: str = Field(json_schema_extra={"anonymize": True})

        user = UserProfile(email="ivan@mail.com")
        result = user.model_dump()
        assert result["email"] == "ivan@mail.com"

    def test_model_dump_json_anonymized(self):
        import json

        class UserProfile(BaseModel, Anonymizer):
            email: str = Field(json_schema_extra={"anonymize": True})

        user = UserProfile(email="ivan@mail.com")
        result = json.loads(user.model_dump_json_anonymized())
        assert result["email"] == "i***@***.com"

    def test_nested_model(self):
        class Address(BaseModel, Anonymizer):
            city: str
            street: str = Field(json_schema_extra={"anonymize": True})

        class UserProfile(BaseModel, Anonymizer):
            name: str
            address: Address

        user = UserProfile(
            name="ivan",
            address=Address(city="Moscow", street="Lenina 1"),
        )

        result = user.model_dump_anonymized()
        assert result["name"] == "ivan"
        assert result["address"]["city"] == "Moscow"
        assert result["address"]["street"] != "Lenina 1"

    def test_list_of_models(self):
        class Item(BaseModel, Anonymizer):
            value: str = Field(json_schema_extra={"anonymize": True})

        class Container(BaseModel, Anonymizer):
            items: list[Item]

        container = Container(items=[Item(value="secret1"), Item(value="secret2")])
        result = container.model_dump_anonymized()
        assert result["items"][0]["value"] != "secret1"
        assert result["items"][1]["value"] != "secret2"
        assert result["items"][0]["value"].startswith("s")
        assert result["items"][1]["value"].startswith("s")

    def test_custom_mask_via_registry(self):
        def mask_ssn(value: str) -> str:
            return "***-**-" + value[-4:]

        MaskRegistry.register("ssn", mask_ssn)

        class Person(BaseModel, Anonymizer):
            ssn: str = Field(json_schema_extra={"anonymize": "ssn"})

        person = Person(ssn="123-45-6789")
        result = person.model_dump_anonymized()
        assert result["ssn"] == "***-**-6789"

    def test_field_without_anonymize(self):
        class UserProfile(BaseModel, Anonymizer):
            name: str
            age: int

        user = UserProfile(name="ivan", age=25)
        result = user.model_dump_anonymized()
        assert result == {"name": "ivan", "age": 25}
