from typing import Optional
from weakref import ref

from discord.abc import GuildChannel
from discord import HTTPException, Role

# Metadata contains user-configurable values that control how the bot behaves.
# This subclass exists simply to help keep our code more coherent later on.


class MetaData(dict):

    def __init__(self, bot, **kwargs):
        super().__init__(**kwargs)
        self._bot = ref(bot)

    @property
    def bot(self):
        return self._bot()

    async def get_channel(self, channel_type: str) -> Optional[GuildChannel]:
        _id = self.get(channel_type + '_channel', 0)
        try:
            return self.bot.guild.get_channel(_id) or await self.bot.guild.fetch_channel(_id)
        except HTTPException:
            return

    async def get_role(self, role_type: str) -> Optional[Role]:
        _id = self.get(role_type + '_role', 0)
        try:
            _coro = self.bot.guild.fetch_roles
            return self.bot.guild.get_role(_id) or next((role for role in await _coro() if role.id == _id), None)
        except HTTPException:
            return

    @property
    def domain_bl(self) -> list[str]:
        return self.get('domain_bl', [])

    @property
    def domain_wl(self) -> list[str]:
        return self.get('domain_wl', [])

    @property
    def appeal_bl(self) -> list[int]:
        return self.get('appeal_bl', [])

    @property
    def trivia_bl(self) -> list[int]:
        return self.get('trivia_bl', [])

    @property
    def suggest_bl(self) -> list[int]:
        return self.get('suggest_bl', [])

    @property
    def event_ignored_roles(self) -> list[int]:
        return self.get('event_ignored_roles', [])

    @property
    def event_ignored_channels(self) -> list[int]:
        return self.get('event_ignored_channels', [])

    @property
    def auto_mod_ignored_roles(self) -> list[int]:
        return self.get('auto_mod_ignored_roles', [])

    @property
    def auto_mod_ignored_channels(self) -> list[int]:
        return self.get('auto_mod_ignored_channels', [])

    @property
    def activity(self) -> Optional[str]:
        return self.get('activity')

    @property
    def welcome_msg(self) -> Optional[str]:
        return self.get('welcome_msg', 'Welcome to the server <member>!')
