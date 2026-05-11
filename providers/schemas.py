from ninja import Schema


class ProviderOut(Schema):
    country_code: str
    provider_code: str
    name: str
    timeout_seconds: float
    max_retries: int
