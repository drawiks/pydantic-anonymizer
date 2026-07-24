<div align="center">
    <h1>🔒 pydantic-anonymizer</h1>
    <a href="https://pypi.org/project/pydantic-anonymizer/">
        <img alt="PyPI version" src="https://img.shields.io/pypi/v/pydantic-anonymizer?color=blue">
    </a>
    <img height="20" alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9+-blue">
    <img height="20" alt="License MIT" src="https://img.shields.io/badge/license-MIT-green">
    <img height="20" alt="Status" src="https://img.shields.io/badge/status-stable-brightgreen">
    <p><strong>mask sensitive data in Pydantic models</strong></p>
    <p><a href="README.md">Русский</a></p>
</div>

---

```
                 ,--.                  ,--.  ,--.       
 ,---.,--. ,--.,-|  | ,--,--.,--,--, ,-'  '-.`--' ,---. 
| .-. |\  '  /' .-. |' ,-.  ||      \'-.  .-',--.| .--' 
| '-' ' \   ' \ `-' |\ '-'  ||  ||  |  |  |  |  |\ `--. 
|  |-'.-'  /   `---'  `--`--'`--''--'  `--'  `--' `---' 
`--'  `---'                                             
                                                                            
                                                  ,--.                      
 ,--,--.,--,--,  ,---. ,--,--, ,--. ,--.,--,--,--.`--',-----. ,---. ,--.--. 
' ,-.  ||      \| .-. ||      \ \  '  / |        |,--.`-.  / | .-. :|  .--' 
\ '-'  ||  ||  |' '-' '|  ||  |  \   '  |  |  |  ||  | /  `-.\   --.|  |    
 `--`--'`--''--' `---' `--''--'.-'  /   `--`--`--'`--'`-----' `----'`--'    
                               `---'                                        
```

## **📦 installation**

```bash
pip install pydantic-anonymizer
```

---

## **📑 quick start**

```python
from pydantic import BaseModel, Field
from pydantic_anonymizer import Anonymizer

class UserProfile(BaseModel, Anonymizer):
    username: str
    email: str = Field(json_schema_extra={"anonymize": True})
    card_number: str = Field(json_schema_extra={"anonymize": "card"})
    phone_number: str = Field(json_schema_extra={"anonymize": "phone"})

user = UserProfile(
    username="ivan_dev",
    email="ivan@mail.com",
    card_number="4242111122223333",
    phone_number="+380500223785"
)

print(user.model_dump())
# {'username': 'ivan_dev', 'email': 'ivan@mail.com', 'card_number': '4242111122223333', 'phone_number': '+380500223785'}

print(user.model_dump_anonymized())
# {'username': 'ivan_dev', 'email': 'i***@***.com', 'card_number': '4242-****-****-3333', 'phone_number': '+380 (***) ***-**-85'}
```

---

## **🧩 features**

