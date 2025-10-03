from dotenv import load_dotenv
import os

load_dotenv()


def _get_env(var: str, default=None):
    value = os.getenv(var, default)
    if not value:
        raise Exception(f"Environment variable '{var}' is not set")
    return value


class REZConfig:
    def __init__(self):
        self.cit_base_url = _get_env("CIT_BASE_URL")
        self.rez_base_url = _get_env("REZ_BASE_URL")


rez_config = REZConfig()
