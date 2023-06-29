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
            logging.fatal('Invalid Mongo connection URI provided. Please check your config.py file is correct.')
            raise SystemExit()

        self.database: AsyncIOMotorDatabase = self.client.database
        self.metadata: AsyncIOMotorCollection = self.database.metadata
        self.modlogs: AsyncIOMotorCollection = self.database.modlogs

        self._session = None

    async def __aenter__(self):
        try:
            self._session: AsyncIOMotorClientSession = await self.client.start_session()
        except ServerSelectionTimeoutError:
            logging.fatal('Failed to connect to MongoDB. Please check your config.py file is correct.')
            raise SystemExit()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        await self._session.end_session()
        return False

    async def get_metadata(self):
        data = await self.metadata.find_one({}, session=self._session)

        if data is None:
            _none = None
            _list = []
            default = {
                'gen_channel': _none,
                'log_channel': _none,
                'trivia_channel': _none,
                'suggest_channel': _none,

                'trivia_bl': _list,
                'suggest_bl': _list,

                'domain_bl': _none,
                'domain_wl': _none,

                'admin_role': _none,
                'bot_role': _none,
                'senior_role': _none,
                'hmod_role': _none,
                'smod_role': _none,
                'rmod_role': _none,
                'tmod_role': _none,
                'helper_role': _none,

                'trivia_role': _none,
                'active_role': _none,
                
                'ignored_roles': _list,
                'ignored_channels': _list,

                'activity': _none
            }
            await self.metadata.insert_one(default, session=self._session)
            return default

        return data
