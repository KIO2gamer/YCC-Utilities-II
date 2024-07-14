import logging
from time import time
from typing import Literal, AsyncIterator

from certifi import where
from pymongo import ReturnDocument, DESCENDING
from pymongo.errors import (
    ConfigurationError,
    ServerSelectionTimeoutError
)
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorClientSession
)

from core.modlog import ModLogEntry
from core.errors import ModLogNotFound
from core.metadata import MetaData


class MongoDBClient:

    DEFAULT_METADATA = {
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

    COMMAND_TYPES = Literal['faq', 'custom']
    ROLE_TYPES = Literal['persistent', 'custom']

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

        self.__session: AsyncIOMotorClientSession | None = None

    async def __aenter__(self):
        try:
            self.__session = await self.client.start_session()
        except ServerSelectionTimeoutError:
            logging.fatal('Failed to connect to MongoDB. Please check your config.py file is correct.')
            raise SystemExit()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.__session.end_session()

    async def get_metadata(self) -> MetaData:
        data = await self.database.metadata.find_one({}, session=self.__session)

        if data is None:
            data = self.DEFAULT_METADATA
            await self.database.metadata.insert_one(data, session=self.__session)

        return MetaData(self.bot, **data)

    async def update_metadata(self, **kwargs) -> None:
        data = await self.database.metadata.find_one_and_update(
            {},
            {'$set': kwargs},
            return_document=ReturnDocument.AFTER,
            session=self.__session
        )
        # Edit `CustomBot.metadata` in-place rather than returning a new version
        self.bot.metadata = MetaData(self.bot, **data)

    async def new_modlog_id(self) -> int:
        modlog = await self.database.modlogs.find_one(sort=[('case_id', DESCENDING)], session=self.__session)
        return modlog.get('case_id') + 1 if modlog else 1

    async def insert_modlog(self, **kwargs) -> ModLogEntry:
        await self.database.modlogs.insert_one(kwargs, session=self.__session)
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

        data = await self.database.modlogs.find_one_and_update(
            search_dict,
            {'$set': update_dict},
            return_document=ReturnDocument.AFTER,
            session=self.__session
        )

        if data is None:
            raise ModLogNotFound()

        logging.info(f'Updated existing modlog entry - Case ID: {data.get("case_id")} - Updated: {update_dict}')

        return ModLogEntry(self.bot, **data)

    async def search_modlog(self, **kwargs) -> list[ModLogEntry]:
        data = self.database.modlogs.find(kwargs, session=self.__session)
        modlogs = [ModLogEntry(self.bot, **entry) async for entry in data]

        if not modlogs:
            raise ModLogNotFound()

        return modlogs

    async def dump_msg_stats(self, entries: list[dict]):
        if not entries:
            return
        await self.database.msg_stats.insert_many(entries, session=self.__session)

    def get_msg_stats(self, lookback: int | float) -> AsyncIterator[dict]:
        _m = time() - lookback
        return self.database.msg_stats.find({'created': {'$gt': _m}}, session=self.__session)

    async def dump_vc_stats(self, entries: list[dict]):
        if not entries:
            return
        await self.database.vc_stats.insert_many(entries, session=self.__session)

    def get_vc_stats(self, lookback: int | float) -> AsyncIterator[dict]:
        _m = time() - lookback
        return self.database.vc_stats.find({'joined': {'$gt': _m}}, session=self.__session)

    async def purge_old_stats(self, lookback: int | float) -> int:
        _m = time() - lookback
        result_1 = await self.database.msg_stats.delete_many({'created': {'$lt': _m}}, session=self.__session)
        result_2 = await self.database.vc_stats.delete_many({'joined': {'$lt': _m}}, session=self.__session)
        return result_1.deleted_count + result_2.deleted_count

    async def fetch_commands(self, command_type: COMMAND_TYPES) -> list[dict]:
        return [cmd async for cmd in self.database[f'{command_type}_commands'].find({}, session=self.__session)]

    async def insert_command(self, command_type: COMMAND_TYPES, **kwargs) -> dict:
        await self.database[f'{command_type}_commands'].insert_one(kwargs, session=self.__session)
        return kwargs

    async def delete_command(self, command_type: COMMAND_TYPES, **kwargs) -> bool:
        result = await self.database[f'{command_type}_commands'].delete_one(kwargs, session=self.__session)
        return bool(result.deleted_count)

    async def fetch_roles(self, role_type: ROLE_TYPES) -> list[dict]:
        return [entry async for entry in self.database[f'{role_type}_roles'].find({}, session=self.__session)]

    async def insert_role(self, role_type: ROLE_TYPES, **kwargs) -> dict:
        await self.database[f'{role_type}_roles'].insert_one(kwargs, session=self.__session)
        return kwargs

    async def delete_role(self, role_type: ROLE_TYPES, **kwargs) -> bool:
        result = await self.database[f'{role_type}_roles'].delete_one(kwargs, session=self.__session)
        return bool(result.deleted_count)

    def get_views(self) -> AsyncIterator[dict]:
        return self.database.views.find({}, session=self.__session)

    async def add_view(self, **kwargs) -> dict:
        await self.database.views.insert_one(kwargs, session=self.__session)
        return kwargs
