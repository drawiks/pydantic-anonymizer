<div align="center">
    <h1>🔒 pydantic-anonymizer</h1>
    <a href="https://pypi.org/project/pydantic-anonymizer/">
        <img alt="PyPI version" src="https://img.shields.io/pypi/v/pydantic-anonymizer?color=blue">
    </a>
    <img height="20" alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9+-blue">
    <img height="20" alt="License MIT" src="https://img.shields.io/badge/license-MIT-green">
    <img height="20" alt="Status" src="https://img.shields.io/badge/status-stable-brightgreen">
    <p>
        <img height="20" alt="PyPI Downloads" src="https://static.pepy.tech/personalized-badge/pydantic-anonymizer?period=total&units=INTERNATIONAL_SYSTEM&left_color=GREY&right_color=RED&left_text=downloads">
    </p>
    <p><strong>anonymize sensitive data in pydantic models</strong></p>
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

## **📦 установка**

```bash
pip install pydantic-anonymizer
```

---

## **📑 быстрый старт**

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

## **🧩 возможности**

- 🔐 **автоматическая маскировка** - настройка через `json_schema_extra` в полях модели
- 📧 **generic маскирование** - частичная маска для email и текста (`i***@***.com`)
- 💳 **маскирование карт** - формат `4242-****-****-3333`
- 📱 **маскирование телефонов** - корректный парсинг кодов стран благодаря [phonenumbers](https://pypi.org/project/phonenumbers/)
- 🏗️ **вложенные модели** - рекурсивная обработка вложенных Pydantic моделей
- 📋 **списки** - поддержка `list[Model]` с маскированием каждого элемента
- 🛠️ **кастомные стратегии** - собственные функции маскирования через `MaskRegistry`
- ✅ **надёжность** - 27 тестов покрывают все сценарии
- 🪶 **минимум зависимостей** - только `pydantic>=2.0` и `phonenumbers>=8.13`

---

## **📖 использование**

### базовое использование

```python
from pydantic import BaseModel, Field
from pydantic_anonymizer import Anonymizer

class User(BaseModel, Anonymizer):
    name: str
    email: str = Field(json_schema_extra={"anonymize": True})

user = User(name="ivan", email="ivan@mail.com")

# оригинальные данные
user.model_dump()  # {'name': 'ivan', 'email': 'ivan@mail.com'}

# замаскированные данные
user.model_dump_anonymized()  # {'name': 'ivan', 'email': 'i***@***.com'}

# JSON строка
user.model_dump_json_anonymized()  # '{"name": "ivan", "email": "i***@***.com"}'
```

### вложенные модели

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

### списки моделей

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

### кастомные стратегии

```python
from pydantic import BaseModel, Field
from pydantic_anonymizer import Anonymizer, MaskRegistry

# регистрация自己的 функции маскирования
def mask_ssn(value: str) -> str:
    return "***-**-" + value[-4:]

MaskRegistry.register("ssn", mask_ssn)

class Person(BaseModel, Anonymizer):
    ssn: str = Field(json_schema_extra={"anonymize": "ssn"})

person = Person(ssn="123-45-6789")
person.model_dump_anonymized()  # {'ssn': '***-**-6789'}
```

---

## **🎭 встроенные стратегии**

| Стратегия | Поле | Вход | Выход |
|-----------|------|------|-------|
| `True` (generic) | email | `ivan@mail.com` | `i***@***.com` |
| `"card"` | номер карты | `4242111122223333` | `4242-****-****-3333` |
| `"phone"` | телефон | `+380500223785` | `+380 (***) ***-**-85` |

### поддержка кодов стран

маскирование телефонов корректно работает с любыми кодами стран:

| Страна | Код | Пример |
|--------|-----|--------|
| Украина | +380 | `+380500223785` → `+380 (***) ***-**-85` |
| США | +1 | `+14155552671` → `+1 (***) ***-**-71` |
| Великобритания | +44 | `+447911123456` → `+44 (***) ***-**-56` |
| Россия | +7 | `+79161234567` → `+7 (***) ***-**-67` |
| Германия | +49 | `+4915112345678` → `+49 (***) ***-**-78` |
| Китай | +86 | `+8613812345678` → `+86 (***) ***-**-78` |

---

## **📝 примеры**

### логирование в FastAPI

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
    # логируем с маскированием
    print(user.model_dump_anonymized())
    # {'username': 'admin', 'email': 'a***@***.com', 'card_number': '4242-****-****-3333'}

    # оригинальные данные для обработки
    return user.model_dump()
```

### безопасное логирование

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
    # безопасно логируем - номер карты замаскирован
    logger.info("платёж: %s", payment.model_dump_anonymized())

    # работаем с оригинальными данными
    charge_card(payment.card_number, payment.amount)
```

---

## **📜 лицензия**

[MIT](https://github.com/drawiks/pydantic-anonymizer/blob/main/LICENSE)
