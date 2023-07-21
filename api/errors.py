from aiohttp import ClientResponse

RESPONSE_DATA = dict | list | str


class HTTPException(Exception):

    def __init__(self, response: ClientResponse, data: RESPONSE_DATA):
        self.response = response
        self.data = data

        self.method = response.method
        self.url = response.url
        self.code = response.status
        self.reason = response.reason

    def __str__(self):
        return f'{self.method.upper()} {self.url} responded with {self.code} {self.reason}'


class BadRequest(HTTPException):

    pass


class Unauthorized(HTTPException):

    pass


class Forbidden(HTTPException):

    pass


class NotFound(HTTPException):

    pass


class TooManyRequests(HTTPException):

    pass


class ServerError(HTTPException):

    pass
