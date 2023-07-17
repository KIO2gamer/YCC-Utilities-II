from typing import Literal
from urllib.parse import urlparse

from discord.ext import commands
from discord.abc import GuildChannel
from discord import (
    ActivityType,
    Activity,
    User,
    Role
)

from main import CustomBot
from core.context import CustomContext


class ConfigurationCommands(commands.Cog):

    CHANNEL_TYPES = Literal['appeal', 'trivia', 'suggest', 'general', 'logging']
    ROLE_TYPES = Literal['admin', 'bot', 'senior', 'hmod', 'smod', 'rmod', 'tmod', 'helper', 'trivia', 'active']
    ROLE_TYPES_MAP = {'bot': 'Bot Admin', 'senior': 'Senior Staff', 'hmod': 'Head Moderator',
                      'smod': 'Senior Moderator', 'rmod': 'Moderator', 'tmod': 'Trainee Moderator'}
    BLACKLIST_TYPES = Literal['suggest', 'trivia', 'appeal']

    def __init__(self, bot: CustomBot):
        self.bot = bot

    @commands.command(
        name='config-channel',
        aliases=[],
        description='Sets a text channel as the bot\'s `appeal`, `trivia`, `suggest`, `general` or `logging` channel.',
        extras={'requirement': 9}
    )
    async def config_channel(self, ctx: CustomContext, channel_type: CHANNEL_TYPES, *, channel: GuildChannel):
        kwarg = {f'{channel_type}_channel': channel.id}
        await self.bot.mongo_db.update_metadata(**kwarg)
        msg = f'*Set {channel.mention} as the new `{channel_type}` channel.*'
        await self.bot.good_embed(ctx, msg)

    @commands.command(
        name='config-role',
        aliases=[],
        description='Sets a role as the one of the bot\'s recognised roles (staff roles, active role etc).',
        extras={'requirement': 9}
    )
    async def config_role(self, ctx: CustomContext, role_type: ROLE_TYPES, *, role: Role):
        kwarg = {f'{role_type}_role': role.id}
        await self.bot.mongo_db.update_metadata(**kwarg)
        msg = f'*Set {role.mention} as the new `{self.ROLE_TYPES_MAP.get(role_type, role_type.capitalize())}` role.*'
        await self.bot.good_embed(ctx, msg)

    @commands.command(
        name='wldomain',
        aliases=[],
        description='Toggles the whitelisting of a URL domain.',
        extras={'requirement': 4}
    )
    async def wldomain(self, ctx: CustomContext, domain: str):
        wl = [_ for _ in self.bot.metadata.domain_wl]
        if domain in wl:
            wl.remove(domain)
            msg = f'*Removed `{domain}` from the domain whitelist.*'
        else:
            wl.append(domain)
            msg = f'*Added `{domain}` to the domain whitelist.*'
        await self.bot.mongo_db.update_metadata(domain_wl=wl)
        await self.bot.good_embed(ctx, msg)

    @commands.command(
        name='bldomain',
        aliases=[],
        description='Toggles the blacklisting of a URL domain.',
        extras={'requirement': 4}
    )
    async def bldomain(self, ctx: CustomContext, domain: str):
        bl = [_ for _ in self.bot.metadata.domain_bl]
        if domain in bl:
            bl.remove(domain)
            msg = f'*Removed `{domain}` from the domain blacklist.*'
        else:
            bl.append(domain)
            msg = f'*Added `{domain}` to the domain blacklist.*'
        await self.bot.mongo_db.update_metadata(domain_bl=bl)
        await self.bot.good_embed(ctx, msg)

    @commands.command(
        name='blacklist',
        aliases=[],
        description='Blacklists a user from one of the bot\'s features (`suggest`, `trivia` or `appeal`).',
        extras={'requirement': 4}
    )
    async def blacklist(self, ctx: CustomContext, blacklist_type: BLACKLIST_TYPES, user: User):
        bl = [_ for _ in self.bot.metadata.__getattribute__(f'{blacklist_type}_bl')]
        if user.id in bl:
            bl.remove(user.id)
            msg = f'*Removed {user.mention} from the `{blacklist_type}` blacklist.*'
        else:
            await self.bot.check_target_member(user)
            bl.append(user.id)
            msg = f'*Added {user.mention} to the `{blacklist_type}` blacklist.*'
        await self.bot.mongo_db.update_metadata(**{f'{blacklist_type}_bl': bl})
        await self.bot.good_embed(ctx, msg)

    @commands.command(
        name='set-status',
        aliases=[],
        description='Edits the bot\'s status to `Listening to <status>`.',
        extras={'requirement': 9}
    )
    async def set_status(self, ctx: CustomContext, *, status: str):
        await self.bot.change_presence(activity=Activity(type=ActivityType.listening, name=status))
        await self.bot.mongo_db.update_metadata(activity=status)
        await self.bot.good_embed(ctx, f'*Set status as `{status}`!*')

    @commands.command(
        name='set-welcome',
        aliases=[],
        description='Edits the welcome message sent when a member joins. Use `<member>` to mention the member.',
        extras={'requirement': 9}
    )
    async def set_welcome(self, ctx: CustomContext, *, message: str):
        await self.bot.mongo_db.update_metadata(welcome_msg=message)
        await self.bot.good_embed(ctx, f'*Set welcome message as `{message}`!*')

    @commands.command(
        name='set-appeal-url',
        aliases=[],
        description='Edits the ban appeal URL that gets sent to banned users. Use `off` to disable this feature.',
        extras={'requirement': 9}
    )
    async def set_appeal_url(self, ctx: CustomContext, *, url: str):
        if url == 'off':
            url = None
        else:
            try:
                result = urlparse(url)
                valid = all([result.scheme, result.netloc])
            except ValueError:
                valid = False
            if valid is False:
                raise Exception('Invalid URL provided.')
        await self.bot.mongo_db.update_metadata(appeal_url=url)
        await self.bot.good_embed(ctx, f'*Set appeal URL as `{url}`!*')


async def setup(bot: CustomBot):
    await bot.add_cog(ConfigurationCommands(bot))
