# Provider mocks

Mock HTTP servers used by Docker Compose to simulate external billing providers.

The same image is used for AR and BR. Runtime behavior is configured with env vars:

- `PROVIDER_COUNTRY`: `AR` or `BR`.
- `PROVIDER_CODE`: provider identifier returned by `/health`.
- `MOCK_MODE`: `success`, `transient`, `permanent`, or `timeout`.
- `RESPONSE_DELAY_SECONDS`: optional artificial delay.

Endpoints:

- `GET /health`
- `POST /invoices`
