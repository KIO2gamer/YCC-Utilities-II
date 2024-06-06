from asyncio import sleep
from discord.ext import commands
from discord import Message

from main import CustomBot


"""
Custom slow mode enforcer using channel permission overwrites.

Note: This was very quickly and shoddily put together.

If you're reading this code and thinking about making something similar, do a better job of it than I have.
"""


class CustomSlowmode(commands.Cog):

    def __init__(self, bot: CustomBot) -> None:
        self.bot: CustomBot = bot

        self.duration: int = 86400
        self.channel_id: int = 1039886236602601512

    @commands.Cog.listener(name="on_message")
    async def enforce_slowmode(self, message: Message) -> None:
        author = message.author
        channel = message.channel
        clearance = await self.bot.member_clearance(author)

        if channel.id != self.channel_id:
            return
        elif clearance:
            return
        elif author.bot:
            return

        await channel.set_permissions(author, send_messages=False)
        await sleep(self.duration)
        await channel.set_permissions(author, send_messages=None)


async def setup(bot: CustomBot) -> None:
    await bot.add_cog(CustomSlowmode(bot))
