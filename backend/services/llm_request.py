from click import prompt
from dotenv import load_dotenv
import os
import requests

load_dotenv()

YC_API_KEY = os.getenv("YC_API_KEY")
YC_FOLDER_ID = os.getenv("YC_FOLDER_ID")

def ask_yagpt(system_prompt: str, user_text: str, temperature: float = 0.0) -> str:
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {YC_API_KEY}",
        "x-folder-id": YC_FOLDER_ID,
    }
    model_uri = f"gpt://{YC_FOLDER_ID}/yandexgpt/latest"
    payload = {
        "modelUri": model_uri,
        "completionOptions": {
            "stream": False,
            "temperature": temperature,
            "maxTokens": "1500"
        },
        "messages": [
            {
                "role": "system",
                "text": system_prompt
            },
            {
                "role": "user",
                "text": user_text
            }
        ]
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        raise Exception(f"Ошибка Yandex API ({response.status_code}): {response.text}")
    data = response.json()
    try:
        return data["result"]["alternatives"][0]["message"]["text"]
    except (KeyError, IndexError):
        raise Exception("YandexGPT вернул неожиданный формат ответа")

if __name__ == "__main__":
    prompt = """Сгенерируй финальный список из 120–150 профессиональных тегов для классификации онлайн-курсов.

ОБЛАСТИ ДЛЯ ОХВАТА:

Разработка (все популярные языки, архитектура, мобилки, фронт/бэк).

Данные и ИИ (Data Science, Analytics, ML, Big Data, SQL).

Инфраструктура (DevOps, Cloud, Linux, Cybersecurity).

Дизайн (UI/UX, Graphic Design, Figma, 3D).

Бизнес и Менеджмент (Project/Product Management, Agile, Soft Skills, Finance).

Маркетинг (SEO, SMM, Digital Marketing).

ТРЕБОВАНИЯ К ТЕГАМ:

Только на английском языке.

Теги должны быть "плоскими" (одно-два слова, например "Python" или "System Design").

Избегай слишком узких тем (вместо "Python 3.10" пиши "Python").

Обязательно включи популярные инструменты (Docker, React, Excel, Jira).

ФОРМАТ ВЫВОДА (КРИТИЧЕСКИ ВАЖНО):
Выдай результат ОДНИМ сплошным списком через запятую. НЕ используй нумерацию, НЕ разбивай на категории заголовками, НЕ пиши никакого вводного текста. Только слова через запятую."""
    sys_p = """Ты — эксперт по анализу данных и проектированию образовательных программ (Curriculum Architect). Твоя задача — создать профессиональную, стандартизированную таксономию навыков для платформы онлайн-обучения. Ты используешь общепринятые в индустрии названия технологий и профессий на английском языке. Ты лаконичен и строго следуешь заданному формату вывода."""
    res = ask_yagpt(system_prompt=sys_p, user_text=prompt, temperature=0.5)
    print(res)