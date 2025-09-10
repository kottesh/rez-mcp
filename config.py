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
        self.mcp_host = _get_env("MCP_HOST")
        self.mcp_port = int(_get_env("MCP_PORT"))
        self.cit_base_url = _get_env("CIT_BASE_URL")
        self.mcp_mode = _get_env("MCP_MODE", "http")
        self.mcp_auth_host = _get_env("MCP_AUTH_HOST")
        self.mcp_auth_port = int(_get_env("MCP_AUTH_PORT"))


rez_config = REZConfig()
