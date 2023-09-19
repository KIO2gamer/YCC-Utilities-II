import logging

from discord.abc import GuildChannel
from discord.ext import commands
from discord import Message, HTTPException

from main import CustomBot


class VideoStickyMessage(commands.Cog):

    CHANNEL_ID = 1064918781719228456
    CONTENT = """
__**Important Offer, Earn $$$: Calling All Creators**__

**This new platform aims to be a better alternative to Patreon for content creators. Get an exclusive early invite to FYP.Fans, launching in 2 weeks. Brought to you by the minds behind Discords.com and FYP.bio.**

**What they are offering (IF you join the program):**

:white_small_square: **Lifetime 1% platform fee:** Keep 99% of your earnings! (Regular fee 7%). :money_with_wings: 
:white_small_square: Get Featured on Discords.com, FYP.Bio and FYP.Fans.  :mega:
:white_small_square: Priority support to get your page setup and profitable. :parrot: 

**Join Now:** https://discord.gg/SeFvJdzAM
"""
    LIMIT = 3

    def __init__(self, bot: CustomBot):
        self.bot = bot

        self.count: int = 0
        self.previous_message: Message | None = None
        self.channel: GuildChannel | None = None

    @commands.Cog.listener()
    async def on_message(self, message: Message):
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
