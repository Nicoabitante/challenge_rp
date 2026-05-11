from ninja import NinjaAPI

api = NinjaAPI(title="Challenge RP API")


@api.get("/health")
def health(request):
    return {"status": "ok"}
