import logging
from re import findall
from urllib.parse import urlparse
from datetime import timedelta

from discord.ext import commands, tasks
from discord.abc import GuildChannel
from discord.utils import utcnow
from discord import (
    HTTPException,
    Thread,
    Message,
    Member,
    Embed,
    Color
)

from main import CustomBot


class AutoModerator(commands.Cog):

    MUTE_DURATION = 120

    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.infraction_map: dict[Member, int] = {}

    def cog_load(self):
        self.infraction_cooldown.add_exception_type(Exception)
        self.infraction_cooldown.start()

    def cog_unload(self):
        self.infraction_cooldown.cancel()
        self.infraction_cooldown.clear_exception_types()

    @tasks.loop(minutes=1)
    async def infraction_cooldown(self):
        for member in self.infraction_map:
            self.infraction_map[member] -= 1

        to_delete = [member for member in self.infraction_map if self.infraction_map[member] < 1]
        for member in to_delete:
            self.infraction_map.pop(member)

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        await self.moderate_message(message)

    @commands.Cog.listener()
    async def on_message_edit(self, _: Message, after: Message):
        await self.moderate_message(after)

    async def moderate_message(self, message: Message):
        author = message.author
        if not message.guild or message.guild.id != self.bot.guild_id or author.bot:
            return

        if isinstance(message.channel, GuildChannel):
            channel = message.channel
        elif isinstance(message.channel, Thread):
            channel = message.channel.parent
        else:
            return

        urls = findall(r'(https?://\S+)', message.content)
        domains = [urlparse(url).netloc for url in urls]

        if not domains or await self.bot.member_clearance(author) > 1:
            return
        elif [domain for domain in domains if domain in self.bot.metadata.domain_bl]:
            pass
        elif [role for role in author.roles if role.id in self.bot.metadata.auto_mod_ignored_roles]:
            return
        elif not [domain for domain in domains if domain not in self.bot.metadata.domain_wl] \
                and channel.id in self.bot.metadata.auto_mod_ignored_channels:
            return

        try:
            await message.delete()
        except HTTPException as error:
            logging.error(f'Failed to moderate message (ID: {message.id}) - {error}')
            return

        try:
            await channel.send(f'{author.mention}, that link is not allowed.', delete_after=5)
        except HTTPException:
            pass

        msg_embed = Embed(color=Color.red(), description=f'{author.mention} (In {channel.mention})')
        msg_embed.set_author(icon_url=self.bot.user.avatar or self.bot.user.default_avatar, name='Message Deleted')
        msg_embed.set_thumbnail(url=author.avatar or author.default_avatar)
        msg_embed.set_footer(text=f'User ID: {author.id}')
        msg_embed.add_field(name='Message Content', value=message.content, inline=False)
        msg_embed.add_field(name='Keyword:', value=urls[0], inline=False)

        try:
            automod_log_channel = await self.bot.metadata.get_channel('automod')
            if not automod_log_channel:
                return
            # noinspection PyUnresolvedReferences
            await automod_log_channel.send(embed=msg_embed)
        except HTTPException as error:
            logging.error(f'Failed to log auto-moderation - {error}')

        try:
            self.infraction_map[author] += 1
        except KeyError:
            self.infraction_map[author] = 1

        if self.infraction_map[author] % 5:
            return
        self.infraction_map.pop(author)

        try:
            await author.timeout(timedelta(seconds=self.MUTE_DURATION))
        except HTTPException as error:
            logging.error(f'Failed to time out {author} (ID: {author.id}) for auto-mod infractions - {error}')
            return

        await self.bot.mongo_db.insert_modlog(
            case_id=await self.bot.mongo_db.new_modlog_id(), mod_id=self.bot.user.id, user_id=author.id,
            type='mute', reason='[AUTO] 5 Auto-Mod infractions.', created=round(utcnow().timestamp()),
            duration=self.MUTE_DURATION, received=False, active=True, deleted=False)


async def setup(bot: CustomBot):
    await bot.add_cog(AutoModerator(bot))
