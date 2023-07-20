import logging

from discord.ext import commands
from discord import (
    HTTPException,
    Member
)

from main import CustomBot


class WelcomeListener(commands.Cog):

    def __init__(self, bot: CustomBot):
        self.bot = bot

    @commands.Cog.listener(name='on_member_join')
    async def welcome_members(self, member: Member):
        general = await self.bot.metadata.get_channel('general')
        if general:
            try:
                # noinspection PyUnresolvedReferences
                await general.send(self.bot.metadata.welcome_msg.replace('<member>', member.mention))
            except (HTTPException, AttributeError) as error:
                logging.error(f'Failed to send welcome message for {member} - {error}')


async def setup(bot: CustomBot):
    await bot.add_cog(WelcomeListener(bot))
