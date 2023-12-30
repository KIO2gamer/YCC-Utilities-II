import logging

from discord.abc import GuildChannel
from discord.ext import commands
from discord import Message, HTTPException

from main import CustomBot


class VideoStickyMessage(commands.Cog):

    CHANNEL_ID = 1014709650890969188
    CONTENT = """
Try out </compare:1181916274167660624> and </feedback:1182594980271890462> using <@1048092058784649226>!
"""
    LIMIT = 3

    def __init__(self, bot: CustomBot):
        self.bot = bot

        self.count: int = 0
        self.previous_message: Message | None = None
        self.channel: GuildChannel | None = None

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        return

        if message.channel.id != self.CHANNEL_ID or message.author == self.bot.user:
            return

        self.count += 1
        if self.count < self.LIMIT:
            return

        self.count = 0

        try:
            self.channel = \
                self.channel or self.bot.get_channel(self.CHANNEL_ID) or await self.bot.fetch_channel(self.CHANNEL_ID)
        except HTTPException as error:
            logging.error(f'Failed to fetch channel (ID: {self.CHANNEL_ID}) to post sticky message - {error}')

        try:
            await self.previous_message.delete()
        except (HTTPException, AttributeError):
            pass

        try:
            self.previous_message = await self.channel.send(self.CONTENT)
        except HTTPException as error:
            logging.error(f'Failed to send sticky message in {self.channel} - {error}')


async def setup(bot: CustomBot):
    await bot.add_cog(VideoStickyMessage(bot))