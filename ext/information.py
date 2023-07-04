from time import time
from datetime import timedelta

from discord.ext import commands
from discord.utils import format_dt
from discord import (
    User,
    Color,
    Embed
)

from main import CustomBot
from core.context import CustomContext


class InformationCommands(commands.Cog):

    _afk_users = []

    def __init__(self, bot: CustomBot):
        self.bot = bot

    @commands.command(
        name='ping',
        aliases=['latency'],
        description='View the bot\'s current latency.',
        extras={'requirement': 1}
    )
    async def ping(self, ctx: CustomContext):
        await self.bot.good_embed(ctx, f'*Pong! Latency: `{round(self.bot.latency, 3)}s`*.')

    @commands.command(
        name='uptime',
        aliases=['ut'],
        description='View the bot\'s current uptime.',
        extras={'requirement': 1}
    )
    async def uptime(self, ctx: CustomContext):
        await self.bot.good_embed(ctx, f'*Current uptime: `{timedelta(seconds=round(time() - self.bot.start_time))}`.*')

    @commands.command(
        name='avatar',
        aliases=['av'],
        description='View a user\'s global avatar.',
        extras={'requirement': 1}
    )
    async def avatar(self, ctx: CustomContext, *, user: User = None):
        user = user or ctx.author
        avatar_embed = Embed(colour=Color.blue(), description=f'**{user.mention}\'s avatar:**')
        avatar_embed.set_image(url=user.avatar if user.avatar else user.default_avatar)
        await ctx.send(embed=avatar_embed)

    @commands.command(
        name='userinfo',
        aliases=['whois', 'ui'],
        description='View information about a user/member.',
        extras={'requirement': 1}
    )
    async def userinfo(self, ctx: CustomContext, *, user: User = None):
        bool_map = {True: '**Yes**', False: '**No**'}
        _none = '**`None`**'

        user = user or ctx.author
        member = await self.bot.user_to_member(user)

        user_info_embed = Embed(colour=Color.blue(), title=user.name, description=user.mention)
        user_info_embed.set_author(name='User Info', icon_url=self.bot.user.avatar.url)
        user_info_embed.set_thumbnail(url=user.avatar if user.avatar else user.default_avatar)
        user_info_embed.set_footer(text=f'User ID: {user.id}')
        user_info_embed.add_field(name='In Guild:', value=bool_map[bool(member)])
        user_info_embed.add_field(name='Banned:', value=bool_map[user.id in self.bot.bans])
        user_info_embed.add_field(name='Muted:', value=_none if not member else bool_map[member.is_timed_out()])

        user_info_embed.add_field(
            name=f'Roles: [{len(member.roles) - 1 if member else 0}]',
            value=_none if not member or len(member.roles) <= 1 else
            ' '.join([role.mention for role in member.roles[1:]]), inline=False)

        user_info_embed.add_field(name='Created At:', value=f'<t:{round(user.created_at.timestamp())}:F>')
        user_info_embed.add_field(name='Joined Guild On:', value=format_dt(member.joined_at, 'F') if member else _none)

        perm_level = f'`Level {await self.bot.member_clearance(user)}`' if member else '`None`'
        user_info_embed.add_field(name='Guild Permission Level:', value=perm_level, inline=False)

        await ctx.send(embed=user_info_embed)


async def setup(bot: CustomBot):
    await bot.add_cog(InformationCommands(bot))
