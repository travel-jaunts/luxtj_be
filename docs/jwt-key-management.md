# JWT Key Management

Account and identity/admin tokens use separate key rings, issuers, and audiences. Account tokens use the `luxtj-account-auth` issuer and `luxtj-account` audience by default; identity tokens use `luxtj-identity-auth` and `luxtj`.

Each token includes a `kid`, `jti`, `iss`, `aud`, token type, subject UUID, issued-at time, and expiry. Decoders allow only configured algorithms and key IDs, validate issuer and audience, reject future-issued tokens beyond the configured clock skew, and never accept a key supplied by a token.

Key rings are supplied as JSON mappings from key ID to secret. Set the active key ID to issue with a new key while retaining the previous key in the ring during the overlap period. After all tokens signed by the old key have expired, remove the old key. For a compromised key, remove it immediately, revoke affected refresh sessions, and require re-authentication.

Production startup rejects missing or development-default keys and rejects shared account/identity keys, issuers, or audiences. Secrets belong in the deployment secret manager and rotation ownership belongs to the platform operations team.
