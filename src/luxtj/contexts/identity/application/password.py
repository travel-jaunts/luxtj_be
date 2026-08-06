import hashlib
import hmac
import secrets


class PasswordHasher:
    """PBKDF2-SHA256 password hasher (stdlib, no extra dependency)."""

    ALGORITHM = "pbkdf2_sha256"
    ITERATIONS = 120_000

    def hash(self, password: str) -> str:
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            self.ITERATIONS,
        ).hex()
        return f"{self.ALGORITHM}${self.ITERATIONS}${salt}${digest}"

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            algorithm, iterations_s, salt, expected = password_hash.split("$", 3)
            if algorithm != self.ALGORITHM:
                return False
            iterations = int(iterations_s)
        except ValueError:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        ).hex()
        return hmac.compare_digest(digest, expected)


class TokenHasher:
    def hash(self, raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    def generate_raw_token(self) -> str:
        return secrets.token_urlsafe(32)
