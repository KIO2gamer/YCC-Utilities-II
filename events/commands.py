import logging
from copy import copy

from discord.ext import commands
from discord import (
    HTTPException,
    Message
)

from main import CustomBot
from core.context import CustomContext


class CustomCommandEvents(commands.Cog):

    def __init__(self, bot: CustomBot):
        self.bot = bot

    @commands.Cog.listener(name='on_message')
    async def handle_custom_commands(self, message: Message):
        content = message.content
        prefix = self.bot.command_prefix
        if not content or not message.guild or message.guild.id != self.bot.guild_id or message.author.bot:
            return
        elif not content.startswith(prefix) or not await self.bot.member_clearance(message.author):
            return

        content_lower = content.lower()

        for faq in await self.bot.mongo_db.fetch_commands('faq'):

            faq_invoke = prefix + faq.get('shortcut')
            if content_lower == faq_invoke or content_lower.startswith(faq_invoke + ' '):

                try:
                    await message.delete()
                    await message.channel.send(faq.get('response'))
                except HTTPException as error:
                    logging.error(f'Error while responding to FAQ - {error}')
                return

        for custom in await self.bot.mongo_db.fetch_commands('custom'):

            custom_invoke = prefix + custom.get('shortcut')
            if content_lower == custom_invoke or content_lower.startswith(custom_invoke + ' '):

                action = custom.get('action')
                reason = custom.get('reason')
                duration = custom.get('duration')
                duration = f'{duration}s' if duration else ''

                message_copy = copy(message)
                try:
                    user = content.split(' ')[1]
                    message_copy.content = f'{prefix}{action} {user} {duration} {reason}'
                except IndexError:
                    message_copy.content = f'{prefix}{action}'

                ctx = await self.bot.get_context(message_copy, cls=CustomContext)
                await self.bot.invoke(ctx)
                return


async def setup(bot: CustomBot):
    await bot.add_cog(CustomCommandEvents(bot))
