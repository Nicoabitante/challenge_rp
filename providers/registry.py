from functools import lru_cache

from django.conf import settings
from django.utils.module_loading import import_string

from providers.base import BillingProvider
from providers.exceptions import UnsupportedCountryError


@lru_cache
def list_providers() -> tuple[BillingProvider, ...]:
    providers = []
    for dotted_path in settings.BILLING_PROVIDERS:
        provider_class = import_string(dotted_path)
        providers.append(provider_class())
    return tuple(providers)


def get_provider_for_country(country_code: str) -> BillingProvider:
    normalized_country = country_code.upper()
    for provider in list_providers():
        if provider.country_code == normalized_country:
            return provider
    raise UnsupportedCountryError(f"Unsupported country_code: {country_code}")


def clear_provider_cache() -> None:
    list_providers.cache_clear()
