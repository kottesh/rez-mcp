import httpx
import logging
from config import rez_config

logger = logging.getLogger(__name__)


async def post(api_url: str, payload: dict) -> dict:
    async with httpx.AsyncClient(
        timeout=30,
        base_url=rez_config.cit_base_url,
        verify=False,
        follow_redirects=False,
    ) as client:
        try:
            logger.info(f"Calling API at {api_url} with body {payload}")
            response = await client.post(api_url, data=payload)
            response.raise_for_status()
            return response.text

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code if e.response else "Unknown status"
            content = e.response.text if e.response else "Nothing"

            logger.error(f"HTTPError: ({status_code}) - {content}")
            raise Exception(f"API HTTPError: ({status_code}) : {content}") from e

        except Exception as e:
            logger.error(f"Error during API call: {str(e)}")
            raise Exception(f"Failed to call API {str(e)}") from e


async def call(api_url, params: dict | None = None):
    async with httpx.AsyncClient(
        timeout=30,
        base_url=rez_config.cit_base_url,
        verify=False,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0"
        },
    ) as client:
        try:
            logger.info(
                f"Calling API at {api_url} with params {params if params else 'Nothing'}"
            )
            response = await client.get(api_url, params=params)
            response.raise_for_status()
            return response.text

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code if e.response else "Unknown status"
            content = e.response.text if e.response else "Nothing"

            logger.error(f"HTTPError: ({status_code}) - {content}")
            raise Exception(f"API HTTPError: ({status_code}) : {content}") from e

        except Exception as e:
            logger.error(f"Error during API call: {str(e)}")
            raise Exception(f"Failed to call API {str(e)}") from e
