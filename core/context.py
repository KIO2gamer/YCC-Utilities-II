from discord.ext import commands


class CustomContext(commands.Context):

    async def author_clearance(self) -> int:
        return await self.bot.member_clearance(self.author)


async def enforce_clearance(ctx: CustomContext) -> bool:
    return await ctx.author_clearance() >= ctx.command.extras.get('requirement', 0)
