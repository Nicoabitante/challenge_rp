import json
import socket
from dataclasses import dataclass
from json import JSONDecodeError
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from providers.exceptions import ProviderTimeoutError, ProviderTransientError


@dataclass(frozen=True)
class JsonResponse:
    status_code: int
    body: dict


def post_json(url: str, payload: dict, *, timeout_seconds: float) -> JsonResponse:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return JsonResponse(
                status_code=response.status,
                body=_load_json(response.read()),
            )
    except HTTPError as exc:
        return JsonResponse(
            status_code=exc.code,
            body=_load_json(exc.read()),
        )
    except TimeoutError as exc:
        raise ProviderTimeoutError(f"Provider request timed out after {timeout_seconds} seconds.") from exc
    except socket.timeout as exc:
        raise ProviderTimeoutError(f"Provider request timed out after {timeout_seconds} seconds.") from exc
    except URLError as exc:
        if isinstance(exc.reason, socket.timeout):
            raise ProviderTimeoutError(f"Provider request timed out after {timeout_seconds} seconds.") from exc
        raise ProviderTransientError(f"Provider request failed: {exc.reason}") from exc


def _load_json(raw_body: bytes) -> dict:
    if not raw_body:
        return {}
    try:
        return json.loads(raw_body.decode("utf-8"))
    except JSONDecodeError as exc:
        raise ProviderTransientError("Provider returned an invalid JSON response.") from exc