- 🔐 **automatic masking** - configure via `json_schema_extra` in model fields
- 📧 **generic masking** - partial mask for emails and text (`i***@***.com`)
- 💳 **card masking** - format `4242-****-****-3333`
- 📱 **phone masking** - correct country code parsing with [phonenumbers](https://github.com/daviddryden/python-phonenumbers)
- 🏗️ **nested models** - recursive processing of nested Pydantic models
- 📋 **lists** - support for `list[Model]` with masking of each element
- 🛠️ **custom strategies** - your own masking functions via `MaskRegistry`
- ✅ **reliable** - 27 tests covering all scenarios
- 🪶 **minimal dependencies** - only `pydantic>=2.0` and `phonenumbers>=8.13`

---

## **📖 usage**

### basic usage

```python
from pydantic import BaseModel, Field
from pydantic_anonymizer import Anonymizer

class User(BaseModel, Anonymizer):
    name: str
    email: str = Field(json_schema_extra={"anonymize": True})

user = User(name="ivan", email="ivan@mail.com")

# original data
user.model_dump()  # {'name': 'ivan', 'email': 'ivan@mail.com'}

# masked data
user.model_dump_anonymized()  # {'name': 'ivan', 'email': 'i***@***.com'}

# JSON string
user.model_dump_json_anonymized()  # '{"name": "ivan", "email": "i***@***.com"}'
```

### nested models

```python
from pydantic import BaseModel, Field
from pydantic_anonymizer import Anonymizer

class Address(BaseModel, Anonymizer):
    city: str
    street: str = Field(json_schema_extra={"anonymize": True})

class UserProfile(BaseModel, Anonymizer):
    name: str
    address: Address

user = UserProfile(
    name="ivan",
    address=Address(city="Moscow", street="Lenina 1")
)

result = user.model_dump_anonymized()
# {'name': 'ivan', 'address': {'city': 'Moscow', 'street': 'L***a 1'}}
```

### lists of models

```python
from pydantic import BaseModel, Field
from pydantic_anonymizer import Anonymizer

class Card(BaseModel, Anonymizer):
    number: str = Field(json_schema_extra={"anonymize": "card"})

class Wallet(BaseModel, Anonymizer):
    cards: list[Card]

wallet = Wallet(cards=[
    Card(number="4242111122223333"),
    Card(number="5555666677778888")
])

result = wallet.model_dump_anonymized()
# {'cards': [{'number': '4242-****-****-3333'}, {'number': '5555-****-****-8888'}]}
```

### custom strategies

```python
from pydantic import BaseModel, Field
from pydantic_anonymizer import Anonymizer, MaskRegistry

# register your own masking function
def mask_ssn(value: str) -> str:
    return "***-**-" + value[-4:]

MaskRegistry.register("ssn", mask_ssn)

class Person(BaseModel, Anonymizer):
    ssn: str = Field(json_schema_extra={"anonymize": "ssn"})

person = Person(ssn="123-45-6789")
person.model_dump_anonymized()  # {'ssn': '***-**-6789'}
```

---

## **🎭 built-in strategies**

| Strategy | Field | Input | Output |
|----------|-------|-------|--------|
| `True` (generic) | email | `ivan@mail.com` | `i***@***.com` |
| `"card"` | card number | `4242111122223333` | `4242-****-****-3333` |
| `"phone"` | phone | `+380500223785` | `+380 (***) ***-**-85` |

### country code support

phone masking works correctly with any country codes:

| Country | Code | Example |
|---------|------|---------|
| Ukraine | +380 | `+380500223785` → `+380 (***) ***-**-85` |
| USA | +1 | `+14155552671` → `+1 (***) ***-**-71` |
| UK | +44 | `+447911123456` → `+44 (***) ***-**-56` |
| Russia | +7 | `+79161234567` → `+7 (***) ***-**-67` |
| Germany | +49 | `+4915112345678` → `+49 (***) ***-**-78` |
| China | +86 | `+8613812345678` → `+86 (***) ***-**-78` |

---

## **📝 examples**

### FastAPI logging

```python
from fastapi import FastAPI
from pydantic import BaseModel, Field
from pydantic_anonymizer import Anonymizer

app = FastAPI()

class UserCreate(BaseModel, Anonymizer):
    username: str
    email: str = Field(json_schema_extra={"anonymize": True})
    card_number: str = Field(json_schema_extra={"anonymize": "card"})

@app.post("/users")
def create_user(user: UserCreate):
    # log with masking
    print(user.model_dump_anonymized())
    # {'username': 'admin', 'email': 'a***@***.com', 'card_number': '4242-****-****-3333'}

    # original data for processing
    return user.model_dump()
```

### safe logging

```python
import logging
from pydantic import BaseModel, Field
from pydantic_anonymizer import Anonymizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Payment(BaseModel, Anonymizer):
    card_number: str = Field(json_schema_extra={"anonymize": "card"})
    amount: float

def process_payment(payment: Payment):
    # safe to log - card number is masked
    logger.info("payment: %s", payment.model_dump_anonymized())

    # work with original data
    charge_card(payment.card_number, payment.amount)
```

---

## **📜 license**

[MIT](https://github.com/drawiks/pydantic-anonymizer/blob/main/LICENSE)
