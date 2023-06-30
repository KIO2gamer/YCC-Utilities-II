from datetime import timedelta

from discord.ext import commands
from discord import (
    User
)

from main import CustomBot
from core.embed import EmbedField
from core.modlog import ModLogEntry
from core.errors import ModLogNotFound
from core.context import CustomContext
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

    def _filter_modlogs(self, modlogs: list[ModLogEntry], flags: list[str] = None) -> list[ModLogEntry]:
        flags = flags or []
        filtered_modlogs = []

        for modlog in modlogs:
            for flag in flags:
                if flag not in self._flag_map or self._flag_map[flag] == modlog.type:
                    filtered_modlogs.append(modlog)
                    break

        if not filtered_modlogs:
            raise ModLogNotFound()

        return filtered_modlogs

    def _modlogs_to_fields(self, modlogs: list[ModLogEntry], **kwargs) -> list[EmbedField]:
        fields = []

        for modlog in modlogs:
            _id = f'Case {modlog.id}'
            _mod = f'**Moderator:** <@{modlog.mod_id}>\n' if kwargs.get('mod') is True else ''
            _user = f'**User:** <@{modlog.user_id}>\n' if kwargs.get('user') is True else ''
            _channel = f'**Channel:** <#{modlog.channel_id}>\n' if modlog.channel_id else ''
            _type = f'**Type:** {self._type_map.get(modlog.type, modlog.type.capitalize())}\n'
            _reason = f'**Reason:** {modlog.reason} - <t:{modlog.created}:F>\n' if kwargs.get('reason') is True else ''
            _duration = f'**Duration:** `{timedelta(seconds=modlog.duration)}`\n' if modlog.duration else ''
            _received = f'**Received:** `{modlog.received}`\n' if kwargs.get('received') is True else ''
            _ongoing = f'**Ongoing:** `{not modlog.expired}`\n' if kwargs.get('ongoing') is True else ''
            _deleted = f'**Deleted:** `{modlog.deleted}`\n' if kwargs.get('deleted') is True else ''

            text = _user + _type + _channel + _mod + _reason + _duration + _received + _ongoing + _deleted

            fields.append(EmbedField(name=_id, text=text))

        return fields

    @commands.command(
        name='modlogs',
        aliases=['logs', 'history'],
        description='View the modlogs history of a specific user. Flags can be used to filter specific actions.',
        extras={'requirement': 1}
    )
    async def modlogs(self, ctx: CustomContext, user: User = None, *, flags: str = ''):
        user = user or ctx.author
        modlogs = await self.bot.mongo_db.search_modlog(user_id=user.id)
        filtered_modlogs = self._filter_modlogs(modlogs, flags=flags.split(' '))
        filtered_modlogs.reverse()

        fields = self._modlogs_to_fields(filtered_modlogs, mod=True, reason=True, received=True)
        embeds = self.bot.fields_to_embeds(fields, title=f'Modlogs for {user.name}')
        for embed in embeds:
            embed.reverse_fields()

        message = await ctx.send(embed=embeds[0])
        view = Paginator(ctx.author, message, embeds)
        await message.edit(view=view)


async def setup(bot: CustomBot):
    await bot.add_cog(ModLogCommands(bot))
