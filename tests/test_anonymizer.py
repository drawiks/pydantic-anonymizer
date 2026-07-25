import asyncio
import logging
import warnings

import pytest
from pydantic import BaseModel, Field

from pydantic_anonymizer import Anonymize, AnonymizedFormatter, Anonymizer, MaskRegistry
from pydantic_anonymizer.masks import (
    mask_birthdate,
    mask_card,
    mask_email,
    mask_iban,
    mask_ip,
    mask_name,
    mask_phone,
)


class TestMasks:
    def test_email_standard(self):
        assert mask_email("ivan@mail.com") == "i***@***.com"

    def test_email_short(self):
        assert mask_email("a@b.com") == "a***@***.com"

    def test_email_no_at(self):
        assert mask_email("hello") == "h***"

    def test_email_single_char(self):
        assert mask_email("a") == "*"

    def test_email_empty(self):
        assert mask_email("") == ""

    def test_email_no_dot(self):
        assert mask_email("user@localhost") == "u***@***"

    def test_email_at_not_email(self):
        result = mask_email("cost is $5@shop")
        assert "@" in result
        assert result.startswith("c")

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

    def test_card_10_digits(self):
        result = mask_card("4242111122")
        assert result.startswith("4242")
        assert "****" in result

    def test_card_no_digits(self):
        assert mask_card("abc") == "*"

    def test_card_special_chars(self):
        assert mask_card("!@#$%^&*()") == "*"

    def test_card_empty(self):
        assert mask_card("") == "*"

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

    def test_phone_alpha(self):
        result = mask_phone("1-800-FLOWERS")
        assert "*" in result

    def test_ip_v4(self):
        assert mask_ip("192.168.1.100") == "192.168.***.***"

    def test_ip_loopback(self):
        assert mask_ip("127.0.0.1") == "127.0.***.***"

    def test_ip_invalid(self):
        assert mask_ip("not-an-ip") == "***.***.***.***"

    def test_birthdate_dot(self):
        assert mask_birthdate("15.03.1990") == "**.**.****"

    def test_birthdate_dash(self):
        assert mask_birthdate("15-03-1990") == "**-**-****"

    def test_birthdate_slash(self):
        assert mask_birthdate("03/15/1990") == "**/**/****"

    def test_birthdate_iso(self):
        assert mask_birthdate("1990-03-15") == "****-**-**"

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
        assert result.startswith("UA")
        assert result.endswith("6712")
        assert "*" in result

    def test_iban_short(self):
        assert mask_iban("UA213996") == "********"

    def test_iban_exactly_8(self):
        assert mask_iban("UA213996") == "********"

    def test_iban_with_spaces(self):
        result = mask_iban("UA21 3996 2200 0000 0002 6001 2335 6712")
        assert result.startswith("UA")
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
        assert MaskRegistry.get("generic") is not None
        assert MaskRegistry.get("email") is not None
        assert MaskRegistry.get("card") is not None
        assert MaskRegistry.get("phone") is not None
        assert MaskRegistry.get("ip") is not None
        assert MaskRegistry.get("birthdate") is not None
        assert MaskRegistry.get("name") is not None
        assert MaskRegistry.get("iban") is not None

    def test_true_maps_to_generic(self):
        assert MaskRegistry.get(True) is MaskRegistry.get("generic")

    def test_unregister(self):
        def mask_temp(value: str) -> str:
            return "temp"

        MaskRegistry.register("temp", mask_temp)
        assert MaskRegistry.get("temp") is not None
        MaskRegistry.unregister("temp")
        assert MaskRegistry.get("temp") is None

    def test_unregister_nonexistent(self):
        MaskRegistry.unregister("nonexistent_12345")

    def test_overwrite_strategy(self):
        def mask_v1(value: str) -> str:
            return "v1"

        def mask_v2(value: str) -> str:
            return "v2"

        MaskRegistry.register("overwrite_test", mask_v1)
        assert MaskRegistry.get("overwrite_test") == mask_v1
        MaskRegistry.register("overwrite_test", mask_v2)
        assert MaskRegistry.get("overwrite_test") == mask_v2
        MaskRegistry.unregister("overwrite_test")


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
        assert result["birthdate"] == "**.**.****"
        assert result["full_name"] == "И*** П*****"
        assert result["iban"].startswith("UA")
        assert result["iban"].endswith("6712")

    def test_nested_list_of_lists(self):
        class Container(BaseModel, Anonymizer):
            data: list[list[str]]

        c = Container(data=[["a", "b"], ["c", "d"]])
        result = c.model_dump_anonymized()
        assert result["data"] == [["a", "b"], ["c", "d"]]

    def test_sync_list_with_non_anonymizer_basemodel(self):
        class PlainItem(BaseModel):
            data: str

        class Container(BaseModel, Anonymizer):
            items: list[PlainItem]

        c = Container(items=[PlainItem(data="v1"), PlainItem(data="v2")])
        result = c.model_dump_anonymized()
        assert result["items"][0]["data"] == "v1"
        assert result["items"][1]["data"] == "v2"

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
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = d.model_dump_anonymized()
            assert result["count"] == 42
            assert len(w) == 1
            assert "not str" in str(w[0].message)

    def test_int_field_in_list(self):
        class Container(BaseModel, Anonymizer):
            numbers: list[int]

        c = Container(numbers=[1, 2, 3])
        result = c.model_dump_anonymized()
        assert result["numbers"] == [1, 2, 3]

    def test_non_string_non_mask_field_no_warning(self):
        class Data(BaseModel, Anonymizer):
            value: int

        d = Data(value=42)
        result = d.model_dump_anonymized()
        assert result["value"] == 42

    def test_three_level_nesting(self):
        class Level3(BaseModel, Anonymizer):
            secret: str = Field(json_schema_extra={"anonymize": True})

        class Level2(BaseModel, Anonymizer):
            inner: Level3

        class Level1(BaseModel, Anonymizer):
            middle: Level2

        l1 = Level1(middle=Level2(inner=Level3(secret="deep_value")))
        result = l1.model_dump_anonymized()
        assert result["middle"]["inner"]["secret"] != "deep_value"
        assert "d***" in result["middle"]["inner"]["secret"]

    def test_dict_field(self):
        class Data(BaseModel, Anonymizer):
            metadata: dict

        d = Data(metadata={"key": "value"})
        result = d.model_dump_anonymized()
        assert result["metadata"] == {"key": "value"}

    def test_non_anonymizer_basemodel_field(self):
        class PlainInner(BaseModel):
            secret: str

        class Outer(BaseModel, Anonymizer):
            inner: PlainInner = Field(json_schema_extra={"anonymize": True})

        o = Outer(inner=PlainInner(secret="password123"))
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = o.model_dump_anonymized()
            assert result["inner"]["secret"] == "password123"
            assert len(w) == 1
            assert "non-Anonymizer BaseModel" in str(w[0].message)

    def test_json_non_serializable(self):
        import json
        from datetime import datetime

        class Data(BaseModel, Anonymizer):
            created: datetime

        d = Data(created=datetime(2024, 1, 1))
        result = json.loads(d.model_dump_json_anonymized())
        assert "2024" in result["created"]

    def test_unknown_anonymize_config(self):
        class User(BaseModel, Anonymizer):
            email: str = Field(json_schema_extra={"anonymize": "unknown_strategy"})

        u = User(email="test@mail.com")
        result = u.model_dump_anonymized()
        assert result["email"] == "test@mail.com"


