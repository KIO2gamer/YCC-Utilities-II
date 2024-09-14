from discord.ui import (
    View,
    Button
)
from discord import (
    HTTPException,
    Interaction,
    Embed,
    Color,
    Role
)


class RoleButton(Button):

    def __init__(self, role: Role):
        super().__init__(label=role.name, emoji='<:role:1014718526075961374>', custom_id=f'r{role.id}')

        self.role = role

    async def callback(self, interaction: Interaction) -> None:
        # noinspection PyUnresolvedReferences
        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            if self.role in interaction.user.roles:
                await interaction.user.remove_roles(self.role)
                msg = f'*{self.role.mention} removed.*'
            else:
                await interaction.user.add_roles(self.role)
                msg = f'*{self.role.mention} added.*'
            color = Color.green()

        except (HTTPException, AttributeError):
            msg = '❌ Something went wrong, please contact a staff member.'
            color = Color.red()

        callback_embed = Embed(color=color, description=msg)
        await interaction.followup.send(embed=callback_embed)


class RoleView(View):

    def __init__(self, roles: list[Role]):
        super().__init__(timeout=None)

        for role in roles:
            if len(self.children) <= 25:
                self.add_item(RoleButton(role))
