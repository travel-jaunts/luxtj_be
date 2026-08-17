# PII encryption

Passport numbers are the only PII encrypted at rest today. They are stored as Fernet
ciphertext in `account_profile_travellers.passport_number_encrypted`, alongside a plaintext
`passport_last4` so listing travellers never requires decryption. The API only ever returns
`passportMasked` (`******1234`).

## Configuration

`LTJBE_PII_ENCRYPTION_KEYS` is a comma-separated list of Fernet keys. The **first** key
encrypts; all keys can decrypt.

```powershell
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

If the variable is unset a development key is used. `validate_pii_encryption_configuration()`
rejects that default when `LTJBE_ENV` is `production`.

## Rotation

1. Generate a new key and prepend it: `LTJBE_PII_ENCRYPTION_KEYS=<new>,<old>`.
2. Deploy. New writes use `<new>`; existing ciphertext still decrypts with `<old>`.
3. Re-save the traveller rows to re-encrypt them, then drop `<old>`.
