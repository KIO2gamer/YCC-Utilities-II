import logging
from time import time

from certifi import where
from pymongo import ReturnDocument, DESCENDING
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

from core.modlog import ModLogEntry
from core.errors import ModLogNotFound
from core.metadata import MetaData


class MongoDBClient:

    def __init__(self, bot, connection_uri: str):
        self.bot = bot

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
        self.msg_stats: AsyncIOMotorCollection = self.database.msg_stats
        self.vc_stats: AsyncIOMotorCollection = self.database.vc_stats

        self._session = None

    async def __aenter__(self):
        try:
            self._session: AsyncIOMotorClientSession = await self.client.start_session()
        except ServerSelectionTimeoutError:
            logging.fatal('Failed to connect to MongoDB. Please check your config.py file is correct.')
            raise SystemExit()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._session.end_session()

    async def get_metadata(self) -> MetaData:
        data = await self.metadata.find_one({}, session=self._session)

        if data is None:
            default = {
                'appeal_channel': None,
                'trivia_channel': None,
                'suggest_channel': None,
                'general_channel': None,
                'logging_channel': None,

                'admin_role': None,
                'bot_role': None,
                'senior_role': None,
                'hmod_role': None,
                'smod_role': None,
                'rmod_role': None,
                'tmod_role': None,
                'helper_role': None,

                'trivia_role': None,
                'active_role': None,

                'domain_bl': [],
                'domain_wl': [],

                'appeal_bl': [],
                'trivia_bl': [],
                'suggest_bl': [],

                'event_ignored_roles': [],
                'event_ignored_channels': [],
                'auto_mod_ignored_roles': [],
                'auto_mod_ignored_channels': [],

                'activity': None,
                'welcome_msg': None,
                'appeal_url': None
            }
            await self.metadata.insert_one(default, session=self._session)
            data = default

        return MetaData(self.bot, **data)

    async def update_metadata(self, **kwargs) -> None:
        data = await self.metadata.find_one_and_update(
            {},
            {'$set': kwargs},
            return_document=ReturnDocument.AFTER,
            session=self._session
        )
        # Edit `CustomBot.metadata` in-place rather than returning a new version
        self.bot.metadata = MetaData(self.bot, **data)

    async def new_modlog_id(self) -> int:
        modlog = await self.modlogs.find_one(sort=[('case_id', DESCENDING)], session=self._session)
        return modlog.get('case_id') + 1 if modlog else 1

    async def insert_modlog(self, **kwargs) -> ModLogEntry:
        await self.modlogs.insert_one(kwargs, session=self._session)
        logging.info(f'New modlog entry created - Case ID: {kwargs.get("case_id")}')
        return ModLogEntry(self.bot, **kwargs)

    async def update_modlog(self, **kwargs) -> ModLogEntry:
        # Kwargs with leading underscores are our search parameters
        # Kwargs without leading underscores are our values to update
        search_dict = {}
        update_dict = {}

        for kwarg in kwargs:
            if kwarg.startswith('_'):
                search_dict[kwarg[1:]] = kwargs[kwarg]
            else:
                update_dict[kwarg] = kwargs[kwarg]

        data = await self.modlogs.find_one_and_update(
            search_dict,
            {'$set': update_dict},
            return_document=ReturnDocument.AFTER,
            session=self._session
        )

        if data is None:
            raise ModLogNotFound()

        logging.info(f'Updated existing modlog entry - Case ID: {data.get("case_id")} - Updated: {update_dict}')

        return ModLogEntry(self.bot, **data)

    async def search_modlog(self, **kwargs) -> list[ModLogEntry]:
        data = self.modlogs.find(kwargs, session=self._session)
        modlogs = [ModLogEntry(self.bot, **entry) async for entry in data]

        if not modlogs:
            raise ModLogNotFound()

        return modlogs

    async def dump_msg_stats(self, entries: list[dict]):
        if not entries:
            return
        await self.msg_stats.insert_many(entries, session=self._session)

    async def get_msg_stats(self, lookback: int | float, **kwargs) -> list[dict]:
        _m = time() - lookback
        return [entry async for entry in self.msg_stats.find({'created': {'$gt': _m}} | kwargs, session=self._session)]

    async def dump_vc_stats(self, entries: list[dict]):
        if not entries:
            return
        await self.vc_stats.insert_many(entries, session=self._session)

    async def get_vc_stats(self, lookback: int | float, **kwargs) -> list[dict]:
        _m = time() - lookback
        return [entry async for entry in self.vc_stats.find({'joined': {'$gt': _m}} | kwargs, session=self._session)]
