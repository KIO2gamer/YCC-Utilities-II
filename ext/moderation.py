from unicodedata import normalize
from random import randint

from discord.ext import commands
from discord.utils import utcnow
from discord import (
    HTTPException,
    Member,
    User
)

from main import CustomBot
from core.context import CustomContext


class ModerationCommands(commands.Cog):

    _reason = 'No reason provided.'
    _sent_mapping = {True: '', False: ' (I could not DM them)'}

    def __init__(self, bot: CustomBot):
        self.bot = bot

    @commands.command(
        name='decancer',
        aliases=['dc'],
        description='Converts a member\'s nickname into standard English font.',
        extras={'requirement': 1}
    )
    @commands.bot_has_permissions(manage_nicknames=True)
    async def decancer(self, ctx: CustomContext, member: Member, *, reason: str = _reason):
        await self.bot.check_target_member(member)

        new_nickname = normalize('NFKD', member.display_name).encode('ascii', 'ignore').decode('utf-8')
        await member.edit(nick=new_nickname)

        modlog_data = await ctx.to_modlog_data(member.id, reason=reason)
        await self.bot.mongo_db.insert_modlog(**modlog_data)

        await self.bot.good_embed(ctx, f'Changed {member.mention}\'s nickname.')

    @commands.command(
        name='modnick',
        aliases=['mn', 'nick'],
        description='Assigns a randomly-generated nickname to a member.',
        extras={'requirement': 1}
    )
    @commands.bot_has_permissions(manage_nicknames=True)
    async def modnick(self, ctx: CustomContext, member: Member, *, reason: str = _reason):
        await self.bot.check_target_member(member)

        new_nickname = f'Moderated Nickname-{hex(randint(1, 10000000))}'
        await member.edit(nick=new_nickname)

        modlog_data = await ctx.to_modlog_data(member.id, reason=reason)
        await self.bot.mongo_db.insert_modlog(**modlog_data)

        await self.bot.good_embed(ctx, f'Changed {member.mention}\'s nickname.')

    @commands.command(
        name='note',
        aliases=['n', 'addnote'],
        description='Add a note for a user. This will be visible in their modlogs.',
        extras={'requirement': 1}
    )
    async def note(self, ctx: CustomContext, user: User, *, reason: str = _reason):
        await self.bot.check_target_member(user)

        modlog_data = await ctx.to_modlog_data(user.id, reason=reason)
        await self.bot.mongo_db.insert_modlog(**modlog_data)

        await self.bot.good_embed(ctx, f'Note added for {user.mention}.')

    @commands.command(
        name='dm',
        aliases=['message', 'send'],
        description='Attempts to send an anonymous DM to a member. This will be visible in their modlogs.',
        extras={'requirement': 1}
    )
    async def dm(self, ctx: CustomContext, user: User, *, reason: str = _reason):
        await self.bot.check_target_member(user)

        try:
            await self.bot.neutral_embed(user, f'**You received a message from {self.bot.guild}:** {reason}')
        except HTTPException:
            await self.bot.bad_embed(ctx, f'❌ Unable to message {user.mention}.')
            return

        modlog_data = await ctx.to_modlog_data(user.id, reason=reason, received=True)
        await self.bot.mongo_db.insert_modlog(**modlog_data)

        await self.bot.good_embed(ctx, f'Message sent to {user.mention}.')

    @commands.command(
        name='warn',
        aliases=['w'],
        description='Formally warns a user, creates a new modlog entry and DMs them the reason.',
        extras={'requirement': 1}
    )
    async def warn(self, ctx: CustomContext, user: User, *, reason: str = _reason):
        await self.bot.check_target_member(user)

        sent = False
        try:
            await self.bot.bad_embed(user, f'**You received a warning in {self.bot.guild} for:** {reason}')
            sent = True
        except HTTPException:
            pass

        modlog_data = await ctx.to_modlog_data(user.id, reason=reason, received=sent)
        await self.bot.mongo_db.insert_modlog(**modlog_data)

        await self.bot.good_embed(ctx, f'Warned {user.mention}: {reason}{self._sent_mapping[sent]}')

    @commands.command(
        name='mute',
        aliases=['m', 'timeout'],
        description='Puts a user in timeout, creates a new modlog entry and DMs them the reason.',
        extras={'requirement': 2}
    )
    @commands.bot_has_permissions(moderate_members=True)
    async def mute(self, ctx: CustomContext, user: User, duration: str, *, reason: str = _reason):
        await self.bot.check_target_member(user)

        _time_delta = self.bot.convert_duration(duration)
        seconds = _time_delta.total_seconds()
        until = round(utcnow().timestamp() + seconds)

        member = await self.bot.user_to_member(user)
        if isinstance(member, Member):
            if member.is_timed_out() is True:
                raise Exception(f'{member.mention} is already muted.')
            else:
                await member.timeout(_time_delta)

        sent = False
        try:
            await self.bot.bad_embed(user, f'**You were muted in {self.bot.guild} until <t:{until}:F> for:** {reason}')
            sent = True
        except HTTPException:
            pass

        modlog_data = await ctx.to_modlog_data(user.id, reason=reason, received=sent, duration=seconds)
        await self.bot.mongo_db.insert_modlog(**modlog_data)

        await self.bot.good_embed(ctx, f'Muted {user.mention} until <t:{until}:F>: {reason}{self._sent_mapping[sent]}')


async def setup(bot: CustomBot):
    await bot.add_cog(ModerationCommands(bot))
