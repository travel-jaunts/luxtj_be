# Account Refresh Sessions

Account refresh tokens are single-use credentials. Each token contains a unique `jti` and is stored only as a SHA-256 hash in `account_refresh_sessions`.

## Refresh

Send the refresh token to `POST /v1/auth/user/refresh`. A successful response contains a new access token and a new refresh token. The submitted refresh token is revoked and cannot be used again.

Clients must replace the stored refresh token after every successful refresh. They must treat a refresh failure as a requirement to authenticate again; a reused or tampered token can revoke all refresh sessions for the account.

## Logout

Send the current refresh token to `POST /v1/auth/user/logout` to revoke that session. Use the authenticated `POST /v1/auth/user/logout-all` operation to revoke every refresh session for the account.

## Storage and cleanup

Raw refresh tokens are never persisted. Expired revoked sessions are retained for the configured incident and reuse-detection window, then removed by the application cleanup task. Active sessions are not removed by cleanup.

Signing secrets must be stored in the deployment secret manager. When refresh-token reuse is detected, clients should discard all locally stored account tokens and require a fresh OTP authentication.
