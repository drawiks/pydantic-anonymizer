import asyncio
import logging
import re

import pytest
from pydantic import BaseModel, Field

from pydantic_anonymizer import Anonymize, AnonymizedFormatter, Anonymizer, MaskRegistry
from pydantic_anonymizer.masks import (
    mask_birthdate,
    mask_card,
    mask_generic,
    mask_iban,
    mask_ip,
    mask_name,
    mask_phone,
)


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

    def test_generic_email_no_dot(self):
        assert mask_generic("user@localhost") == "u***@***"

    def test_card_standard(self):
        assert mask_card("4242111122223333") == "4242-****-****-3333"

    def test_card_with_dashes(self):
        assert mask_card("4242-1111-2222-3333") == "4242-****-****-3333"

    def test_card_short(self):
        assert mask_card("42421111") == "4242-1111"

    def test_card_very_short(self):
        assert mask_card("4242") == "****"

    def test_card_non_standard_length(self):
        result = mask_card("424211112222")
        assert result.startswith("4242")
        assert result.endswith("2222")
        assert "****" in result

    def test_card_12_digits(self):
        result = mask_card("424211112222")
        assert result.startswith("4242")
        assert "****" in result

    def test_card_10_digits(self):
        result = mask_card("4242111122")
        assert result.startswith("4242")
        assert "****" in result

    def test_unknown_anonymize_config(self):
        class User(BaseModel, Anonymizer):
            email: str = Field(json_schema_extra={"anonymize": "unknown_strategy"})

        u = User(email="test@mail.com")
        result = u.model_dump_anonymized()
        assert result["email"] == "test@mail.com"

    def test_phone_standard(self):
        assert mask_phone("+380500223785") == "+380 (***) ***-**-85"

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
        assert "*" in mask_phone("+1234")

    def test_phone_empty(self):
        assert mask_phone("") == ""

    def test_phone_invalid(self):
        assert mask_phone("not a phone") == "not a phone"

    def test_phone_short_national(self):
        result = mask_phone("+38050")
        assert "+380" in result
        assert "**" in result

    def test_ip_v4(self):
        assert mask_ip("192.168.1.100") == "192.168.***.***"

    def test_ip_loopback(self):
        assert mask_ip("127.0.0.1") == "127.0.***.***"

    def test_ip_invalid(self):
        assert mask_ip("not-an-ip") == "***.***.***.***"

    def test_birthdate_dot(self):
        assert mask_birthdate("15.03.1990") == "**.**.1990"

    def test_birthdate_dash(self):
        assert mask_birthdate("15-03-1990") == "**-**-1990"

    def test_birthdate_slash(self):
        assert mask_birthdate("03/15/1990") == "**/**/1990"

    def test_birthdate_invalid(self):
        assert mask_birthdate("not-a-date") == "not-a-date"

    def test_name_two_words(self):
        assert mask_name("Иван Петров") == "И*** П*****"

    def test_name_single(self):
        assert mask_name("Иван") == "И***"

    def test_name_three_words(self):
        assert mask_name("Иван Сергеевич Петров") == "И*** С******** П*****"

    def test_name_single_char(self):
        assert mask_name("A B") == "* *"

    def test_iban_standard(self):
        result = mask_iban("UA213996220000000002600123356712")
        assert result.startswith("UA21")
        assert result.endswith("6712")
        assert "*" in result

    def test_iban_short(self):
        assert mask_iban("UA213996") == "********"

    def test_iban_with_spaces(self):
        result = mask_iban("UA21 3996 2200 0000 0002 6001 2335 6712")
        assert result.startswith("UA21")
        assert result.endswith("6712")


class TestRegistry:
    def test_custom_strategy(self):
        def mask_ssn(value: str) -> str:
            return "***-**-" + value[-4:]

        MaskRegistry.register("ssn", mask_ssn)
        assert MaskRegistry.get("ssn") == mask_ssn
        assert "ssn" in MaskRegistry.list_strategies()

    def test_unknown_strategy(self):
        assert MaskRegistry.get("unknown") is None

    def test_builtin_strategies_exist(self):
        assert MaskRegistry.get(True) is not None
        assert MaskRegistry.get("card") is not None
        assert MaskRegistry.get("phone") is not None
        assert MaskRegistry.get("ip") is not None
        assert MaskRegistry.get("birthdate") is not None
        assert MaskRegistry.get("name") is not None
        assert MaskRegistry.get("iban") is not None


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

    def test_new_strategies_in_model(self):
        class Data(BaseModel, Anonymizer):
            ip: str = Field(json_schema_extra={"anonymize": "ip"})
            birthdate: str = Field(json_schema_extra={"anonymize": "birthdate"})
            full_name: str = Field(json_schema_extra={"anonymize": "name"})
            iban: str = Field(json_schema_extra={"anonymize": "iban"})

        d = Data(
            ip="10.0.0.1",
            birthdate="25.12.1990",
            full_name="Иван Петров",
            iban="UA213996220000000002600123356712",
        )

        result = d.model_dump_anonymized()
        assert result["ip"] == "10.0.***.***"
        assert result["birthdate"] == "**.**.1990"
        assert result["full_name"] == "И*** П*****"
        assert result["iban"].startswith("UA21")
        assert result["iban"].endswith("6712")

    def test_nested_list_of_lists(self):
        class Container(BaseModel, Anonymizer):
            data: list[list[str]]

        c = Container(data=[["a", "b"], ["c", "d"]])
        result = c.model_dump_anonymized()
        assert result["data"] == [["a", "b"], ["c", "d"]]

    def test_nested_model_with_anonymize_config(self):
        class Inner(BaseModel, Anonymizer):
            secret: str = Field(json_schema_extra={"anonymize": True})

        class Outer(BaseModel, Anonymizer):
            inner: Inner = Field(json_schema_extra={"anonymize": True})

        o = Outer(inner=Inner(secret="password123"))
        result = o.model_dump_anonymized()
        assert result["inner"]["secret"] != "password123"

    def test_list_field_with_anonymize_config(self):
        class User(BaseModel, Anonymizer):
            emails: list[str] = Field(json_schema_extra={"anonymize": True})

        u = User(emails=["a@b.com", "c@d.com"])
        result = u.model_dump_anonymized()
        assert result["emails"][0] != "a@b.com"
        assert result["emails"][1] != "c@d.com"

    def test_non_string_field_with_anonymize_config(self):
        class Data(BaseModel, Anonymizer):
            count: int = Field(json_schema_extra={"anonymize": True})

        d = Data(count=42)
        result = d.model_dump_anonymized()
        assert result["count"] == 42

    def test_int_field_in_list(self):
        class Container(BaseModel, Anonymizer):
            numbers: list[int]

        c = Container(numbers=[1, 2, 3])
        result = c.model_dump_anonymized()
        assert result["numbers"] == [1, 2, 3]

    def test_non_string_non_mask_field(self):
        class Data(BaseModel, Anonymizer):
            value: int = Field(json_schema_extra={"anonymize": True})

        d = Data(value=42)
        result = d.model_dump_anonymized()
        assert result["value"] == 42


