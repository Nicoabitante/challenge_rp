# challenge_rp

Django, Django Ninja, pytest, Poetry y Docker.

Architecture notes and technical decisions are documented in [docs/architecture.md](docs/architecture.md).

## Requirements

- Python 3.12+
- Poetry 2+
- Docker y Docker Compose

## Local installation

```bash
poetry install
poetry run python manage.py migrate
poetry run python manage.py runserver
```

The API is available at:

- `GET /health`
- `GET /providers`
- `POST /invoices`
- `GET /invoices/{invoice_id}`
- `/docs`

## Tests

```bash
poetry run pytest
```

## Docker

```bash
docker compose up --build
```

Docker Compose starts PostgreSQL, both external provider mocks, runs migrations, and then starts the Django app.

Provider mocks live in `provider_mocks/`. Compose starts one AR mock and one BR mock from the same image:

- `provider-ar-mock`: `POST /invoices`
- `provider-br-mock`: `POST /invoices`

Each mock supports `MOCK_MODE=success|transient|permanent|timeout` for manual failure testing.
