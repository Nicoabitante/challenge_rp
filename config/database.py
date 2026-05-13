from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlparse


def database_config_from_url(database_url: str | None, *, base_dir: Path) -> dict:
    if not database_url:
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": base_dir / "db.sqlite3",
        }

    parsed = urlparse(database_url)
    scheme = parsed.scheme.removesuffix("+psycopg")

    if scheme in {"postgres", "postgresql"}:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(parsed.path.lstrip("/")),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or ""),
            "OPTIONS": dict(parse_qsl(parsed.query)),
        }

    if scheme == "sqlite":
        database_path = unquote(parsed.path)
        if parsed.netloc:
            database_path = f"/{parsed.netloc}{database_path}"
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": database_path,
        }

    raise ValueError(f"Unsupported DATABASE_URL scheme: {parsed.scheme}")