class TestDecorator:
    def test_decorator_basic(self):
        @Anonymize(email=True)
        class User(BaseModel):
            username: str
            email: str

        user = User(username="ivan", email="ivan@mail.com")
        assert hasattr(user, "model_dump_anonymized")
        result = user.model_dump_anonymized()
        assert result["email"] == "i***@***.com"
        assert result["username"] == "ivan"

    def test_decorator_multiple_strategies(self):
        @Anonymize(email=True, card="card", phone="phone")
        class Payment(BaseModel):
            email: str
            card: str
            phone: str

        p = Payment(
            email="a@b.com",
            card="4242111122223333",
            phone="+380500223785",
        )

        result = p.model_dump_anonymized()
        assert result["email"] == "a***@***.com"
        assert result["card"] == "4242-****-****-3333"
        assert "+380" in result["phone"]

    def test_decorator_not_base_model(self):
        with pytest.raises(TypeError):

            @Anonymize(email=True)
            class NotAModel:
                email: str

    def test_decorator_invalid_field(self):
        with pytest.raises(ValueError):

            @Anonymize(nonexistent=True)
            class User(BaseModel):
                email: str


class TestAsync:
    def test_async_dump(self):
        class User(BaseModel, Anonymizer):
            email: str = Field(json_schema_extra={"anonymize": True})

        user = User(email="test@mail.com")
        result = asyncio.run(user.model_dump_anonymized_async())
        assert result["email"] == "t***@***.com"

    def test_async_json_dump(self):
        import json

        class User(BaseModel, Anonymizer):
            email: str = Field(json_schema_extra={"anonymize": True})

        user = User(email="test@mail.com")
        result = asyncio.run(user.model_dump_json_anonymized_async())
        assert json.loads(result)["email"] == "t***@***.com"


class TestFormatter:
    def test_formatter_anonymizes(self):
        class User(BaseModel, Anonymizer):
            email: str = Field(json_schema_extra={"anonymize": True})

        formatter = AnonymizedFormatter("%(message)s")
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="User: %s", args=(User(email="ivan@mail.com"),), exc_info=None,
        )
        formatted = formatter.format(record)
        assert "i***@***.com" in formatted

    def test_formatter_passthrough(self):
        formatter = AnonymizedFormatter("%(message)s")
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="plain text", args=None, exc_info=None,
        )
        assert formatter.format(record) == "plain text"

    def test_formatter_with_list(self):
        class User(BaseModel, Anonymizer):
            email: str = Field(json_schema_extra={"anonymize": True})

        formatter = AnonymizedFormatter("%(message)s")
        users = [User(email="a@b.com"), User(email="c@d.com")]
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Users: %s", args=(users,), exc_info=None,
        )
        formatted = formatter.format(record)
        assert "a***@***.com" in formatted
        assert "c***@***.com" in formatted

    def test_formatter_with_dict_args(self):
        class User(BaseModel, Anonymizer):
            email: str = Field(json_schema_extra={"anonymize": True})

        formatter = AnonymizedFormatter("%(message)s")
        user = User(email="test@mail.com")
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="User: %(user)s",
            args=({"user": user},),
            exc_info=None,
        )
        formatted = formatter.format(record)
        assert "t***@***.com" in formatted

    def test_formatter_with_single_arg(self):
        class User(BaseModel, Anonymizer):
            email: str = Field(json_schema_extra={"anonymize": True})

        formatter = AnonymizedFormatter("%(message)s")
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="User: %s",
            args=(User(email="single@mail.com"),),
            exc_info=None,
        )
        formatted = formatter.format(record)
        assert "s***@***.com" in formatted

    def test_formatter_with_dict_in_args(self):
        formatter = AnonymizedFormatter("%(message)s")
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Data: %(data)s",
            args=({"data": {"key": "value"}},),
            exc_info=None,
        )
        formatted = formatter.format(record)
        assert "value" in formatted
