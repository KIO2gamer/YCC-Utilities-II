from typing import Literal, get_args
from urllib.parse import urlparse

from discord.ext import commands
from discord.abc import GuildChannel
from discord import (
    Embed,
    Color,
    User,
    Role
)

from main import CustomBot
from core.context import CustomContext


class ConfigurationCommands(commands.Cog):

    CHANNEL_TYPES = Literal['appeal', 'trivia', 'suggest', 'general', 'logging']
    ROLE_TYPES = Literal['admin', 'bot', 'senior', 'hmod', 'smod', 'rmod', 'tmod', 'helper', 'trivia', 'active']
    ROLE_TYPES_MAP = {'bot': 'Bot Admin', 'senior': 'Senior Staff', 'hmod': 'Head Mod',
                      'smod': 'Senior Mod', 'rmod': 'Moderator', 'tmod': 'Trainee Mod'}
    BLACKLIST_TYPES = Literal['suggest', 'trivia', 'appeal']
    IGNORED_TYPES = Literal['event', 'auto_mod']

    def __init__(self, bot: CustomBot):
        self.bot = bot

    @commands.command(
        name='config',
        aliases=[],
        description='Displays the bot\'s current configuration settings.',
        extras={'requirement': 9}
    )
    async def config(self, ctx: CustomContext):
        async with ctx.typing():

            avatar = self.bot.user.avatar or self.bot.user.default_avatar
            config_embed = Embed(color=Color.blue(), title=self.bot.guild.name)
            config_embed.set_author(name='Configuration Settings', icon_url=avatar)
            config_embed.set_thumbnail(url=self.bot.guild.icon or avatar)
            config_embed.set_footer(text='Note: Some features pertaining to these settings are currently unavailable.')

            metadata = self.bot.metadata

            staff_roles = {self.ROLE_TYPES_MAP.get(name, name.capitalize()): await metadata.get_role(name)
                           for name in get_args(self.ROLE_TYPES)[:-2]}
            other_roles = {self.ROLE_TYPES_MAP.get(name, name.capitalize()): await metadata.get_role(name)
                           for name in get_args(self.ROLE_TYPES)[-2:]}
            channels = {name.capitalize(): await metadata.get_channel(name)
                        for name in get_args(self.CHANNEL_TYPES)}

            config_embed.add_field(
                name='Staff Roles:',
                value='\n'.join([f'> **`[{8 - list(staff_roles).index(r)}]` {r}:** '
                                 f'{staff_roles[r].mention if staff_roles[r] else "**`None`**"}' for r in staff_roles]),
                inline=False)
            config_embed.add_field(
                name='Other Roles:',
                value='\n'.join([f'> **{r}**: '
                                 f'{other_roles[r].mention if other_roles[r] else "**`None`**"}' for r in other_roles]),
                inline=False)
            config_embed.add_field(
                name='Channels:',
                value='\n'.join([f'> **{c}:** '
                                 f'{channels[c].mention if channels[c] else "**`None`**"}' for c in channels]),
                inline=False)

            config_embed.add_field(
                name='Ignored By Auto-Mod:',
                value=' '.join(([f'<#{c}>' for c in metadata.auto_mod_ignored_channels] +
                               [f'<@&{r}>' for r in metadata.auto_mod_ignored_roles]) or ['**`None`**']),
                inline=False)
            config_embed.add_field(
                name='Ignored By Logger:',
                value=' '.join(([f'<#{c}>' for c in metadata.event_ignored_channels] +
                               [f'<@&{r}>' for r in metadata.event_ignored_roles]) or ['**`None`**']),
                inline=False)

            config_embed.add_field(
                name='Miscellaneous:',
                value=f'> **Welcome Message: `{metadata.welcome_msg}`**\n'
                      f'> **Appeal URL: `{metadata.appeal_url}`**\n'
                      f'> **Bot Status: `{metadata.activity}`**',
                inline=False)

        await ctx.send(embed=config_embed)

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
        await self.bot.mongo_db.update_metadata(activity=status)
        await self.bot.init_status()
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

    @commands.command(
        name='config-ignored',
        aliases=[],
        description='Toggles a role/channel as being "ignored" by the auto-mod or event logger.',
        extras={'requirement': 9}
    )
    async def config_ignored(self, ctx: CustomContext, ignored_type: IGNORED_TYPES, target: GuildChannel | Role):
        str_type = 'roles' if isinstance(target, Role) else 'channels'
        id_list = [_ for _ in self.bot.metadata.__getattribute__(f'{ignored_type}_ignored_{str_type}')]
        if target.id in id_list:
            id_list.remove(target.id)
            msg = f'*Removed {target.mention} from the list of ignored `{ignored_type}` {str_type}.*'
        else:
            id_list.append(target.id)
            msg = f'*Added {target.mention} to the list of ignored `{ignored_type}` {str_type}.*'
        await self.bot.mongo_db.update_metadata(**{f'{ignored_type}_ignored_{str_type}': id_list})
        await self.bot.good_embed(ctx, msg)


async def setup(bot: CustomBot):
    await bot.add_cog(ConfigurationCommands(bot))
