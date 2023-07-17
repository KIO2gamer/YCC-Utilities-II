from discord.ext import commands

from main import CustomBot
from core.context import CustomContext


class MiscellaneousCommands(commands.Cog):

    def __init__(self, bot: CustomBot):
        self.bot = bot


async def setup(bot: CustomBot):
    await bot.add_cog(MiscellaneousCommands(bot))
