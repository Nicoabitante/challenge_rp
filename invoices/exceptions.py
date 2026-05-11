class InvoiceError(Exception):
    pass


class IdempotencyConflict(InvoiceError):
    pass
