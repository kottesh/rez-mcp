import hmac
from hashlib import sha256
from config import REZConfig
import time
import base64
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def base64_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def base64_decode(s: str) -> bytes:
    missing = 4 - (len(s) % 4) % 4
    s += "=" * missing

    return base64.urlsafe_b64decode(s)


def generate_token(data: str, expiry_in: int = 600) -> str:
    expiry = int(time.time()) + expiry_in

    payload = f"{data}|{expiry}"

    signature = hmac.new(REZConfig.SECRET_KEY, payload.encode(), sha256).digest()

    return f"{base64_encode(payload.encode())}.{base64_encode(signature)}"


def verify_token(token: str) -> tuple[str | None, bool]:
    try:
        parts = token.split(".", 1)

        if len(parts) != 2:
            logger.info(f"Invalid token | {token}")
            return None, False

        payload, expected_sig = base64_decode(parts[0]), base64_decode(parts[1])

        computed_sig = hmac.new(REZConfig.SECRET_KEY, payload, sha256).digest()

        if not hmac.compare_digest(computed_sig, expected_sig):
            logger.info(f"Token verification failed | {token} |Signature mismatch.")
            return None, False

        data, expiry = payload.decode().rsplit("|", 1)

        if int(time.time()) > int(expiry):
            logger.info(
                f"Token expired | {token} | Expired at: {datetime.fromtimestamp(expiry)}"
            )
            return None, False

        return data, True

    except Exception as e:
        logger.error(f"Failed to verify the token: {str(e)}")
        return None, False
