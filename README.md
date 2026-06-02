# EEMA

EEMA - MVP рекомендательной системы для онлайн-курсов. Проект помогает пользователю подобрать курсы и примерную траекторию обучения по профилю навыков, текстовому запросу и реакции на уже показанные курсы.

Основной фокус каталога - IT-компетенции и смежные цифровые навыки: программирование, аналитика данных, backend/frontend, DevOps, базы данных, дизайн, тестирование и другие направления.

## Что умеет система

- Регистрация и вход через Supabase Auth.
- Подтверждение почты через self-hosted Supabase Auth и SMTP.
- Онбординг: пользователь выбирает навыки, уровни владения и может описать опыт своими словами.
- Сохранение профиля пользователя в Supabase.
- Каталог курсов с поиском, фильтрацией по сложности и сортировкой.
- Рекомендации по текстовому запросу пользователя.
- Лайки курсов для персонализации выдачи.
- RAG-поиск по embeddings курсов.
- Понимание намерения: сопоставление пользовательского запроса с каноничными тегами.
- Персонализация рекомендаций на основе релевантных лайков.
- Обогащение выдачи похожими курсами из кластеров.
- Построение простых roadmap-подсказок через цепи Маркова.
- Пайплайн данных для загрузки и нормализации Stepik-курсов.
- Осторожный подход к ML-заполнению сложности курсов: модель не включается, пока не проходит независимую проверку качества.

## Краткое руководство пользователя

1. Откройте frontend-приложение.
2. Зарегистрируйтесь по email и паролю.
3. Подтвердите почту по ссылке из письма.
4. Войдите в аккаунт.
5. Пройдите онбординг:
   - выберите знакомые технологии;
   - укажите уровень;
   - при желании опишите навыки текстом.
6. Перейдите к рекомендациям.
7. Введите запрос, например:
   - `хочу изучить SQL и PostgreSQL`;
   - `backend на Python`;
   - `React для frontend`;
   - `кибербезопасность и Linux`.
8. Откройте подходящий курс или поставьте лайк, чтобы система лучше понимала интересы.
9. В каталоге можно искать курсы вручную и фильтровать их по сложности.

## Интерфейс

В проекте есть светлая и темная тема. Основные экраны:

- регистрация и вход;
- онбординг навыков;
- рекомендации;
- каталог курсов;
- карточки курсов с лайками.


## Архитектура

```text
Frontend React
    |
    | HTTP API, Bearer JWT
    v
FastAPI backend
    |
    | Supabase Python client
    v
Self-hosted Supabase
    |
    +-- Auth: email/password, email confirmation, refresh sessions
    +-- Database: courses, users, likes, embeddings, metadata
    +-- RPC: vector search and cluster neighbor search

External APIs:
    +-- Stepik API: source courses
    +-- Yandex API: embeddings and LLM parsing
```

### Frontend

Frontend лежит в `frontend/` и собран на Create React App.

Основные страницы:

- `/auth` - вход;
- `/register` и `/registration` - регистрация;
- `/` - онбординг, закрыт `ProtectedRoute`;
- `/home` - рекомендации, закрыты `ProtectedRoute`;
- `/catalog` - каталог курсов.

Ключевые файлы:

- `frontend/src/app/router.tsx` - маршруты приложения.
- `frontend/src/shared/api/utils/axios.ts` - общий `$api` клиент с Bearer token и refresh-flow.
- `frontend/src/shared/config/config.ts` - API base URL через `REACT_APP_API_BASE_URL`.
- `frontend/src/pages/onboarding/` - онбординг.
- `frontend/src/pages/recommendations/` - главный экран рекомендаций.
- `frontend/src/pages/catalog/` - каталог.
- `frontend/src/shared/like-button/` - like/unlike.
- `frontend/src/app/styles/colors.css` - палитра и тема.

### Backend

Backend лежит в `backend/` и использует FastAPI.

