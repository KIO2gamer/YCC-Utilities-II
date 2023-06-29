from discord.ext import commands
from discord.utils import utcnow


class CustomContext(commands.Context):

    __enduring__ = ('mute', 'channel_ban', 'ban')

    async def author_clearance(self) -> int:
        return await self.bot.member_clearance(self.author)

    async def to_modlog_data(self, user_id: int, **kwargs) -> dict:
        _type = self.command.callback.__name__
        return {
            'case_id': await self.bot.mongo_db.generate_id(),
            'mod_id': self.author.id,
            'user_id': user_id,
            'channel_id': kwargs.get('channel_id', 0),
            'type': _type,
            'reason': kwargs.get('reason', 'No reason provided.'),
            'created': round(utcnow().timestamp()),
            'duration': kwargs.get('duration', 0),
            'received': kwargs.get('received', False),
            'active': _type in self.__enduring__,
            'deleted': False
        }


async def enforce_clearance(ctx: CustomContext) -> bool:
    return await ctx.author_clearance() >= ctx.command.extras.get('requirement', 0)
