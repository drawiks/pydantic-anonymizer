import re

import phonenumbers

__all__ = [
    "mask_email",
    "mask_card",
    "mask_ip",
    "mask_birthdate",
    "mask_name",
    "mask_iban",
    "mask_phone",
]


def mask_email(value: str) -> str:
    if not value:
        return value

    at_index = value.find("@")
    if at_index != -1:
        local = value[:at_index]
        domain = value[at_index + 1:]
        masked_local = local[0] + "***" if local else "***"
        dot_index = domain.rfind(".")
        if dot_index != -1:
            tld = domain[dot_index:]
            masked_domain = "***" + tld
        else:
            masked_domain = "***"
        return masked_local + "@" + masked_domain

    if len(value) <= 1:
        return "*"
    return value[0] + "***"


def mask_card(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if not digits:
        return "*"
    if len(digits) < 8:
        return "*" * len(digits)

    first4 = digits[:4]
    last4 = digits[-4:]
    if len(digits) - 8 > 0 and (len(digits) - 8) % 4 != 0:
        groups = (len(digits) - 8) // 4 + 1
        middle_masked = "-".join(["****"] * groups)
    else:
        middle_masked = "-".join(["****"] * max((len(digits) - 8) // 4, 1)) if len(digits) > 8 else ""

    parts = [first4]
    if middle_masked:
        parts.append(middle_masked)
    parts.append(last4)

    return "-".join(parts)


def mask_ip(value: str) -> str:
    parts = value.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.***.***"
    return "***.***.***.***"


def mask_birthdate(value: str) -> str:
    match = re.match(r"^(\d{1,2})(\D+)(\d{1,2})(\D+)(\d{4})$", value)
    if match:
        sep1, sep2 = match.group(2), match.group(4)
        return f"**{sep1}**{sep2}****"
    return re.sub(r"\d", "*", value)


def mask_name(value: str) -> str:
    parts = value.split()
    masked = []
    for part in parts:
        if len(part) <= 1:
            masked.append("*")
        else:
            masked.append(part[0] + "*" * (len(part) - 1))
    return " ".join(masked)


def mask_iban(value: str) -> str:
    clean = re.sub(r"\s", "", value)
    if len(clean) <= 8:
        return "*" * len(clean)
    return clean[:2] + "*" * (len(clean) - 6) + clean[-4:]


def mask_phone(value: str) -> str:
    try:
        num = phonenumbers.parse(value, None)
    except phonenumbers.NumberParseException:
        digits = re.sub(r"\D", "", value)
        return "*" * len(digits) if digits else value

    country_code = num.country_code
    national = str(num.national_number)

    if len(national) <= 2:
        masked_national = "*" * len(national)
    else:
        last_two = national[-2:]
        masked_national = f"(***) ***-**-{last_two}"

    return f"+{country_code} {masked_national}"