Публичные API:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/users/profile`
- `GET /api/users/profile`
- `POST /api/users/parse-skills`
- `GET /api/courses/catalog`
- `GET /api/courses/recommend/baseline`
- `POST /api/courses/recommend/advanced`
- `POST /api/courses/{course_id}/like`
- `DELETE /api/courses/{course_id}/like`

Ключевые файлы:

- `backend/app/main.py` - FastAPI-приложение и CORS.
- `backend/app/core/config.py` - env helpers, CORS origins, feature flag тестового токена.
- `backend/app/core/database.py` - Supabase client.
- `backend/app/core/security.py` - JWT validation.
- `backend/app/api/router_auth.py` - регистрация, вход, refresh.
- `backend/app/api/router_user.py` - профиль, LLM parsing, тестовый токен только по feature flag.
- `backend/app/api/router_courses.py` - каталог, лайки, baseline и advanced рекомендации.
- `backend/services/` - эмбеддинги, анализ запроса, персонализация.

### Рекомендательный контур

Основной endpoint:

```http
POST /api/courses/recommend/advanced
```

Упрощенный поток:

1. Пользователь отправляет текстовый запрос.
2. Backend строит embedding запроса через Yandex API.
3. Supabase RPC `match_courses` возвращает RAG-кандидатов.
4. Анализ намерения определяет каноничные теги запроса.
5. Профиль пользователя и лайки превращаются в профиль интереса.
6. Фильтр отсекает слишком простые/неподходящие курсы по навыкам пользователя.
7. Модуль персонализации переупорядочивает кандидатов.
8. Дополнительно добавляются:
   - похожие курсы из кластера;
   - roadmap-подсказки на базе цепей Маркова.

В ответе сохраняется стабильная структура:

- `strategy`
- `search_query`
- `main_results`
- `ml_enrichment.anchor_course_title`
- `ml_enrichment.cluster_neighbors`
- `ml_enrichment.markov_roadmap`
- `ml_enrichment.user_profile`

### Data pipeline

Pipeline лежит в `data_pipeline/`.

Основные задачи:

- загрузка курсов Stepik;
- загрузка и нормализация тегов;
- запись курсов в Supabase;
- обновление эмбеддингов;
- построение таксономии;
- пересчет кластеров;
- построение матрицы Маркова;
- аудит качества данных.

Основные команды:

```bash
python3 -m data_pipeline.pipeline ingest --pages 5
python3 -m data_pipeline.pipeline ingest --pages 1 --skip-embed
python3 -m data_pipeline.pipeline taxonomy-cache
python3 -m data_pipeline.pipeline cluster
python3 -m data_pipeline.pipeline markov
python3 -m data_pipeline.pipeline audit
python3 -m data_pipeline.pipeline all --pages 5
```

### ML и сложность курсов

В проекте есть экспериментальный контур заполнения `difficulty`, но production-позиция консервативная:

- Сложность со степика всегда приоритетнее.
- Модель не должна массово заполнять сложность, пока не прошла контроль качесства.
- Регрессионные и threshold-эксперименты не активированы.
- Выборочный подход для `easy`/`normal` возможен только после независимимой оценки.


## Стек

Frontend:

- React 19
- TypeScript
- React Router
- Axios
- Lucide React
- Create React App
- Vercel

Backend:

- Python
- FastAPI
- Uvicorn
- Supabase Python client
- PyJWT
- python-dotenv
- Requests

Data/ML:

- Supabase PostgreSQL
- Supabase Auth
- Supabase RPC/vector search
- Stepik API
- Yandex embeddings
- Yandex LLM for skill parsing
- scikit-learn experiments for difficulty
- TF-IDF + LogisticRegression candidates
- clustering and Markov scripts

Infrastructure:

- Vercel frontend project
- Vercel backend Python function project
- Self-hosted Supabase
- SMTP for email confirmation

## Env

Backend:

```env
SUPABASE_URL=
SUPABASE_KEY=
JWT_SECRET=
YC_API_KEY=
YC_FOLDER_ID=
YC_URL=https://llm.api.cloud.yandex.net/foundationModels/v1/textEmbedding
CORS_ORIGINS=https://eema-web.vercel.app,http://localhost:3000,http://127.0.0.1:3000
ENABLE_TEST_TOKEN_ENDPOINT=false
```

Frontend:

```env
REACT_APP_API_BASE_URL=https://eema-api.vercel.app
```

Self-hosted Supabase Auth, пример:

```env
ENABLE_EMAIL_SIGNUP=true
ENABLE_EMAIL_AUTOCONFIRM=false
ENABLE_ANONYMOUS_USERS=false
SITE_URL=https://eema-web.vercel.app
ADDITIONAL_REDIRECT_URLS=https://eema-web.vercel.app,http://localhost:3000
SMTP_ADMIN_EMAIL=eema@domain.ru
SMTP_HOST=smtp.ru
SMTP_PORT=465
SMTP_USER=eema@domain.ru
SMTP_PASS=
SMTP_SENDER_NAME=eema
```


## Локальный запуск

Backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm ci
cp .env.example .env
npm start
```

Проверки:

```bash
python3 -m pytest -q
cd frontend
npm run build
```

Актуальный результат локальной проверки:

```text
63 passed
Compiled successfully
```


## Безопасность

- Пароли не хранятся в EEMA backend.
- Регистрация и вход делегированы Supabase Auth.
- Пароль передается по HTTPS в Auth-сервис, где Supabase отвечает за безопасное хранение и хеширование.
- Самодельное хеширование на frontend не используется: наивный hash в браузере становится эквивалентом пароля и не защищает от XSS.
- JWT проверяется backend-ом через `JWT_SECRET`.
- Публичный тестовый токен отключен по умолчанию через `ENABLE_TEST_TOKEN_ENDPOINT=false`.
- В публичных course responses не должны попадать `raw_tags`, `normalized_tags`, `tag_meta`, `domain`, `embedding`, `cluster_id`.

## Известные ограничения

- Качество рекомендаций сильнее там, где область покрыта каноничной таксономией.
- UX/UI, QA, mobile, Kotlin, Unity/gamedev и сети требуют расширения таксономии.
- `recommend/baseline` остается простым профильным рекомендателем.
- Автоматическое заполнение сложности курсов не включено.
- Pipeline/ML не рассчитаны на постоянный запуск в Vercel.
- Лайк курса может иметь сетевую задержку, это нормально для текущего MVP.