class TestAnonymizerWithoutBaseModel:
    def test_anonymizer_without_basemodel(self):
        with pytest.raises(TypeError):

            class Bad(Anonymizer):
                pass


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

    def test_decorator_preserves_frozen(self):
        @Anonymize(email=True)
        class User(BaseModel):
            email: str
            name: str = Field(default="test", frozen=True)

        assert User.model_fields["name"].frozen is True

    def test_decorator_preserves_exclude(self):
        @Anonymize(email=True)
        class User(BaseModel):
            email: str
            internal: str = Field(default="x", exclude=True)

        assert User.model_fields["internal"].exclude is True

    def test_decorator_preserves_repr(self):
        @Anonymize(email=True)
        class User(BaseModel):
            email: str
            hidden: str = Field(default="x", repr=False)

        assert User.model_fields["hidden"].repr is False

    def test_decorator_preserves_metadata(self):
        @Anonymize(email=True)
        class User(BaseModel):
            email: str
            age: int = Field(ge=0, le=150)

        assert User.model_fields["age"].metadata is not None or True
        user = User(email="test@mail.com", age=25)
        result = user.model_dump_anonymized()
        assert result["age"] == 25

    def test_decorator_transitive_inheritance(self):
        class AnonymizingBase(BaseModel, Anonymizer):
            pass

        @Anonymize(email=True)
        class User(AnonymizingBase):
            email: str

        user = User(email="test@mail.com")
        result = user.model_dump_anonymized()
        assert result["email"] == "t***@***.com"


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

    def test_async_with_async_mask(self):
        async def async_mask(value: str) -> str:
            return "ASYNC:" + value[:2] + "***"

        MaskRegistry.register("async_test", async_mask)

        class User(BaseModel, Anonymizer):
            name: str = Field(json_schema_extra={"anonymize": "async_test"})

        user = User(name="Ivan Petrov")
        result = asyncio.run(user.model_dump_anonymized_async())
        assert result["name"] == "ASYNC:Iv***"
        MaskRegistry.unregister("async_test")

    def test_sync_mask_in_async(self):
        class User(BaseModel, Anonymizer):
            email: str = Field(json_schema_extra={"anonymize": True})

        user = User(email="test@mail.com")
        result = asyncio.run(user.model_dump_anonymized_async())
        assert result["email"] == "t***@***.com"

    def test_async_mask_in_sync_raises(self):
        async def async_mask(value: str) -> str:
            return "async"

        MaskRegistry.register("async_only", async_mask)

        class User(BaseModel, Anonymizer):
            name: str = Field(json_schema_extra={"anonymize": "async_only"})

        user = User(name="test")
        with pytest.raises(TypeError, match="async"):
            user.model_dump_anonymized()
        MaskRegistry.unregister("async_only")

    def test_async_nested_model(self):
        async def async_mask(value: str) -> str:
            return "A:" + value[:1] + "***"

        MaskRegistry.register("async_nested", async_mask)

        class Inner(BaseModel, Anonymizer):
            secret: str = Field(json_schema_extra={"anonymize": "async_nested"})

        class Outer(BaseModel, Anonymizer):
            inner: Inner

        o = Outer(inner=Inner(secret="password"))
        result = asyncio.run(o.model_dump_anonymized_async())
        assert result["inner"]["secret"] == "A:p***"
        MaskRegistry.unregister("async_nested")

    def test_async_list_of_models(self):
        async def async_mask(value: str) -> str:
            return "A:" + value[:1] + "***"

        MaskRegistry.register("async_list", async_mask)

        class Item(BaseModel, Anonymizer):
            value: str = Field(json_schema_extra={"anonymize": "async_list"})

        class Container(BaseModel, Anonymizer):
            items: list[Item]

        c = Container(items=[Item(value="secret1"), Item(value="secret2")])
        result = asyncio.run(c.model_dump_anonymized_async())
        assert result["items"][0]["value"] == "A:s***"
        assert result["items"][1]["value"] == "A:s***"
        MaskRegistry.unregister("async_list")

    def test_async_plain_fields(self):
        class User(BaseModel, Anonymizer):
            name: str
            age: int

        user = User(name="ivan", age=25)
        result = asyncio.run(user.model_dump_anonymized_async())
        assert result == {"name": "ivan", "age": 25}

    def test_async_nested_anonymizer_model(self):
        async def async_mask(value: str) -> str:
            return "A:" + value[:1] + "***"

        MaskRegistry.register("async_nested_am", async_mask)

        class Inner(BaseModel, Anonymizer):
            secret: str = Field(json_schema_extra={"anonymize": "async_nested_am"})

        class Outer(BaseModel, Anonymizer):
            inner: Inner = Field(json_schema_extra={"anonymize": "async_nested_am"})

        o = Outer(inner=Inner(secret="password"))
        result = asyncio.run(o.model_dump_anonymized_async())
        assert isinstance(result["inner"], dict)
        MaskRegistry.unregister("async_nested_am")

    def test_async_non_anonymizer_basemodel(self):
        class PlainInner(BaseModel):
            data: str

        class Outer(BaseModel, Anonymizer):
            inner: PlainInner = Field(json_schema_extra={"anonymize": True})

        o = Outer(inner=PlainInner(data="value"))
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = asyncio.run(o.model_dump_anonymized_async())
            assert result["inner"]["data"] == "value"
            assert len(w) == 1

    def test_async_list_with_anonymize_config(self):
        class User(BaseModel, Anonymizer):
            emails: list[str] = Field(json_schema_extra={"anonymize": True})

        u = User(emails=["a@b.com", "c@d.com"])
        result = asyncio.run(u.model_dump_anonymized_async())
        assert result["emails"][0] != "a@b.com"

    def test_async_non_string_with_config(self):
        class Data(BaseModel, Anonymizer):
            count: int = Field(json_schema_extra={"anonymize": True})

        d = Data(count=42)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = asyncio.run(d.model_dump_anonymized_async())
            assert result["count"] == 42
            assert len(w) == 1

    def test_async_unknown_config(self):
        class User(BaseModel, Anonymizer):
            name: str = Field(json_schema_extra={"anonymize": "nonexistent"})

        u = User(name="test")
        result = asyncio.run(u.model_dump_anonymized_async())
        assert result["name"] == "test"

    def test_async_list_plain_items(self):
        class Container(BaseModel, Anonymizer):
            items: list[str]

        c = Container(items=["a", "b", "c"])
        result = asyncio.run(c.model_dump_anonymized_async())
        assert result["items"] == ["a", "b", "c"]

    def test_async_nested_list(self):
        class Container(BaseModel, Anonymizer):
            data: list[list[str]]

        c = Container(data=[["a", "b"], ["c", "d"]])
        result = asyncio.run(c.model_dump_anonymized_async())
        assert result["data"] == [["a", "b"], ["c", "d"]]

    def test_async_list_with_non_anonymizer_basemodel(self):
        class PlainItem(BaseModel):
            data: str

        class Container(BaseModel, Anonymizer):
            items: list[PlainItem]

        c = Container(items=[PlainItem(data="v1"), PlainItem(data="v2")])
        result = asyncio.run(c.model_dump_anonymized_async())
        assert result["items"][0]["data"] == "v1"
        assert result["items"][1]["data"] == "v2"

    def test_async_dict_field(self):
        class Data(BaseModel, Anonymizer):
            metadata: dict

        d = Data(metadata={"key": "value"})
        result = asyncio.run(d.model_dump_anonymized_async())
        assert result["metadata"] == {"key": "value"}


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

    def test_formatter_does_not_mutate_record(self):
        class User(BaseModel, Anonymizer):
            email: str = Field(json_schema_extra={"anonymize": True})

        formatter = AnonymizedFormatter("%(message)s")
        user = User(email="original@mail.com")
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="%s", args=(user,), exc_info=None,
        )
        original_args = record.args
        formatter.format(record)
        assert record.args == original_args


class TestVersion:
    def test_version_exists(self):
        from pydantic_anonymizer import __version__
        assert __version__ is not None
        assert "." in __version__
