from ninja import Router

from providers.registry import list_providers
from providers.schemas import ProviderOut

router = Router(tags=["providers"])


@router.get("/providers", response=list[ProviderOut])
def get_providers(request):
    return [
        {
            "country_code": provider.country_code,
            "provider_code": provider.code,
            "name": provider.name,
            "timeout_seconds": provider.timeout_seconds,
            "max_retries": provider.max_retries,
        }
        for provider in list_providers()
    ]
