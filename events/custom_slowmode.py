from datetime import timedelta

from discord.ext import commands
from discord.utils import utcnow, format_dt
from discord import Message

from main import CustomBot


class CustomSlowmode(commands.Cog):

    def __init__(self, bot: CustomBot) -> None:
        self.bot: CustomBot = bot

        self.channels: dict[int, timedelta] = {
            1039886236602601512: timedelta(seconds=86400)
        }

    @commands.Cog.listener(name="on_message")
    async def enforce_slowmode(self, message: Message) -> None:
        channel, author = message.channel, message.author

        if channel.id not in self.channels:
            return
        elif author.bot:
            return
        elif await self.bot.member_clearance(author) > 0:
            return

        cooldown = self.channels[channel.id]

        async for old_message in channel.history(limit=None, after=utcnow() - cooldown):
            if old_message == message:
                continue
            elif message.author == old_message.author:
                await message.delete()
                await channel.send(
                    f'*{author.mention}, you are on cooldown until {format_dt(old_message.created_at + cooldown)}!*',
                    delete_after=5
                )
                break


async def setup(bot: CustomBot) -> None:
    await bot.add_cog(CustomSlowmode(bot))
