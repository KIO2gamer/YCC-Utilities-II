from datetime import timedelta

from discord.utils import utcnow
from discord.ext import commands
from discord import (
    User,
    HTTPException
)

from main import CustomBot
from core.embed import EmbedField
from core.modlog import ModLogEntry
from core.context import CustomContext
from core.errors import ModLogNotFound, DurationError
from components.paginator import Paginator


class ModLogCommands(commands.Cog):

    _flag_map = {
        '-dc': 'decancer',
        '-mn': 'modnick',
        '-n': 'note',
        '-dm': 'dm',
        '-w': 'warn',
        '-k': 'kick',
        '-m': 'mute',
        '-b': 'ban',
        '-cb': 'channel_ban',
        '-um': 'unmute',
        '-ub': 'unban',
        '-cub': 'channel_unban'
    }

    _type_map = {
        'modnick': 'Nickname Moderation',
        'dm': 'Direct Message',
        'channel_ban': 'Channel Ban',
        'channel_unban': 'Channel Unban'
    }

    def __init__(self, bot: CustomBot):
        self.bot = bot

    def _filter_modlogs(self, modlogs: list[ModLogEntry], flags: list[str]) -> list[ModLogEntry]:
        flags = [] if flags == [''] else flags

        if flags:
            filtered_modlogs = []
            for modlog in modlogs:
                for flag in flags:
                    _type = self._flag_map.get(flag)
                    if _type and _type == modlog.type:
                        filtered_modlogs.append(modlog)
                        break
        else:
            filtered_modlogs = modlogs

        if not filtered_modlogs:
            raise ModLogNotFound()

        return filtered_modlogs

    def _modlogs_to_fields(self, modlogs: list[ModLogEntry], **kwargs) -> list[EmbedField]:
        fields = []

        for modlog in modlogs:
            _id = f'Case {modlog.id} {"(Ongoing)" if modlog.active is True else ""}'
            _mod = f'**Moderator:** <@{modlog.mod_id}>\n' if kwargs.get('mod') is True else ''
            _user = f'**User:** <@{modlog.user_id}>\n' if kwargs.get('user') is True else ''
            _channel = f'**Channel:** <#{modlog.channel_id}>\n' if modlog.channel_id else ''
            _type = f'**Type:** {self._type_map.get(modlog.type, modlog.type.capitalize())}\n'
            _reason = f'**Reason:** {modlog.reason} - <t:{modlog.created}:F>\n' if kwargs.get('reason') is True else ''
            _duration = \
                f'**Duration:** ' \
                f'`{timedelta(seconds=modlog.duration) if modlog.duration < self.bot.perm_duration else "permanent"}' \
                f'`\n' if modlog.duration else ''
            _until = f'**Expires:** <t:{modlog.until}:F>' if kwargs.get('until') is True else ''
            _received = f'**Received:** `{modlog.received}`\n' if kwargs.get('received') is True else ''
            _deleted = f'**Deleted:** `{modlog.deleted}`\n' if kwargs.get('deleted') is True else ''

            text = _user + _type + _channel + _mod + _reason + _duration + _until + _received + _deleted

            fields.append(EmbedField(name=_id, text=text))

        return fields

    @commands.command(
        name='mylogs',
        aliases=['ml'],
        description='Allows members to view their own modlogs history by sending a DM to the command author.',
        extras={'requirement': 0}
    )
    @commands.cooldown(1, 15)
    async def mylogs(self, ctx: CustomContext):
        try:
            modlogs = await self.bot.mongo_db.search_modlog(user_id=ctx.author.id, deleted=False)
            modlogs = [modlog for modlog in modlogs if modlog.type != 'note']
            modlogs.reverse()
        except ModLogNotFound:
            modlogs = []

        fields = self._modlogs_to_fields(modlogs, reason=True)
        embeds = self.bot.fields_to_embeds(
            fields,
            title=f'Your Modlogs - {self.bot.guild}',
            description='`No modlogs to be displayed.`' if not modlogs else None
        )

        try:
            message = await ctx.author.send(embed=embeds[0])
        except HTTPException:
            raise Exception('Please enable your DMs.')

        await message.edit(view=Paginator(ctx.author, message, embeds))
        await self.bot.good_embed(ctx, 'Done, check your DMs.')

    @commands.command(
        name='modlogs',
        aliases=['logs', 'history'],
        description='View the modlogs history of a specific user. Flags can be used to filter specific actions.',
        extras={'requirement': 1}
    )
    async def modlogs(self, ctx: CustomContext, user: User = None, *, flags: str = ''):
        user = user or ctx.author
        modlogs = await self.bot.mongo_db.search_modlog(user_id=user.id, deleted=False)
        filtered_modlogs = self._filter_modlogs(modlogs, flags.split(' '))
        filtered_modlogs.reverse()

        fields = self._modlogs_to_fields(filtered_modlogs, mod=True, reason=True, received=True)
        embeds = self.bot.fields_to_embeds(fields, title=f'Modlogs for {user.name}')
        for embed in embeds:
            embed.reverse_fields()

        message = await ctx.send(embed=embeds[0])
        await message.edit(view=Paginator(ctx.author, message, embeds))

    @commands.command(
        name='moderations',
        aliases=['activelogs', 'mds'],
        description='View a list of ongoing moderations.  Flags can be used to filter specific actions.',
        extras={'requirement': 1}
    )
    async def moderations(self, ctx: CustomContext, *, flags: str = ''):
        modlogs = await self.bot.mongo_db.search_modlog(active=True, deleted=False)
        filtered_modlogs = self._filter_modlogs(modlogs, flags.split(' '))
        filtered_modlogs.reverse()

        fields = self._modlogs_to_fields(filtered_modlogs, user=True, until=True)
        embeds = self.bot.fields_to_embeds(fields, title='Active Moderations')
        for embed in embeds:
            embed.reverse_fields()

        message = await ctx.send(embed=embeds[0])
        await message.edit(view=Paginator(ctx.author, message, embeds))

    @commands.command(
        name='case',
        aliases=['findcase'],
        description='Find a specific modlog entry by case ID.',
        extras={'requirement': 1}
    )
    async def case(self, ctx: CustomContext, case_id: int):
        modlogs = await self.bot.mongo_db.search_modlog(case_id=case_id, deleted=False)
        modlogs.reverse()

        fields = self._modlogs_to_fields(modlogs, user=True, mod=True, reason=True)
        embeds = self.bot.fields_to_embeds(fields)
        for embed in embeds:
            embed.reverse_fields()

        message = await ctx.send(embed=embeds[0])
        await message.edit(view=Paginator(ctx.author, message, embeds))

    @commands.command(
        name='reason',
        aliases=['r'],
        description='Edit the reason of an existing modlog.',
        extras={'requirement': 2}
    )
    async def reason(self, ctx: CustomContext, case_id: int, *, reason: str):
        modlog = await self.bot.mongo_db.update_modlog(_case_id=case_id, _deleted=False, reason=reason)
        await self.bot.good_embed(ctx, f'**Reason updated for case {modlog.id}:** {reason}')

    @commands.command(
        name='duration',
        aliases=['dur'],
        description='Edit the duration of an active modlog.',
        extras={'requirement': 3}
    )
    async def duration(self, ctx: CustomContext, case_id: int, duration: str):
        permanent = False
        try:
            _time_delta = self.bot.convert_duration(duration)
        except DurationError as error:
            if duration.lower() in 'permanent':
                permanent = True
                _time_delta = timedelta(seconds=self.bot.perm_duration)
            else:
                raise error
        seconds = _time_delta.total_seconds()

        if not 60 <= seconds <= 2419200:
            try:
                modlog = await self.bot.mongo_db.update_modlog(
                    _case_id=case_id, _type='ban', _active=True, _deleted=False, duration=seconds)
            except ModLogNotFound:
                modlog = await self.bot.mongo_db.update_modlog(
                    _case_id=case_id, _type='channel_ban', _active=True, _deleted=False, duration=seconds)
        else:
            modlog = await self.bot.mongo_db.update_modlog(
                _case_id=case_id, _active=True, _deleted=False, duration=seconds)

        if modlog.type == 'mute':
            try:
                member = await self.bot.guild.fetch_member(modlog.user_id)
            except HTTPException:
                pass
            else:
                new_muted_duration = timedelta(seconds=modlog.created + seconds - utcnow().timestamp())
                await member.timeout(new_muted_duration)

        duration_str = '`permanent`' if permanent is True else f'`{_time_delta}` (expires <t:{modlog.until}:R>)'
        await self.bot.good_embed(ctx, f'**Updated duration for case {case_id} to {duration_str}.**')

    @commands.command(
        name='delcase',
        aliases=['rmcase'],
        description='Deletes a modlog, making it invisible on most commands. Ongoing cases cannot be deleted.',
        extras={'requirement': 6}
    )
    async def delcase(self, ctx: CustomContext, case_id: int):
        try:
            deleted_modlog = await self.bot.mongo_db.update_modlog(
                _case_id=case_id, _deleted=False, _active=False, deleted=True)
        except ModLogNotFound:
            raise Exception(f'Modlog not found or could not be deleted as it is ongoing.')
        await self.bot.good_embed(ctx, f'**Case {deleted_modlog.id} deleted.**')

    @commands.command(
        name='restorecase',
        aliases=['rescase', 'rc'],
        description='Restores a modlog. This will reverse the effects of it being deleted.',
        extras={'requirement': 6}
    )
    async def restorecase(self, ctx: CustomContext, case_id: int):
        restored_modlog = await self.bot.mongo_db.update_modlog(_case_id=case_id, _deleted=True, deleted=False)
        await self.bot.good_embed(ctx, f'**Case {restored_modlog.id} restored.**')

    @commands.command(
        name='deletedlogs',
        aliases=['dellogs'],
        description='View the deleted modlogs of a specific user. Flags can be used to filter specific actions.',
        extras={'requirement': 6}
    )
    async def deletedlogs(self, ctx: CustomContext, user: User = None, *, flags: str = ''):
        user = user or ctx.author
        modlogs = await self.bot.mongo_db.search_modlog(user_id=user.id, deleted=True)
        filtered_modlogs = self._filter_modlogs(modlogs, flags.split(' '))
        filtered_modlogs.reverse()

        fields = self._modlogs_to_fields(filtered_modlogs, mod=True, reason=True, received=True)
        embeds = self.bot.fields_to_embeds(fields, title=f'Deleted Modlogs for {user.name}')
        for embed in embeds:
            embed.reverse_fields()

        message = await ctx.send(embed=embeds[0])
        await message.edit(view=Paginator(ctx.author, message, embeds))


async def setup(bot: CustomBot):
    await bot.add_cog(ModLogCommands(bot))
