class ProviderError(Exception):
    pass


class UnsupportedCountryError(ProviderError):
    pass


class ProviderTransientError(ProviderError):
    pass


class ProviderTimeoutError(ProviderTransientError):
    pass


class ProviderPermanentError(ProviderError):
    pass
