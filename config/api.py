from ninja import NinjaAPI

from invoices.api import router as invoices_router
from providers.api import router as providers_router

api = NinjaAPI(title="Challenge RP API")


@api.get("/health")
def health(request):
    return {"status": "ok"}


api.add_router("", invoices_router)
api.add_router("", providers_router)
