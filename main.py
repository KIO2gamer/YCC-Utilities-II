import os
import asyncio
import logging
from typing import Union

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    from discord.ext import commands
    from discord import (
        __version__ as __discord__,
        Intents,
        Message,
        HTTPException,
        LoginFailure,
        PrivilegedIntentsRequired,
        User,
        Member
    )

    # Local imports
    from resources import config
    from core.mongo import MongoDBClient
    from core.context import CustomContext

except ModuleNotFoundError as unknown_import:
    logging.fatal(f'Missing required dependencies - {unknown_import}.')
    raise SystemExit()


class CustomBot(commands.Bot):

    def __init__(self):

        intents = Intents.all()
        intents.typing = intents.presences = False

        super().__init__(
            command_prefix=config.PREFIX,
            intents=intents,
            owner_ids=config.OWNERS,
            help_command=None,
            case_insensitive=True,
            max_messages=5000
        )
        self.guild_id = config.GUILD_ID
        self.mongo_db = self.guild = None
        self.metadata = {}
        self.bans = []

    async def member_clearance(self, member: Union[User, Member]) -> int:
        if member.id in self.owner_ids or member == self.guild.owner:
            return 9
        elif isinstance(member, User):
            try:
                member = self.guild.get_member(member.id) or await self.guild.fetch_member(member.id)
            except HTTPException:
                return 0

        roles = [role.id for role in member.roles]
        data = self.metadata

        return \
            8 if data.get('admin_role') in roles else \
            7 if data.get('bot_role') in roles else \
            6 if data.get('senior_role') in roles else \
            5 if data.get('hmod_role') in roles else \
            4 if data.get('smod_role') in roles else \
            3 if data.get('rmod_role') in roles else \
            2 if data.get('tmod_role') in roles else \
            1 if data.get('helper_role') in roles else 0

    async def on_message(self, message: Message) -> None:
        if message.guild is None or message.guild.id != self.guild_id:
            return

        ctx = await self.get_context(message, cls=CustomContext)
        await self.invoke(ctx)

    async def setup_hook(self) -> None:
        logging.info(f'Logging in as {self.user.name} (ID: {self.user.id})...')

        try:
            owners = [await self.fetch_user(_id) for _id in self.owner_ids]
            self.guild = await self.fetch_guild(self.guild_id)
            logging.info(f'Owner(s): {", ".join([owner.name for owner in owners])}')
            logging.info(f'Guild: {self.guild.name}')

        except HTTPException:
            logging.fatal('Invalid IDs passed. Please check your config.py file is correct.')
            raise SystemExit()

        logging.info('Fetching guild bans, this may take a while...')
        self.bans = [entry.user.id async for entry in self.guild.bans(limit=None)]

        self.metadata = await self.mongo_db.get_metadata()

    def run_bot(self) -> None:

        async def _run_bot():
            async with self, MongoDBClient(self, config.MONGO) as self.mongo_db:
                for filename in os.listdir('./ext'):
                    if filename.endswith('.py'):
                        try:
                            await self.load_extension(f'ext.{filename[:-3]}')
                        except (commands.ExtensionFailed, commands.NoEntryPointError) as extension_error:
                            logging.error(f'Extension {filename} could not be loaded: {extension_error}')
                try:
                    await self.start(config.TOKEN)
                except LoginFailure:
                    logging.fatal('Invalid token passed.')
                except PrivilegedIntentsRequired:
                    logging.fatal('Intents are being requested that have not been enabled in the developer portal.')

        async def _cleanup():
            pass

        # noinspection PyUnresolvedReferences
        with asyncio.Runner() as runner:
            try:
                runner.run(_run_bot())
            except (KeyboardInterrupt, SystemExit):
                logging.info('Received signal to terminate bot and event loop.')
            finally:
                logging.info('Cleaning up tasks and connections...')
                runner.run(_cleanup())
                logging.info('Done. Have a nice day!')


if __name__ == '__main__':

    if __discord__ == '2.3.1':
        bot = CustomBot()
        bot.run_bot()

    else:
        logging.fatal('The incorrect version of discord.py has been installed.')
        logging.fatal('Current Version: {}'.format(__discord__))
        logging.fatal('Required: 2.3.1')
