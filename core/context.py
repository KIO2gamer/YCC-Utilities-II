from discord.ext import commands


class CustomContext(commands.Context):

    async def author_clearance(self) -> int:
        return await self.bot.member_clearance(self.author)
