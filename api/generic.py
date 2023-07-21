import logging
import asyncio

from aiohttp import (
    ClientSession,
    ClientResponse,
    ClientError
)

from api.errors import (
    RESPONSE_DATA,
    HTTPException,
    BadRequest,
    Unauthorized,
    Forbidden,
    NotFound,
    TooManyRequests,
    ServerError
)


async def json_or_text(response: ClientResponse) -> RESPONSE_DATA:
    try:
        return await response.json()
    except ClientError:
        return await response.text()


class AsyncRequestsClient:

    def __init__(self):
        self.__session: ClientSession | None = None

    async def __aenter__(self):
        self.__session = ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.__session.close()

    async def request(self, method: str, url: str, retries: int = -1, **kwargs) -> RESPONSE_DATA:
        if not self.__session:
            raise ClientError('`AsyncRequestsClient.request` must be used in an asynchronous context manager.')

        async with self.__session.request(method, url, **kwargs) as response:
            logging.info(f'({response.status}) {method.upper() + "      "[:6 - len(method)]} {url}')

            data = await json_or_text(response)

            if 200 <= response.status < 300:
                return data

            elif response.status == 429 and retries < 6:
                retries += 1
                retry_after = 2 ** retries

                logging.info(f'We are being rate limited. Retrying in {retry_after} seconds...')
                await asyncio.sleep(retry_after)

                return await self.request(method, url, retries=retries, **kwargs)

            elif response.status == 400:
                cls = BadRequest
            elif response.status == 401:
                cls = Unauthorized
            elif response.status == 403:
                cls = Forbidden
            elif response.status == 404:
                cls = NotFound
            elif response.status == 429:
                cls = TooManyRequests
            elif response.status >= 500:
                cls = ServerError
            else:
                cls = HTTPException

            raise cls(response, data)
