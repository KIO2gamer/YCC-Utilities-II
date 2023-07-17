from typing import Literal

from discord.ext import commands
from discord.abc import GuildChannel
from discord import Role

from main import CustomBot
from core.context import CustomContext


class ConfigurationCommands(commands.Cog):

    CHANNEL_TYPES = Literal['appeal', 'trivia', 'suggest', 'general', 'logging']
    ROLE_TYPES = Literal['admin', 'bot', 'senior', 'hmod', 'smod', 'rmod', 'tmod', 'helper', 'trivia', 'active']
    ROLE_TYPES_MAP = {'bot': 'Bot Admin', 'senior': 'Senior Staff', 'hmod': 'Head Moderator',
                      'smod': 'Senior Moderator', 'rmod': 'Moderator', 'tmod': 'Trainee Moderator'}

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


async def setup(bot: CustomBot):
    await bot.add_cog(ConfigurationCommands(bot))
