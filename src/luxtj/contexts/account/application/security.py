import hashlib
import hmac
import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class OtpHashResult:
    otp_hash: str
    otp_salt: str


class OtpSecurityService:
    def __init__(self, *, pepper: str, otp_length: int = 6) -> None:
        self._pepper = pepper
        self._otp_length = otp_length

    def generate_otp(self) -> str:
        max_value = (10**self._otp_length) - 1
        return f"{secrets.randbelow(max_value + 1):0{self._otp_length}d}"

    def hash_otp(self, otp: str) -> OtpHashResult:
        salt = secrets.token_hex(16)
        digest = hashlib.sha256(f"{salt}:{otp}:{self._pepper}".encode()).hexdigest()
        return OtpHashResult(otp_hash=digest, otp_salt=salt)

    def verify_otp(self, *, otp: str, otp_hash: str, otp_salt: str) -> bool:
        digest = hashlib.sha256(f"{otp_salt}:{otp}:{self._pepper}".encode()).hexdigest()
        return hmac.compare_digest(digest, otp_hash)
