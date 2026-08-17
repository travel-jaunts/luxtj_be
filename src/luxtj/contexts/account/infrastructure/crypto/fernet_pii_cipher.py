from cryptography.fernet import Fernet, MultiFernet


class FernetPiiCipher:
    """Encrypts with the first key; decrypts with any key so rotation stays possible."""

    def __init__(self, keys: list[str]) -> None:
        if not keys:
            raise ValueError("at least one PII encryption key is required")
        self._fernet = MultiFernet([Fernet(key) for key in keys])

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode()).decode()
