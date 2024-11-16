import logging
from copy import copy
from datetime import timedelta

from discord.ext import commands
from discord import (
    HTTPException,
    Message,
    Embed,
    Color
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

                response = faq.get('response')
                for user in message.mentions:
                    response = f'{user.mention} {response}'

                try:
                    await message.delete()
                    await message.channel.send(response)
                except HTTPException as error:
                    logging.error(f'Error while responding to FAQ - {error}')
                return

        for custom in await self.bot.mongo_db.fetch_commands('custom'):

            custom_name = custom.get('shortcut', '')
            custom_invoke = prefix + custom_name
            if content_lower == custom_invoke or content_lower.startswith(custom_invoke + ' '):

                action = custom.get('action', '')
                reason = custom.get('reason', '')
                duration = custom.get('duration', 0)
                duration_str = f'{duration}s' if duration else ''

                message_copy = copy(message)
                try:
                    user = content.split(' ')[1]
                    message_copy.content = f'{prefix}{action} {user} {duration_str} {reason}'
                except IndexError:
                    help_embed = Embed(
                        color=Color.blue(),
                        title=f'{prefix}{custom_name} Command',
                        description=f'This is a user-created custom moderation command. '
                                    f'{action.capitalize()}s the specified user/member '
                                    f'{"for the pre-set duration" if duration_str else ""} '
                                    f'and creates a new entry in their modlogs history.')
                    help_embed.set_author(name='Help Menu', icon_url=self.bot.user.avatar)
                    help_embed.set_footer(text=f'Use {self.bot.command_prefix}help to view all commands.')

                    help_embed.add_field(name='Reason:', value=f'`{reason}`', inline=False)
                    if duration_str:
                        help_embed.add_field(
                            name=f'{"Cleanse " if action == "softban" else ""}Duration:',
                            value=f'`{"permanent" if duration == self.bot.perm_duration else timedelta(seconds=duration)}`',
                            inline=False)
                    help_embed.add_field(name='Usage:', value=f'`{prefix}{custom_name} <user>`', inline=False)
                    help_embed.add_field(name='Aliases:', value='`None`', inline=False)

                    return await message.channel.send(embed=help_embed)

                ctx = await self.bot.get_context(message_copy, cls=CustomContext)
                return await self.bot.invoke(ctx)


async def setup(bot: CustomBot):
    await bot.add_cog(CustomCommandEvents(bot))
