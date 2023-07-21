from typing import Mapping, Optional

from discord.ext import commands
from discord import (
    Embed,
    Color
)


class CustomHelpCommand(commands.HelpCommand):

    COG_NAME_DICT = {
        'ConfigurationCommands': 'Configuration Commands',
        'InformationCommands': 'Information Commands',
        'MiscellaneousCommands': 'Miscellaneous Commands',
        'ModerationCommands': 'Moderation Commands',
        'ModLogsCommands': 'Modlogs Commands',
        'TokenHandler': 'Currency Commands',
        'UserStatistics': 'User Statistics',
    }

    async def send_bot_help(self, mapping: Mapping[Optional[commands.Cog], list[commands.Command]]) -> None:
        avatar = self.context.bot.user.avatar or self.context.bot.user.default_avatar
        prefix = self.context.bot.command_prefix

        bot_help_embed = Embed(color=Color.blue(), title='All Commands')
        bot_help_embed.set_author(name='Help Menu', icon_url=avatar)
        bot_help_embed.set_footer(text=f'Use {prefix}help <command> for more info on a single command.')

        for cog in mapping:
            if cog and cog.get_commands() and cog.qualified_name in self.COG_NAME_DICT:
                cog_commands = [command.qualified_name for command in cog.get_commands()]
                cog_commands_str = f'`{", ".join(cog_commands)}`' if cog_commands else '`No Commands Found`'
                bot_help_embed.add_field(
                    name=self.COG_NAME_DICT[cog.qualified_name],
                    value=cog_commands_str,
                    inline=False
                )

        await self.context.send(embed=bot_help_embed)

    async def send_command_help(self, command: commands.Command) -> None:
        # noinspection PyUnresolvedReferences
        await self.context.bot.send_command_help(self.context, command)

    async def send_error_message(self, error: str) -> None:
        # noinspection PyUnresolvedReferences
        await self.context.bot.bad_embed(self.context, f'❌ {error}')
