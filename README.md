# challenge_rp

Django, Django Ninja, pytest, Poetry y Docker.

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

- `GET /api/health`
- `/api/docs`

## Tests

```bash
poetry run pytest
```

## Docker

```bash
docker compose up --build
```
