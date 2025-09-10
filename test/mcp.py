import asyncio
from fastmcp import Client
from tools.setup import get_profile

client = Client("http://0.0.0.0:5432/mcp")


# async def main():
#     async with client:
#         result = await client.call_tool("login", {})
#         print(result)


asyncio.run(get_profile(None))
