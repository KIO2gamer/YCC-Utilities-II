import asyncio
import logging
from time import time
from datetime import timedelta

from discord.ext import commands, tasks
from discord.abc import GuildChannel
from discord.utils import utcnow, format_dt
from discord import (
    HTTPException,
    VoiceState,
    Message,
    Member,
    Embed,
    Color,
    User
)

from main import CustomBot
from core.context import CustomContext
from core.errors import ModLogNotFound


class UserStatistics(commands.Cog):

    ACTIVE_ROLE_LOOKBACK = 2419200
    ACTIVE_ROLE_LIMIT = 10

    MOD_STAT_TYPES = {'dm': 'DMs', 'warn': 'Warns', 'kick': 'Kicks',
                      'mute': 'Mutes', 'ban': 'Bans', 'channel_ban': 'Channel Bans',
                      'unmute': 'Unmutes', 'unban': 'Unbans', 'channel_unban': 'Channel Unbans'}

    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.msg_stats, self.vc_stats, self.pending_vc_stats = [], [], []

    def cog_load(self) -> None:
        self.handle_stats.add_exception_type(Exception)
        self.handle_stats.start()

    def cog_unload(self) -> None:
        self.handle_stats.cancel()
        self.handle_stats.clear_exception_types()

    @tasks.loop(minutes=1)
    async def handle_stats(self) -> None:
        await self.bot.wait_until_ready()
        await asyncio.sleep(45)

        _msg, _vc = [_ for _ in self.msg_stats], [_ for _ in self.vc_stats]
        self.msg_stats, self.vc_stats = [], []
        await self.bot.mongo_db.dump_msg_stats(_msg)
        await self.bot.mongo_db.dump_vc_stats(_vc)

        active_role = await self.bot.metadata.get_role('active')
        if not active_role:
            return

        msg_stats = await self.bot.mongo_db.get_msg_stats(lookback=self.ACTIVE_ROLE_LOOKBACK)
        vc_stats = await self.bot.mongo_db.get_vc_stats(lookback=self.ACTIVE_ROLE_LOOKBACK)
        sorted_stats = self.get_sorted_stats(msg_stats, vc_stats)

        _l = self.ACTIVE_ROLE_LIMIT

        top_10_msg_users, top_10_vc_users = list(sorted_stats.get('umc', {})), list(sorted_stats.get('uvt', {}))
        top_10_msg_users = top_10_msg_users if len(top_10_msg_users) < _l else top_10_msg_users[:_l]
        top_10_vc_users = top_10_vc_users if len(top_10_vc_users) < _l else top_10_vc_users[:_l]

        top_users: set[int] = set(top_10_msg_users + top_10_vc_users)
        role_users: list[int] = [user.id for user in active_role.members]

        user_ids_in = [user_id for user_id in top_users if user_id not in role_users]
        user_ids_out = [user_id for user_id in role_users if user_id not in top_users]

        for user_id in user_ids_in:
            try:
                member = self.bot.guild.get_member(user_id) or await self.bot.guild.fetch_member(user_id)
                await member.add_roles(active_role)
            except HTTPException as error:
                logging.error(f'Failed to add active role to member (ID: {user_id}) - {error}')
        for user_id in user_ids_out:
            try:
                member = self.bot.guild.get_member(user_id) or await self.bot.guild.fetch_member(user_id)
                await member.remove_roles(active_role)
            except HTTPException as error:
                logging.error(f'Failed to remove active role from member (ID: {user_id}) - {error}')

    def _on_join_vc(self, member: Member, after: VoiceState) -> None:
        vc_dict = {
            'user_id': member.id,
            'channel_id': after.channel.id,
            'joined': time(),
        }
        self.pending_vc_stats.append(vc_dict)

    def _on_leave_vc(self, member: Member) -> None:
        try:
            ongoing = [vc_stat for vc_stat in self.pending_vc_stats if vc_stat['user_id'] == member.id][0]
        except IndexError:
            return
        self.pending_vc_stats.remove(ongoing)
        ongoing['left'] = time()
        self.vc_stats.append(ongoing)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState) -> None:
        if member.guild.id != self.bot.guild_id or member.bot or before.channel == after.channel:
            return

        if not before.channel:
            self._on_join_vc(member, after)

        elif not after.channel:
            self._on_leave_vc(member)

        elif before.channel and after.channel:
            self._on_leave_vc(member)
            self._on_join_vc(member, after)

    @commands.Cog.listener()
    async def on_message(self, message: Message) -> None:
        if not message.guild or message.guild.id != self.bot.guild_id or message.author.bot:
            return

        msg_dict = {
            'user_id': message.author.id,
            'message_id': message.id,
            'channel_id': message.channel.id,
            'created': time()
        }
        self.msg_stats.append(msg_dict)

    @staticmethod
    def get_sorted_stats(msg_stats: list[dict], vc_stats: list[dict]) -> dict[str, dict]:
        umc, cmc, uvt, cvt = {}, {}, {}, {}

        for entry in msg_stats:
            user = entry.get('user_id')
            channel = entry.get('channel_id')
            try:
                umc[user] += 1
            except KeyError:
                umc[user] = 1
            try:
                cmc[channel] += 1
            except KeyError:
                cmc[channel] = 1

        for entry in vc_stats:
            user = entry.get('user_id')
            channel = entry.get('channel_id')
            vc_td = entry.get('left', 0) - entry.get('joined', 0)
            try:
                uvt[user] += vc_td
            except KeyError:
                uvt[user] = vc_td
            try:
                cvt[channel] += vc_td
            except KeyError:
                cvt[channel] = vc_td

        umc = {k: i for k, i in sorted(umc.items(), key=lambda x: x[1], reverse=True)}
        cmc = {k: i for k, i in sorted(cmc.items(), key=lambda x: x[1], reverse=True)}
        uvt = {k: i for k, i in sorted(uvt.items(), key=lambda x: x[1], reverse=True)}
        cvt = {k: i for k, i in sorted(cvt.items(), key=lambda x: x[1], reverse=True)}

        return {'umc': umc, 'cmc': cmc, 'uvt': uvt, 'cvt': cvt}

    @commands.command(
        name='topstats',
        aliases=[],
        description='View the most active users and channels in the server.',
        extras={'requirement': 0}
    )
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def topstats(self, ctx: CustomContext, lookback: str = '28d'):
        async with ctx.typing():
            _time_delta = self.bot.convert_duration(lookback)
            seconds = _time_delta.total_seconds()

            msg_stats = await self.bot.mongo_db.get_msg_stats(seconds)
            vc_stats = await self.bot.mongo_db.get_vc_stats(seconds)

            sorted_stats = self.get_sorted_stats(msg_stats, vc_stats)

            umc = sorted_stats.get('umc', {})
            cmc = sorted_stats.get('cmc', {})
            uvt = sorted_stats.get('uvt', {})
            cvt = sorted_stats.get('cvt', {})

            since_dt = utcnow() - _time_delta
            avatar = self.bot.user.avatar
            guild = self.bot.guild
            nd = '`No data to be displayed`'

            topstats_embed = Embed(color=Color.blue(), title=guild, description=f'**Since {format_dt(since_dt, "F")}**')
            topstats_embed.set_author(name='Top Statistics', icon_url=avatar)
            topstats_embed.set_thumbnail(url=guild.icon or avatar)
            topstats_embed.set_footer(text=f'Try out {self.bot.command_prefix}stats to view your own stats!')

            topstats_embed.add_field(
                name='User Messages:',
                value='\n'.join([f'> <@{u}>**: {umc[u]:,}**' for u in list(umc)[:5]]) or nd,
                inline=False)
            topstats_embed.add_field(
                name='Channel Messages:',
                value='\n'.join([f'> <#{c}>**: {cmc[c]:,}**' for c in list(cmc)[:5]]) or nd,
                inline=False)
            topstats_embed.add_field(
                name='User VC Activity:',
                value='\n'.join([f'> <@{u}>**: `{timedelta(seconds=round(uvt[u]))}`**' for u in list(uvt)[:5]]) or nd,
                inline=False)
            topstats_embed.add_field(
                name='Channel VC Activity:',
                value='\n'.join([f'> <#{c}>**: `{timedelta(seconds=round(cvt[c]))}`**' for c in list(cvt)[:5]]) or nd,
                inline=False)

        await ctx.send(embed=topstats_embed)

    @commands.command(
        name='stats',
        aliases=[],
        description='View your own activity stats or check the stats of another user/channel.',
        extras={'requirement': 0}
    )
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def stats(self, ctx: CustomContext, target: GuildChannel | User = None, lookback: str = '28d'):
        async with ctx.typing():
            target = target or ctx.author

            _time_delta = self.bot.convert_duration(lookback)
            seconds = _time_delta.total_seconds()

            msg_stats = await self.bot.mongo_db.get_msg_stats(seconds)
            vc_stats = await self.bot.mongo_db.get_vc_stats(seconds)

            sorted_stats = self.get_sorted_stats(msg_stats, vc_stats)

            mc = sorted_stats.get('cmc' if isinstance(target, GuildChannel) else 'umc', {})
            vt = sorted_stats.get('cvt' if isinstance(target, GuildChannel) else 'uvt', {})

            try:
                m_rank, m_count = f'#{list(mc).index(target.id) + 1}', mc[target.id]
            except ValueError:
                m_rank, m_count = 'N/A', 0
            try:
                v_rank, v_time = f'#{list(vt).index(target.id) + 1}', vt[target.id]
            except ValueError:
                v_rank, v_time = 'N/A', 0

            since_dt = utcnow() - _time_delta
            avatar = self.bot.user.avatar
            author = ('Channel' if isinstance(target, GuildChannel) else 'User') + ' Statistics'
            guild = self.bot.guild
            url = target.avatar or target.default_avatar if isinstance(target, (User, Member)) else guild.icon or avatar

            stats_embed = Embed(color=Color.blue(), title=target, description=f'**Since {format_dt(since_dt, "F")}**')
            stats_embed.set_author(name=author, icon_url=avatar)
            stats_embed.set_thumbnail(url=url)
            stats_embed.set_footer(text=f'Try out {self.bot.command_prefix}topstats to view the top rankings!')

            stats_embed.add_field(
                name=f'Total Messages ({m_rank}):',
                value=f'> **`{m_count:,}`**',
                inline=False)
            stats_embed.add_field(
                name=f'VC Activity ({v_rank}):',
                value=f'> **`{timedelta(seconds=round(v_time))}`**',
                inline=False)

        await ctx.send(embed=stats_embed)

    @commands.command(
        name='modstats',
        aliases=[],
        description='View the moderations statistics of a user.',
        extras={'requirement': 5}
    )
    async def modstats(self, ctx: CustomContext, user: User = None, lookback: str = '28d'):
        async with ctx.typing():
            user = user or ctx.author

            _time_delta = self.bot.convert_duration(lookback)
            seconds = _time_delta.total_seconds()
            now = utcnow()

            try:
                modlogs = await self.bot.mongo_db.search_modlog(mod_id=user.id)
                modlogs = [modlog for modlog in modlogs if modlog.created > now.timestamp() - seconds]
            except ModLogNotFound:
                modlogs = []

            avatar = self.bot.user.avatar
            since_dt = now - _time_delta

            modstats_embed = Embed(colour=Color.blue(), title=user, description=f'**Since {format_dt(since_dt, "F")}**')
            modstats_embed.set_author(name='User Moderation Statistics', icon_url=avatar)
            modstats_embed.set_thumbnail(url=user.avatar or self.bot.guild.icon or avatar)

            for stat_type in self.MOD_STAT_TYPES:
                modstats_embed.add_field(
                    name=self.MOD_STAT_TYPES[stat_type],
                    value=f'> **`{len([modlog for modlog in modlogs if modlog.type == stat_type]):,}`**')

        await ctx.send(embed=modstats_embed)


async def setup(bot: CustomBot):
    await bot.add_cog(UserStatistics(bot))
