# Account OTP Delivery

Production OTP requests require an active, complete Twilio or Telegram integration. If no approved provider is available, the request fails with a generic `503` response and no challenge is persisted.

A test sender is available only when `LTJBE_AUTH_OTP_ALLOW_TEST_SENDER=true` and `LTJBE_ENV` is `development` or `test`. The flag is ignored in every other environment.

Delivery is attempted before the challenge is persisted. A provider failure therefore leaves no challenge to redeem. Clients should retry the OTP request after the provider issue is resolved.

Provider-state warnings and failures are logged without phone numbers or OTP values. Provider credentials belong in the integration registry and must be managed as secrets.
