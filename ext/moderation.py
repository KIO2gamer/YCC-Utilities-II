import logging
from unicodedata import normalize
from datetime import timedelta
from random import randint
from typing import Callable, Optional

from discord.ext import commands
from discord.abc import GuildChannel
from discord.utils import utcnow, MISSING
from discord import (
    PermissionOverwrite,
    HTTPException,
    Member,
    Color,
    User,
    Role
)

from main import CustomBot
from core.embed import CustomEmbed
from core.modlog import ModLogEntry
from core.context import CustomContext
from core.errors import DurationError, ModLogNotFound
from components.appeal import BanAppealView


class ModerationCommands(commands.Cog):

    _reason = 'No reason provided.'
    _sent_map = {True: '', False: ' (I could not DM them)'}
    _anti_lock_role_names = ('rmod', 'smod', 'hmod', 'senior')

    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.locked_channels = {}

    @staticmethod
    async def _try_send(func: Callable, *args, **kwargs) -> bool:
        try:
            await func(*args, **kwargs)
            return True
        except HTTPException:
            return False

    async def _end_modlogs(self, _user_id: int, _type: str, _channel_id: int) -> None:
        while True:
            try:
                await self.bot.mongo_db.update_modlog(
                    _user_id=_user_id, _type=_type, _channel_id=_channel_id, _active=True, active=False)
            except ModLogNotFound:
                break

    async def _anti_lock_roles(self) -> list[Optional[Role]]:
        return [await self.bot.metadata.get_role(role_name) for role_name in self._anti_lock_role_names]

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

        await self.bot.good_embed(ctx, f'*Changed {member.mention}\'s nickname:* {reason}')

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

        await self.bot.good_embed(ctx, f'*Changed {member.mention}\'s nickname:* {reason}')

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

        await self.bot.good_embed(ctx, f'*Note added for {user.mention}:* {reason}')

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
            raise Exception(f'Unable to message {user.mention}.')

        modlog_data = await ctx.to_modlog_data(user.id, reason=reason, received=True)
        await self.bot.mongo_db.insert_modlog(**modlog_data)

        await self.bot.good_embed(ctx, f'*Message sent to {user.mention}:* {reason}')

    @commands.command(
        name='warn',
        aliases=['w'],
        description='Formally warns a user, creates a new modlog entry and DMs them the reason.',
        extras={'requirement': 1}
    )
    async def warn(self, ctx: CustomContext, user: User, *, reason: str = _reason):
        await self.bot.check_target_member(user)

        message = f'**You received a warning in {self.bot.guild} for:** {reason}'
        sent = await self._try_send(self.bot.bad_embed, user, message)

        modlog_data = await ctx.to_modlog_data(user.id, reason=reason, received=sent)
        modlog = await self.bot.mongo_db.insert_modlog(**modlog_data)
        await self.publicise_modlog(user, modlog)

        await self.bot.good_embed(ctx, f'*Warned {user.mention}:* {reason}{self._sent_map[sent]}')

    @commands.command(
        name='kick',
        aliases=['k', 'remove'],
        desription='Kicks a member from the guild, creates a new modlog entry and DMs them the reason.',
        extras={'requirement': 2}
    )
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx: CustomContext, member: Member, *, reason: str = _reason):
        await self.bot.check_target_member(member)

        message = f'**You were kicked from {self.bot.guild} for:** {reason}'
        sent = await self._try_send(self.bot.bad_embed, member, message)

        await member.kick()

        modlog_data = await ctx.to_modlog_data(member.id, reason=reason, received=sent)
        modlog = await self.bot.mongo_db.insert_modlog(**modlog_data)
        await self.publicise_modlog(member, modlog)

        await self.bot.good_embed(ctx, f'*Kicked {member.mention}:* {reason}{self._sent_map[sent]}')

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
        til = round(utcnow().timestamp() + seconds)

        if not 60 <= seconds <= 2419200:
            raise Exception('Duration must be between 1 minute and 28 days.')

        member = await self.bot.user_to_member(user)
        if isinstance(member, Member):
            if member.is_timed_out() is True:
                raise Exception(f'{member.mention} is already muted.')
            else:
                await member.timeout(_time_delta)

        message = f'**You were muted in {self.bot.guild} until <t:{til}:F> for:** {reason}'
        sent = await self._try_send(self.bot.bad_embed, user, message)

        modlog_data = await ctx.to_modlog_data(user.id, reason=reason, received=sent, duration=seconds)
        modlog = await self.bot.mongo_db.insert_modlog(**modlog_data)
        await self.publicise_modlog(user, modlog)

        await self.bot.good_embed(ctx, f'*Muted {user.mention} until <t:{til}:F>:* {reason}{self._sent_map[sent]}')

    @commands.command(
        name='ban',
        aliases=['b'],
        description='Bans a user from the guild, creates a new modlog entry and DMs them the reason.',
        extras={'requirement': 2}
    )
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx: CustomContext, user: User, duration: str, *, reason: str = _reason):
        await self.bot.check_target_member(user)

        if user.id in self.bot.bans:
            raise Exception(f'{user.mention} is already banned.')

        permanent = False
        if duration.lower() in 'permanent':
            permanent = True
            _time_delta = timedelta(seconds=self.bot.perm_duration)
        else:
            _time_delta = self.bot.convert_duration(duration)
        seconds = _time_delta.total_seconds()
        til = round(utcnow().timestamp() + seconds)

        if seconds == self.bot.perm_duration:
            permanent = True

        until_str = f' until <t:{til}:F>' if permanent is False else ' permanently'
        message = f'**You were banned from {self.bot.guild}{until_str} for:** {reason}'

        appeal_url = self.bot.metadata.appeal_url
        view = BanAppealView(appeal_url) if appeal_url and user.id not in self.bot.metadata.appeal_bl else MISSING

        sent = await self._try_send(self.bot.bad_embed, user, message, view=view)

        await self.bot.guild.ban(user, delete_message_days=0)

        modlog_data = await ctx.to_modlog_data(user.id, reason=reason, received=sent, duration=seconds)
        modlog = await self.bot.mongo_db.insert_modlog(**modlog_data)
        await self.publicise_modlog(user, modlog)

        await self.bot.good_embed(ctx, f'*Banned {user.mention}{until_str}:* {reason}{self._sent_map[sent]}')

    @commands.command(
        name='channelban',
        aliases=['cb', 'cban', 'channelblock'],
        description='Blocks a user from viewing a channel, creates a new modlog entry and DMs them the reason.',
        extras={'requirement': 3}
    )
    @commands.bot_has_permissions(manage_roles=True)
    async def channel_ban(
            self, ctx: CustomContext, user: User, channel: GuildChannel, duration: str, *, reason: str = _reason):
        await self.bot.check_target_member(user)

        if channel.overwrites_for(user).view_channel is False:
            raise Exception(f'{user.mention} is already blocked from viewing {channel.mention}.')

        permanent = False
        if duration.lower() in 'permanent':
            permanent = True
            _time_delta = timedelta(seconds=self.bot.perm_duration)
        else:
            _time_delta = self.bot.convert_duration(duration)
        seconds = _time_delta.total_seconds()
        til = round(utcnow().timestamp() + seconds)

        if seconds == self.bot.perm_duration:
            permanent = True

        until_str = f' until <t:{til}:F>' if permanent is False else ''
        message = f'**You were blocked from viewing `#{channel}` in {self.bot.guild}{until_str} for:** {reason}'
        sent = await self._try_send(self.bot.bad_embed, user, message)

        member = await self.bot.user_to_member(user)
        if isinstance(member, Member):
            await channel.set_permissions(member, view_channel=False)

        modlog_data = await ctx.to_modlog_data(
            user.id, channel_id=channel.id, reason=reason, received=sent, duration=seconds)
        await self.bot.mongo_db.insert_modlog(**modlog_data)

        await self.bot.good_embed(
            ctx, f'*Blocked {user.mention} from {channel.mention}{until_str}:* {reason}{self._sent_map[sent]}')

    @commands.command(
        name='unmute',
        aliases=['um'],
        description='Unmutes a timed-out member, creates a new modlogs entry and DMs them the reason.',
        extras={'requirement': 4}
    )
    @commands.bot_has_permissions(moderate_members=True)
    async def unmute(self, ctx: CustomContext, member: Member, *, reason: str = _reason):
        if member.is_timed_out() is False:
            raise Exception(f'{member.mention} is not muted.')

        message = f'**You were unmuted in {self.bot.guild} for:** {reason}'
        sent = await self._try_send(self.bot.neutral_embed, member, message)

        await member.timeout(None)

        modlog_data = await ctx.to_modlog_data(member.id, reason=reason, received=sent)
        modlog = await self.bot.mongo_db.insert_modlog(**modlog_data)
        await self._end_modlogs(member.id, 'mute', 0)
        await self.publicise_modlog(member, modlog)

        await self.bot.good_embed(ctx, f'*Unmuted {member.mention}:* {reason}{self._sent_map[sent]}')

    @commands.command(
        name='unban',
        aliases=['ub'],
        description='Unbans a user from the guild, creates a new modlogs entry and DMs them the reason.',
        extras={'requirement': 4}
    )
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx: CustomContext, user: User, *, reason: str = _reason):
        if user.id not in self.bot.bans:
            raise Exception(f'{user.mention} is not banned.')

        message = f'**You were unbanned from {self.bot.guild} for:** {reason}'
        sent = await self._try_send(self.bot.neutral_embed, user, message)

        await self.bot.guild.unban(user)

        modlog_data = await ctx.to_modlog_data(user.id, reason=reason, received=sent)
        modlog = await self.bot.mongo_db.insert_modlog(**modlog_data)
        await self._end_modlogs(user.id, 'ban', 0)
        await self.publicise_modlog(user, modlog)

        await self.bot.good_embed(ctx, f'*Unbanned {user.mention}:* {reason}{self._sent_map[sent]}')

    @commands.command(
        name='channelunban',
        aliases=['cub', 'cunban', 'channelub'],
        description='Unblocks a user from the channel, creates a new modlogs entry and DMs them the reason.',
        extras={'requirement': 4}
    )
    @commands.bot_has_permissions(manage_roles=True)
    async def channel_unban(self, ctx: CustomContext, user: User, channel: GuildChannel, *, reason: str = _reason):
        if channel.overwrites_for(user).view_channel is not False:
            raise Exception(f'{user.mention} is not blocked from viewing {channel.mention}.')

        message = f'**You were unblocked from `#{channel}` in {self.bot.guild} for:** {reason}'
        sent = await self._try_send(self.bot.neutral_embed, user, message)

        member = await self.bot.user_to_member(user)
        if isinstance(member, Member):
            await channel.set_permissions(member, view_channel=None)

        modlog_data = await ctx.to_modlog_data(user.id, reason=reason, received=sent)
        await self.bot.mongo_db.insert_modlog(**modlog_data)
        await self._end_modlogs(user.id, 'channel_ban', channel.id)

        await self.bot.good_embed(ctx, f'*Unblocked {user.mention} from {channel.mention}:* {reason}')

    @commands.command(
        name='softban',
        aliases=['sb'],
        description='Bans/unbans a user to cleanse their message history.',
        extras={'requirement': 3}
    )
    @commands.bot_has_permissions(ban_members=True)
    async def softban(self, ctx: CustomContext, user: User, cleanse_duration: str, *, reason: str = _reason):
        await self.bot.check_target_member(user)

        if user.id in self.bot.bans:
            raise Exception(f'{user.mention} is already banned.')

        _time_delta = self.bot.convert_duration(cleanse_duration)
        seconds = round(_time_delta.total_seconds())
        then = round(utcnow().timestamp() - seconds)

        if seconds < 0 or seconds > 604800:
            raise Exception('Cleansing duration must be between zero seconds and one week.')

        message = f'**You were kicked from {self.bot.guild} for:** {reason}'
        sent = await self._try_send(self.bot.bad_embed, user, message)

        await self.bot.guild.ban(user, delete_message_seconds=seconds)
        await self.bot.guild.unban(user)

        modlog_data = await ctx.to_modlog_data(user.id, reason=reason, received=sent)
        modlog = await self.bot.mongo_db.insert_modlog(**modlog_data)
        await self.publicise_modlog(user, modlog)

        await self.bot.good_embed(
            ctx,
            f'*Softbanned {user.mention} and cleansed messages from <t:{then}:F>:* {reason}{self._sent_map[sent]}'
        )

    @commands.command(
        name='slowmode',
        aliases=['sm'],
        description='Sets a slow-mode timer for a guild channel.',
        extras={'requirement': 3}
    )
    @commands.bot_has_permissions(manage_channels=True)
    async def slowmode(self, ctx: CustomContext, duration: str, channel: GuildChannel = None):
        channel = channel or ctx.channel

        _time_delta = self.bot.convert_duration(duration, allow_any_duration=True)
        if not 0 <= _time_delta.total_seconds() <= 21600:
            raise DurationError()

        await channel.edit(slowmode_delay=round(_time_delta.total_seconds()))
        await self.bot.good_embed(ctx, f'*Slowmode set to `{_time_delta}` in {channel.mention}.*')

    @commands.command(
        name='purge',
        aliases=[],
        description='Bulk-deletes up to 100 messages, either indiscriminantly or only those sent by a specific user.',
        extras={'requirement': 3}
    )
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx: CustomContext, count: int, user: User = None):
        if count < 1:
            count = 1
        elif count > 100:
            count = 100

        await ctx.message.delete()

        message_count = 0
        purge_limit = 0

        async for message in ctx.channel.history(limit=1000):
            purge_limit += 1
            if not user or message.author == user:
                message_count += 1
            if message_count == count:
                break

        await ctx.channel.purge(limit=purge_limit, check=lambda _message: not user or _message.author == user)

    @commands.command(
        name='lock',
        aliases=['lockchannel'],
        description='Locks down a channel, preventing all non-staff members from using it.',
        extras={'requirement': 4}
    )
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def lock(self, ctx: CustomContext, c: GuildChannel = None):
        c = c or ctx.channel
        if c in self.locked_channels:
            raise Exception(f'{c.mention} is already locked.')

        everyone: Role = self.bot.guild.default_role
        al_roles: list[Role] = [role for role in await self._anti_lock_roles() if role is not None]

        self.locked_channels[c] = {everyone: c.overwrites_for(everyone)} | {r: c.overwrites_for(r) for r in al_roles}

        everyone_ovr_map: dict[Role, PermissionOverwrite] = {everyone: c.overwrites_for(everyone)}
        al_roles_ovr_map: dict[Role, PermissionOverwrite] = {r: c.overwrites_for(r) for r in al_roles}

        everyone_ovr = everyone_ovr_map[everyone]
        everyone_ovr.update(send_messages=False, add_reactions=False, connect=False, send_messages_in_threads=False)
        await c.set_permissions(everyone, overwrite=everyone_ovr)

        for role in al_roles_ovr_map:
            ovr = al_roles_ovr_map[role]
            ovr.update(send_messages=True, add_reactions=True, connect=True, send_messages_in_threads=True)
            await c.set_permissions(role, overwrite=ovr)

        await self.bot.good_embed(ctx, f'*{c.mention} has been locked!*')

    @commands.command(
        name='unlock',
        aliases=['unlockchannel'],
        description='Unlocks a locked channel, reversing the effects of the `lock` command.',
        extras={'requirement': 4}
    )
    @commands.bot_has_permissions(manage_roles=True)
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def unlock(self, ctx: CustomContext, channel: GuildChannel = None):
        channel = channel or ctx.channel
        if channel not in self.locked_channels:
            raise Exception(f'{channel.mention} is not locked.')

        original_overwrites: dict[Role, PermissionOverwrite] = self.locked_channels[channel]
        self.locked_channels.pop(channel)

        for role in original_overwrites:
            await channel.set_permissions(role, overwrite=original_overwrites[role])

        await self.bot.good_embed(ctx, f'*{channel.mention} has been unlocked!*')

    async def publicise_modlog(self, user: User | Member, modlog: ModLogEntry) -> None:
        pmc = await self.bot.metadata.get_channel('public_modlog')
        if pmc is None:
            return

        duration_s = modlog.duration
        duration = 'permanent' if duration_s == self.bot.perm_duration else str(timedelta(seconds=duration_s))

        modlog_embed = CustomEmbed(
            description=f'{user.mention} **(Case {modlog.id})**',
            color=Color.blue()
        )
        modlog_embed.set_author(name='Modlog Created', icon_url=self.bot.user.avatar or self.bot.user.default_avatar)
        modlog_embed.set_thumbnail(url=user.avatar or user.default_avatar)
        modlog_embed.set_footer(text=f'User ID: {user.id}')

        modlog_embed.add_field(
            name='Reason:',
            value=modlog.reason,
            inline=False
        )
        modlog_embed.add_field(
            name='Other Details:',
            value=f'**Type: `{modlog.type.capitalize()}`**\n'
                  f'**Duration: `{duration}`**\n'
                  f'**Received: `{modlog.received}`**',
            inline=False
        )

        try:
            # noinspection PyUnresolvedReferences
            await pmc.send(embed=modlog_embed)
        except (HTTPException, AttributeError) as error:
            logging.error(f'Failed to post new Modlog entry into {pmc.id} - {error}')


async def setup(bot: CustomBot):
    await bot.add_cog(ModerationCommands(bot))
