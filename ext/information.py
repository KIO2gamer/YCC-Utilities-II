from time import time
from asyncio import sleep
from datetime import timedelta

from discord.ext import commands
from discord.utils import format_dt
from discord import (
    HTTPException,
    Message,
    User,
    Color,
    Embed
)
from aiogoogletrans import LANGUAGES, Translator

from main import CustomBot
from core.context import CustomContext


class InformationCommands(commands.Cog):

    _reason = 'No reason provided.'
    _afk_users = {}
    _translator = Translator()

    def __init__(self, bot: CustomBot):
        self.bot = bot

    @commands.command(
        name='ping',
        aliases=['latency'],
        description='Shows the bot\'s current latency.',
        extras={'requirement': 1}
    )
    async def ping(self, ctx: CustomContext):
        await self.bot.good_embed(ctx, f'*Pong! Latency: `{round(self.bot.latency, 3)}s`*.')

    @commands.command(
        name='uptime',
        aliases=[],
        description='Shows the bot\'s current uptime.',
        extras={'requirement': 1}
    )
    async def uptime(self, ctx: CustomContext):
        await self.bot.good_embed(ctx, f'*Current uptime: `{timedelta(seconds=round(time() - self.bot.start_time))}`.*')

    @commands.command(
        name='avatar',
        aliases=['av'],
        description='Shows a user\'s global avatar.',
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
        description='Shows information about a user/member.',
        extras={'requirement': 1}
    )
    async def userinfo(self, ctx: CustomContext, *, user: User = None):
        bool_map = {True: '**Yes**', False: '**No**'}
        _none = '**`None`**'

        user = user or ctx.author
        member = await self.bot.user_to_member(user)

        user_info_embed = Embed(colour=Color.blue(), title=user.name, description=user.mention)
        user_info_embed.set_author(name='User Info', icon_url=self.bot.user.avatar)
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

    @commands.command(
        name='serverinfo',
        aliases=['guildinfo', 'si'],
        description='Shows information about the guild.',
        extras={'requirement': 1}
    )
    async def serverinfo(self, ctx: CustomContext):
        guild = self.bot.guild

        roles = [role.mention for role in guild.roles[1:]]
        roles.reverse()
        extra = ''
        if len(roles) > 15:
            roles = roles[:15]
            extra = f' **. . . (+ {len(guild.roles) - 16} more)**'

        guild_info_embed = Embed(colour=Color.blue(), title=guild.name)
        guild_info_embed.set_author(name='Server Info', icon_url=self.bot.user.avatar)
        guild_info_embed.set_thumbnail(url=guild.icon if guild.icon else self.bot.user.avatar)
        guild_info_embed.set_footer(text=f'Guild ID: {guild.id}')

        guild_info_embed.add_field(name='Owner:', value=guild.owner.mention if guild.owner else '**`None`**')
        guild_info_embed.add_field(name='Member Count:', value=f'**{len(guild.members)}**', inline=True)
        guild_info_embed.add_field(name='Bot Count:', value=f'**{len([m for m in guild.members if m.bot])}**')
        guild_info_embed.add_field(name='Text Channels:', value=f'**{len(guild.text_channels)}**')
        guild_info_embed.add_field(name='Voice Channels:', value=f'**{len(guild.voice_channels)}**')
        guild_info_embed.add_field(name='Category Channels:', value=f'**{len(guild.categories)}**')
        guild_info_embed.add_field(name=f'Roles: [{len(guild.roles) - 1}]', value=f'{" ".join(roles)}{extra}')
        guild_info_embed.add_field(name='Created At:', value=format_dt(guild.created_at), inline=False)

        await ctx.send(embed=guild_info_embed)

    @commands.command(
        name='translate',
        aliases=['t'],
        description='Translates the contents of a message. Default target language is `en` (English). '
                    '`<message>` can be a message link or just a string to translate. '
                    'Can also be invoked in reply to another message to translate the contents of that message.',
        extras={'requirement': 1}
    )
    async def translate(self, ctx: CustomContext, target: str = 'en', *, message: Message | str = None):
        if target.lower() not in LANGUAGES.keys():
            target = 'en'

        if ctx.message.reference:
            _message = await ctx.fetch_message(ctx.message.reference.message_id)
            content = _message.content
            link = f'**[Message Link]({_message.jump_url})**'
        elif isinstance(message, Message):
            content = message.content
            link = f'**[Message Link]({message.jump_url})**'
        else:
            content = message
            link = None

        translation = await self._translator.translate(content, dest=target.lower())

        translation_embed = Embed(colour=Color.blue(), title='Translation Results', description=link)
        translation_embed.add_field(name='Detected Language:', value=LANGUAGES[translation.src].capitalize())
        translation_embed.add_field(name='Target Language:', value=LANGUAGES[translation.dest].capitalize())
        translation_embed.add_field(name='Original Message:', value=content, inline=False)
        translation_embed.add_field(name='Translated Message:', value=translation.text, inline=False)

        await ctx.send(embed=translation_embed)

    @commands.command(
        name='afk',
        aliases=[],
        description='Sets your status as AFK. The bot will notify any member who tries to ping you that you\'re AFK.',
        extras={'requirement': 1}
    )
    async def afk(self, ctx: CustomContext, *, message: str = _reason):
        await self.bot.good_embed(ctx, f'*Set status to AFK: {message}*')
        await sleep(2)
        self._afk_users[ctx.author] = message

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if not message.guild or message.guild.id != self.bot.guild_id or message.author.bot:
            return

        if message.author in self._afk_users:
            try:
                await message.channel.send(f'*Removed {message.author.mention}\'s AFK.*', delete_after=5)
            except HTTPException:
                pass
            self._afk_users.pop(message.author)

        for user in self._afk_users:
            if user in message.mentions:
                try:
                    await message.reply(f'*`{user.name}` is AFK: {self._afk_users[user]}*', delete_after=5)
                except HTTPException:
                    pass
                break


async def setup(bot: CustomBot):
    await bot.add_cog(InformationCommands(bot))
