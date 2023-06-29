import logging

from certifi import where
from pymongo.errors import (
    ConfigurationError,
    ServerSelectionTimeoutError
)
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorCollection,
    AsyncIOMotorClientSession
)


class MongoDBClient:

    def __init__(self, connection_uri: str):
        try:
            self.client: AsyncIOMotorClient = AsyncIOMotorClient(
                connection_uri,
                tlsCAFile=where(),
                serverSelectionTimeoutMS=3000
            )

        except ConfigurationError:
            logging.fatal('Invalid Mongo connection URI provided.')
            raise SystemExit()

        self.database: AsyncIOMotorDatabase = self.client.database
        self.userdata: AsyncIOMotorCollection = self.database.userdata
        self.settings: AsyncIOMotorCollection = self.database.settings
        self._session = None

    async def __aenter__(self):
        try:
            self._session: AsyncIOMotorClientSession = await self.client.start_session()
        except ServerSelectionTimeoutError:
            logging.fatal('Failed to connect to MongoDB. Please check your credentials.')
            raise SystemExit()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        await self._session.end_session()
        return False
