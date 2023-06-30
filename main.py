import os
import asyncio
import logging
from datetime import timedelta
from typing import Union, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    from discord.ui import View
    from discord.ext import commands
    from discord.abc import Messageable
    from discord.utils import MISSING
    from discord import (
        __version__ as __discord__,
        Intents,
        Message,
        HTTPException,
        LoginFailure,
        PrivilegedIntentsRequired,
        User,
        Member,
        Embed,
        Color
    )

    # Local imports
    from resources import config
    from core.mongo import MongoDBClient
    from core.errors import DurationError
    from core.embed import EmbedField, CustomEmbed
    from core.context import CustomContext, enforce_clearance

except ModuleNotFoundError as unknown_import:
    logging.fatal(f'Missing required dependencies - {unknown_import}.')
    raise SystemExit()


class CustomBot(commands.Bot):

    _duration_mapping = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800, 'y': 31536000}

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

        self.add_check(enforce_clearance, call_once=True)

    def convert_duration(self, duration: str) -> timedelta:
        try:
            return timedelta(seconds=int(duration[:-1]) * self._duration_mapping[duration[-1:].lower()])
        except (KeyError, ValueError):
            raise DurationError()

    @staticmethod
    def _new_embed(**kwargs) -> CustomEmbed:
        return CustomEmbed(
            title=kwargs.get('title'),
            description=kwargs.get('description'),
            color=kwargs.get('color', Color.blue()),
            timestamp=kwargs.get('timestamp')
        )

    def fields_to_embeds(self, fields: list[EmbedField], **kwargs) -> list[CustomEmbed]:
        embed_list = [self._new_embed(**kwargs)]

        for field in fields:
            if len(embed_list[-1].fields) > kwargs.get('field_limit', 5) - 1:
                embed_list.append(self._new_embed(**kwargs))
            embed_list[-1].append_field(field)

        for embed in embed_list:
            embed.set_author(name=kwargs.get('author_name'), icon_url=kwargs.get('author_icon'))
            embed.set_footer(text=f'Page {embed_list.index(embed) + 1} of {len(embed_list)}')

        return embed_list

    @staticmethod
    async def basic_embed(destination: Messageable, message: str, color: Color, view: View = MISSING) -> Message:
        embed = Embed(description=message, color=color)
        return await destination.send(embed=embed, view=view)

    async def neutral_embed(self, destination: Messageable, message: str, view: View = MISSING) -> Message:
        return await self.basic_embed(destination, message, Color.blue(), view=view)

    async def good_embed(self, destination: Messageable, message: str, view: View = MISSING) -> Message:
        return await self.basic_embed(destination, message, Color.green(), view=view)

    async def bad_embed(self, destination: Messageable, message: str, view: View = MISSING) -> Message:
        return await self.basic_embed(destination, message, Color.red(), view=view)

    async def user_to_member(self, user: User) -> Optional[Member]:
        try:
            return self.guild.get_member(user.id) or await self.guild.fetch_member(user.id)
        except HTTPException:
            return

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

    async def check_target_member(self, member: Union[User, Member]) -> None:
        if await self.member_clearance(member) > 0:
            raise commands.CheckFailure('The target of this moderation is protected.')

    async def on_command_error(self, ctx: CustomContext, error: commands.CommandError) -> None:
        reset_cooldown = True

        if isinstance(error, (commands.CheckFailure, commands.CommandNotFound)):
            return

        elif isinstance(error, commands.CommandOnCooldown):
            message = f'Wait `{round(error.retry_after)}s` before doing that again.'
            reset_cooldown = False

        elif isinstance(error, commands.BotMissingPermissions):
            message = f'Bot missing required permissions: `{", ".join(error.missing_permissions).replace("_", " ")}`.'

        elif isinstance(error, (commands.UserNotFound, commands.MemberNotFound,
                                commands.ChannelNotFound, commands.RoleNotFound)):
            message = f'{error.__class__.__name__[:-8]} not found.'

        elif isinstance(error, commands.BadArgument):
            message = 'Incorrect argument type(s).'

        elif isinstance(error, commands.CommandInvokeError):
            message = str(error.original)

        else:
            message = f'An unexpected error occurred: {error}'

        if reset_cooldown is True:
            ctx.command.reset_cooldown(ctx)

        await self.bad_embed(ctx, f'❌ {message}')

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
