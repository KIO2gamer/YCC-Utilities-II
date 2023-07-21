import logging

from discord.ext import commands
from discord.utils import format_dt
from discord.abc import GuildChannel
from discord import (
    HTTPException,
    VoiceState,
    Member,
    Embed,
    Color,
    User,
    Message,
    Guild,
    Role,
    Asset
)

from main import CustomBot
from core.embed import EmbedField
from components.paginator import UnAuthoredPaginator


class EventLogger(commands.Cog):

    def __init__(self, bot: CustomBot):
        self.bot = bot

    async def _log_channel(self) -> GuildChannel | None:
        return await self.bot.metadata.get_channel('logging')

    @staticmethod
    async def _try_send(logger: GuildChannel, embed: Embed, event: str) -> Message | None:
        try:
            # noinspection PyUnresolvedReferences
            return await logger.send(embed=embed)
        except (HTTPException, AttributeError) as error:
            logging.error(f'Failed to log event {event} - {error}')

    @property
    def avatar(self) -> Asset:
        return self.bot.user.avatar or self.bot.user.default_avatar

    @property
    def ignored_channels(self) -> list[int]:
        return self.bot.metadata.event_ignored_channels

    @property
    def ignored_roles(self) -> list[int]:
        return self.bot.metadata.event_ignored_roles

    @commands.Cog.listener()
    async def on_message_edit(self, before: Message, after: Message):
        logger = await self._log_channel()
        if not logger:
            return
        elif not before.guild or before.guild.id != self.bot.guild_id or before.author == self.bot.user:
            return
        elif before.channel.id in self.ignored_channels or \
                [role for role in before.author.roles if role.id in self.ignored_roles]:
            return

        edited_msg_embed = Embed(
            color=Color.blue(),
            description=f'{before.author.mention} **([Jump to Message]({before.jump_url}))**')
        edited_msg_embed.set_author(name='Message Edited', icon_url=self.avatar)
        edited_msg_embed.set_thumbnail(url=before.author.avatar or before.author.default_avatar)
        edited_msg_embed.set_footer(text=f'User ID: {before.author.id}')

        edited_msg_embed.add_field(name='Message Content Before:', value=before.content or '`None`', inline=False)
        edited_msg_embed.add_field(name='Message Content After:', value=after.content or '`None`', inline=False)

        await self._try_send(logger, edited_msg_embed, 'on_message_edit')

    @commands.Cog.listener()
    async def on_message_delete(self, message: Message):
        logger = await self._log_channel()
        if not logger:
            return
        elif not message.guild or message.guild.id != self.bot.guild_id or message.author == self.bot.user:
            return
        elif message.channel.id in self.ignored_channels or \
                [role for role in message.author.roles if role.id in self.ignored_roles]:
            return

        deleted_msg_embed = Embed(
            color=Color.red(),
            description=f'{message.author.mention} (In {message.channel.mention})')
        deleted_msg_embed.set_author(name='Message Deleted', icon_url=self.avatar)
        deleted_msg_embed.set_thumbnail(url=message.author.avatar or message.author.default_avatar)
        deleted_msg_embed.set_footer(text=f'User ID: {message.author.id}')

        deleted_msg_embed.add_field(name='Message Content:', value=message.content or '`None`', inline=False)
        deleted_msg_embed.add_field(name='Message Sent At:', value=f'**{format_dt(message.created_at, "F")}**')

        await self._try_send(logger, deleted_msg_embed, 'on_message_delete')

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, payload: list[Message]):
        logger = await self._log_channel()
        if not logger:
            return
        elif not payload or not payload[0].guild or payload[0].guild.id != self.bot.guild_id:
            return
        elif payload[0].channel.id in self.ignored_channels:
            return

        for message in payload:
            if [role for role in message.author.roles if role.id in self.ignored_roles]:
                payload.remove(message)

        if not payload:
            return

        fields = [EmbedField(
            name=f'Message {payload.index(message) + 1}',
            text=f'**Sent by {message.author.mention} at {format_dt(message.created_at, "F")}**\n'
                 f'{message.content or "`None`"}',
            inline=False)
            for message in payload]
        embeds = self.bot.fields_to_embeds(
            fields,
            color=Color.red(),
            description=f'**{len(payload)} Messages Deleted (In {payload[0].channel.mention})**',
            author_name='Bulk Message Deletion',
            author_icon=self.avatar)

        log_message = await self._try_send(logger, embeds[0], 'on_bulk_message_delete')
        if log_message:
            await log_message.edit(view=UnAuthoredPaginator(None, log_message, embeds))

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: Role):
        logger = await self._log_channel()
        if not logger:
            return
        elif role.guild != self.bot.guild:
            return

        new_role_embed = Embed(
            color=Color.green(),
            description=role.mention)
        new_role_embed.set_author(name='Role Created', icon_url=self.avatar)
        new_role_embed.set_thumbnail(url=role.icon or role.guild.icon)
        new_role_embed.set_footer(text=f'Role ID: {role.id}')

        new_role_embed.add_field(name='Created At:', value=f'**{format_dt(role.created_at, "F")}**')

        await self._try_send(logger, new_role_embed, 'on_guild_role_create')

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: Role, after: Role):
        logger = await self._log_channel()
        if not logger:
            return
        elif before.guild != self.bot.guild:
            return
        elif before.id in self.ignored_roles:
            return
        elif before.name == after.name and before.color == after.color:
            return

        edited_role_embed = Embed(
            color=Color.blue(),
            description=before.mention)
        edited_role_embed.set_author(name='Role Updated', icon_url=self.avatar)
        edited_role_embed.set_thumbnail(url=after.icon or after.guild.icon)
        edited_role_embed.set_footer(text=f'Role ID: {after.id}')

        edited_role_embed.add_field(
            name='Before:', value=f'Name: `{before.name}`\nColor: `{before.color}`', inline=False)
        edited_role_embed.add_field(
            name='After:', value=f'Name: `{after.name}`\nColor: `{after.color}`', inline=False)

        await self._try_send(logger, edited_role_embed, 'on_guild_role_update')

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: Role):
        logger = await self._log_channel()
        if not logger:
            return
        elif role.guild != self.bot.guild:
            return
        elif role.id in self.ignored_roles:
            return

        deleted_role_embed = Embed(
            color=Color.red(),
            description=f'`{role.name}`')
        deleted_role_embed.set_author(name='Role Deleted', icon_url=self.avatar)
        deleted_role_embed.set_thumbnail(url=role.icon or role.guild.icon)
        deleted_role_embed.set_footer(text=f'Role ID: {role.id}')

        deleted_role_embed.add_field(name='Created At:', value=f'**{format_dt(role.created_at, "F")}**')

        await self._try_send(logger, deleted_role_embed, 'on_guild_role_delete')

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: GuildChannel):
        logger = await self._log_channel()
        if not logger:
            return
        elif channel.guild != self.bot.guild:
            return

        new_channel_embed = Embed(
            color=Color.green(),
            description=channel.mention)
        new_channel_embed.set_author(name='Channel Created', icon_url=self.avatar)
        new_channel_embed.set_thumbnail(url=channel.guild.icon)
        new_channel_embed.set_footer(text=f'Channel ID: {channel.id}')

        new_channel_embed.add_field(name='Created At:', value=f'**{format_dt(channel.created_at, "F")}**')

        await self._try_send(logger, new_channel_embed, 'on_guild_channel_create')

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: GuildChannel):
        logger = await self._log_channel()
        if not logger:
            return
        elif channel.guild != self.bot.guild:
            return
        elif channel.id in self.ignored_channels:
            return

        deleted_channel_embed = Embed(
            color=Color.red(),
            description=f'`#{channel.name}`')
        deleted_channel_embed.set_author(name='Channel Deleted', icon_url=self.avatar)
        deleted_channel_embed.set_thumbnail(url=channel.guild.icon)
        deleted_channel_embed.set_footer(text=f'Channel ID: {channel.id}')

        deleted_channel_embed.add_field(name='Created At:', value=f'**{format_dt(channel.created_at, "F")}**')

        await self._try_send(logger, deleted_channel_embed, 'on_guild_channel_delete')

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        logger = await self._log_channel()
        if not logger:
            return
        elif member.guild != self.bot.guild:
            return

        new_member_embed = Embed(
            color=Color.green(),
            description=member.mention)
        new_member_embed.set_author(name='Member Joined', icon_url=self.avatar)
        new_member_embed.set_thumbnail(url=member.avatar or member.default_avatar)
        new_member_embed.set_footer(text=f'User ID: {member.id}')

        new_member_embed.add_field(name='Account Created:', value=f'**{format_dt(member.created_at, "F")}**')

        await self._try_send(logger, new_member_embed, 'on_member_join')

    @commands.Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        logger = await self._log_channel()
        if not logger:
            return
        elif before.guild != self.bot.guild:
            return
        elif [role for role in before.roles + after.roles if role.id in self.ignored_roles]:
            return

        if before.nick != after.nick:
            author_name = 'Member Nickname Changed'
            field_name = 'Details:'
            field_text = f'**Before: `{before.nick or before.display_name}`**\n' \
                         f'**After: `{after.nick or after.display_name}`**'

        elif not before.is_timed_out() and after.is_timed_out():
            author_name = 'Member Timed Out'
            field_name = 'Timed Out Until:'
            field_text = f'**{format_dt(after.timed_out_until, "F")}**'

        elif before.is_timed_out() and not after.is_timed_out():
            author_name = 'Member Timeout Removed'
            field_name = None
            field_text = None

        elif len(before.roles) < len(after.roles):
            author_name = 'Member Role(s) Added'
            field_name = 'Role(s):'
            field_text = ' '.join([role.mention for role in after.roles if role not in before.roles])

        elif len(before.roles) > len(after.roles):
            author_name = 'Member Role(s) Removed'
            field_name = 'Role(s):'
            field_text = ' '.join([role.mention for role in before.roles if role not in after.roles])

        else:
            return

        edited_member_embed = Embed(
            color=Color.blue(),
            description=before.mention)
        edited_member_embed.set_author(name=author_name, icon_url=self.avatar)
        edited_member_embed.set_thumbnail(url=after.avatar or after.default_avatar)
        edited_member_embed.set_footer(text=f'User ID: {before.id}')

        if field_name and field_text:
            edited_member_embed.add_field(name=field_name, value=field_text, inline=False)
        edited_member_embed.add_field(name='Account Created:', value=f'**{format_dt(before.created_at, "F")}**')

        await self._try_send(logger, edited_member_embed, 'on_member_update')

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        logger = await self._log_channel()
        if not logger:
            return
        elif member.guild != self.bot.guild:
            return
        elif [role for role in member.roles if role.id in self.ignored_roles]:
            return

        left_member_embed = Embed(
            color=Color.red(),
            description=member.mention)
        left_member_embed.set_author(name='Member Left', icon_url=self.avatar)
        left_member_embed.set_thumbnail(url=member.avatar or member.default_avatar)
        left_member_embed.set_footer(text=f'User ID: {member.id}')

        left_member_embed.add_field(name='Account Created:', value=f'**{format_dt(member.created_at, "F")}**')

        await self._try_send(logger, left_member_embed, 'on_member_remove')

    @commands.Cog.listener()
    async def on_member_ban(self, guild: Guild, user: User | Member):
        if user.id not in self.bot.bans:
            self.bot.bans.append(user.id)

        logger = await self._log_channel()
        if not logger:
            return
        elif guild != self.bot.guild:
            return
        elif isinstance(user, Member) and [role for role in user.roles if role.id in self.ignored_roles]:
            return

        banned_embed = Embed(
            color=Color.red(),
            description=user.mention)
        banned_embed.set_author(name='User Banned', icon_url=self.avatar)
        banned_embed.set_thumbnail(url=user.avatar or user.default_avatar)
        banned_embed.set_footer(text=f'User ID: {user.id}')

        banned_embed.add_field(name='Account Created', value=f'**{format_dt(user.created_at, "F")}**')

        await self._try_send(logger, banned_embed, 'on_member_ban')

    @commands.Cog.listener()
    async def on_member_unban(self, guild: Guild, user: User):
        if user.id in self.bot.bans:
            self.bot.bans.remove(user.id)

        logger = await self._log_channel()
        if not logger:
            return
        elif guild != self.bot.guild:
            return

        unbanned_embed = Embed(
            color=Color.green(),
            description=user.mention)
        unbanned_embed.set_author(name='User Unbanned', icon_url=self.avatar)
        unbanned_embed.set_thumbnail(url=user.avatar or user.default_avatar)
        unbanned_embed.set_footer(text=f'User ID: {user.id}')

        unbanned_embed.add_field(name='Account Created', value=f'**{format_dt(user.created_at, "F")}**')

        await self._try_send(logger, unbanned_embed, 'on_member_unban')

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        logger = await self._log_channel()
        if not logger:
            return
        elif member.guild != self.bot.guild:
            return
        elif [role for role in member.roles if role.id in self.ignored_roles]:
            return

        if not before.channel:
            color = Color.green()
            author_name = 'Member Joined VC'
            field_text = after.channel.mention

        elif not after.channel:
            color = Color.red()
            author_name = 'Member Left VC'
            field_text = before.channel.mention

        elif before.channel != after.channel:
            color = Color.blue()
            author_name = 'Member Switched VCs'
            field_text = f'{before.channel.mention} **->** {after.channel.mention}'

        else:
            return

        vc_embed = Embed(
            color=color,
            description=member.mention)
        vc_embed.set_author(name=author_name, icon_url=self.avatar)
        vc_embed.set_thumbnail(url=member.avatar or member.default_avatar)
        vc_embed.set_footer(text=f'User ID: {member.id}')

        vc_embed.add_field(name='Voice Channel:', value=field_text)

        await self._try_send(logger, vc_embed, 'on_voice_state_update')


async def setup(bot: CustomBot):
    await bot.add_cog(EventLogger(bot))
