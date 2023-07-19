from typing import Literal
from datetime import timedelta

from discord.ext import commands
from discord.utils import utcnow, format_dt
from discord import (
    TextChannel,
    Embed,
    Color,
    Role,
    User
)

from main import CustomBot
from core.context import CustomContext
from core.embed import EmbedField
from components.paginator import Paginator
from components.giveaway import GiveawayView


class MiscellaneousCommands(commands.Cog):

    COMMAND_EXISTS = '`{0}` is already an existing command name/alias.'
    ACTIONS = Literal['warn', 'kick', 'mute', 'ban']

    def __init__(self, bot: CustomBot):
        self.bot = bot

    @staticmethod
    async def _check_role(ctx: CustomContext, role: Role):
        if role >= ctx.guild.me.top_role:
            raise Exception(f'Bot missing permission to edit {role.mention}.')
        elif role >= ctx.author.top_role:
            raise Exception(f'Missing permission to edit {role.mention}.')
        elif role in (ctx.guild.premium_subscriber_role, ctx.guild.default_role):
            raise Exception(f'{role.mention} is an invalid role.')

    async def _send_roles(self, ctx: CustomContext, role_type: str):
        special_roles = await self.bot.mongo_db.fetch_roles(role_type)
        if not special_roles:
            raise Exception(f'No {role_type} roles found.')

        fields = [EmbedField(
            name=f'{role_type.capitalize()} Role',
            text=f'**User:** <@{special_role.get("user_id", 0)}> **(ID: `{special_role.get("user_id", 0)}`)**\n'
                 f'**Role:** <@&{special_role.get("role_id", 0)}> **(ID: `{special_role.get("role_id", 0)}`)**')
            for special_role in special_roles]
        embeds = self.bot.fields_to_embeds(fields, title=f'{role_type.capitalize()} Roles')

        message = await ctx.send(embed=embeds[0])
        await message.edit(view=Paginator(ctx.author, message, embeds))

    @commands.command(
        name='addfaq',
        aliases=[],
        description='Adds an FAQ command to the bot, which will send a simple response message when invoked.',
        extras={'requirement': 6}
    )
    async def addfaq(self, ctx: CustomContext, shortcut: str, *, response: str):
        shortcut = shortcut.lower()
        if shortcut in await self.bot.command_names():
            raise Exception(self.COMMAND_EXISTS.format(shortcut))
        await self.bot.mongo_db.insert_command(
            'faq',
            shortcut=shortcut,
            response=response
        )
        prefix = self.bot.command_prefix
        await self.bot.good_embed(ctx, f'*FAQ command added! Use `{prefix}{shortcut}` to try it out.*')

    @commands.command(
        name='delfaq',
        aliases=[],
        description='Deletes an existing FAQ command.',
        extras={'requirement': 6}
    )
    async def delfaq(self, ctx: CustomContext, shortcut: str):
        shortcut = shortcut.lower()
        result = await self.bot.mongo_db.delete_command('faq', shortcut=shortcut)
        if result is False:
            raise Exception(f'FAQ `{shortcut}` not found.')
        await self.bot.good_embed(ctx, f'*FAQ command deleted: `{shortcut}`.*')

    @commands.command(
        name='faqs',
        aliases=[],
        description='Displays all user-created FAQ commands.',
        extras={'requirement': 1}
    )
    async def faqs(self, ctx: CustomContext):
        faqs = await self.bot.mongo_db.fetch_commands('faq')
        prefix = self.bot.command_prefix
        if not faqs:
            raise Exception(f'No FAQ commands found. Use `{prefix}addfaq` to create one!')

        fields = [EmbedField(
            name=f'{prefix}{faq.get("shortcut")}',
            text=faq.get('response'))
            for faq in faqs]
        embeds = self.bot.fields_to_embeds(fields, title='FAQ Commands')

        message = await ctx.send(embed=embeds[0])
        await message.edit(view=Paginator(ctx.author, message, embeds))

    @commands.command(
        name='addcustom',
        aliases=[],
        description='Creates a new custom moderation command, which acts as a shortcut for moderation commands.',
        extras={'requirement': 6}
    )
    async def addcustom(self, ctx: CustomContext, action: ACTIONS, shortcut: str, duration: str, *, reason: str):
        shortcut = shortcut.lower()
        if shortcut in await self.bot.command_names():
            raise Exception(self.COMMAND_EXISTS.format(shortcut))
        elif action in ('warn', 'kick'):
            seconds = None
        else:
            _time_delta = self.bot.convert_duration(duration)
            seconds = round(_time_delta.total_seconds())
        await self.bot.mongo_db.insert_command(
            'custom',
            action=action,
            shortcut=shortcut,
            duration=seconds,
            reason=reason
        )
        prefix = self.bot.command_prefix
        await self.bot.good_embed(ctx, f'*Custom command created! Use `{prefix}{shortcut}` to try it out.*')

    @commands.command(
        name='delcustom',
        aliases=[],
        description='Deletes an existing custom command.',
        extras={'requirement': 6}
    )
    async def delcustom(self, ctx: CustomContext, shortcut: str):
        shortcut = shortcut.lower()
        result = await self.bot.mongo_db.delete_command('custom', shortcut=shortcut)
        if result is False:
            raise Exception(f'Custom command `{shortcut}` not found.')
        await self.bot.good_embed(ctx, f'*Custom command deleted: `{shortcut}`.*')

    @commands.command(
        name='customs',
        aliases=[],
        description='Displays all user-created custom commands.',
        extras={'requirement': 1}
    )
    async def customs(self, ctx: CustomContext):
        customs = await self.bot.mongo_db.fetch_commands('custom')
        prefix = self.bot.command_prefix
        if not customs:
            raise Exception(f'No custom commands found. Use `{prefix}addcustom` to create one!')

        fields = [EmbedField(
            name=f'{prefix}{custom.get("shortcut")}',
            text=f'**Type:** `{custom.get("action")}`\n'
                 f'**Duration:** `{timedelta(seconds=custom.get("duration")) if custom.get("duration") else None}`\n'
                 f'**Reason:** {custom.get("reason")}')
            for custom in customs]
        embeds = self.bot.fields_to_embeds(fields, title='Custom Commands')

        message = await ctx.send(embed=embeds[0])
        await message.edit(view=Paginator(ctx.author, message, embeds))

    @commands.command(
        name='addcustomrole',
        aliases=[],
        description='Sets up a custom role for the user. The user can then edit their role with `editcustomrole`. '
                    'Note: the role will not be immediately applied upon command invocation.',
        extras={'requirement': 3}
    )
    @commands.bot_has_permissions(manage_roles=True)
    async def addcustomrole(self, ctx: CustomContext, user: User, role: Role):
        await self._check_role(ctx, role)

        custom_roles = await self.bot.mongo_db.fetch_roles('custom')
        for custom_role in custom_roles:
            user_id = custom_role.get('user_id', 0)
            role_id = custom_role.get('role_id', 0)
            if user.id == user_id:
                raise Exception(f'{user.mention} already has <@&{role_id}> as their custom role.')
            elif role.id == custom_role.get('role_id'):
                raise Exception(f'{role.mention} is already assigned as a custom role to <@{user_id}>.')

        await self.bot.mongo_db.insert_role('custom', user_id=user.id, role_id=role.id)
        await self.bot.good_embed(ctx, f'*{role.mention} assigned as {user.mention}\'s custom role.*')

    @commands.command(
        name='delcustomrole',
        aliases=[],
        description='Un-assigns a custom role from a user.',
        extras={'requirement': 3}
    )
    @commands.bot_has_permissions(manage_roles=True)
    async def delcustomrole(self, ctx: CustomContext, user: User):
        result = await self.bot.mongo_db.delete_role('custom', user_id=user.id)
        if result is False:
            raise Exception(f'{user.mention} does not have a custom role assigned.')
        await self.bot.good_embed(ctx, f'*Removed {user.mention}\'s custom role.*')

    @commands.command(
        name='customroles',
        aliases=[],
        description='Displays all custom roles and the users they are assigned to.',
        extras={'requirement': 1}
    )
    async def customroles(self, ctx: CustomContext):
        await self._send_roles(ctx, 'custom')

    @commands.command(
        name='addpersrole',
        aliases=[],
        description='Assigns a persistent role to a user. The role will then be re-added to the user if they re-join. '
                    'Note: the role will not be immediately applied upon command invocation.',
        extras={'requirement': 3}
    )
    @commands.bot_has_permissions(manage_roles=True)
    async def addpersrole(self, ctx: CustomContext, user: User, role: Role):
        await self._check_role(ctx, role)

        persistent_roles = await self.bot.mongo_db.fetch_roles('persistent')
        for persistent_role in persistent_roles:
            user_id = persistent_role.get('user_id', 0)
            role_id = persistent_role.get('role_id', 0)
            if (user.id, role.id) == (user_id, role_id):
                raise Exception(f'{role.mention} is already assigned as a persistent role for {user.mention}.')

        await self.bot.mongo_db.insert_role('persistent', user_id=user.id, role_id=role.id)
        await self.bot.good_embed(ctx, f'*Added {role.mention} as a persistent role for {user.mention}.*')

    @commands.command(
        name='delpersrole',
        aliases=[],
        description='Deletes a persistent role assignment.',
        extras={'requirement': 3}
    )
    @commands.bot_has_permissions(manage_roles=True)
    async def delpersrole(self, ctx: CustomContext, user: User, role: Role):
        result = await self.bot.mongo_db.delete_role('persistent', user_id=user.id, role_id=role.id)
        if result is False:
            raise Exception(f'{user.mention} does not have {role.mention} assigned as a persistent role.')
        await self.bot.good_embed(ctx, f'*Un-assigned {role.mention} as a persistent role for {user.mention}.*')

    @commands.command(
        name='persroles',
        aliases=[],
        description='Displays all persistent roles and the users they are assigned to.',
        extras={'requirement': 1}
    )
    async def persroles(self, ctx: CustomContext):
        await self._send_roles(ctx, 'persistent')

    @commands.command(
        name='editcustomrole',
        aliases=[],
        description='Allows users to edit their own custom role without having the `manage roles` permission.',
        extras={'requirement': 0}
    )
    @commands.cooldown(1, 30)
    @commands.bot_has_permissions(manage_roles=True)
    async def editcustomrole(self, ctx: CustomContext, new_hex: str, *, new_name: str):
        custom_roles = await self.bot.mongo_db.fetch_roles('custom')

        for custom_role in custom_roles:
            if custom_role.get('user_id') == ctx.author.id:
                role_id = custom_role.get('role_id', 0)
                role = ctx.guild.get_role(role_id)
                if isinstance(role, Role):
                    break
        else:
            raise Exception(f'Custom role not found/does not exist.')

        new_colour = int(new_hex.strip('#'), 16)
        await role.edit(name=new_name, color=new_colour)
        await self.bot.good_embed(ctx, f'*Successfully edited {role.mention}.*')

    @commands.command(
        name='giveaway',
        aliases=['gw'],
        description='Starts a giveaway. Note: giveaways are not persistent if the bot restarts.',
        extras={'requirement': 6}
    )
    async def giveaway(self, ctx: CustomContext, channel: TextChannel, winners: int, duration: str, *, prize: str):
        if not 0 < winners < 255:
            raise Exception('Number of winners out of range.')

        avatar = self.bot.user.avatar or self.bot.user.default_avatar
        _time_delta = self.bot.convert_duration(duration, allow_any_duration=True)
        seconds = round(_time_delta.total_seconds())
        now = utcnow()

        giveaway_embed = Embed(color=Color.blue(), title=prize.capitalize(), timestamp=now)
        giveaway_embed.set_author(name='Giveaway!', icon_url=avatar)
        giveaway_embed.set_thumbnail(url=self.bot.guild.icon or avatar)
        giveaway_embed.set_footer(text=f'{winners} Winner(s)')
        giveaway_embed.add_field(name='Ends:', value=f'**{format_dt(now + _time_delta, "F")}**', inline=False)
        giveaway_embed.add_field(name='Hosted By:', value=ctx.author.mention, inline=False)

        message = await channel.send(embed=giveaway_embed)
        view = GiveawayView(message, winners, seconds, prize)
        await message.edit(view=view)
        await view.expire()


async def setup(bot: CustomBot):
    await bot.add_cog(MiscellaneousCommands(bot))
