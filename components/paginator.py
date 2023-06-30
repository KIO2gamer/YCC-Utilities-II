from typing import Union

from discord import ui
from discord import (
    User,
    Member,
    Message,
    Embed,
    Interaction,
    ButtonStyle,
    HTTPException
)


# noinspection PyUnusedLocal,PyUnresolvedReferences
class Paginator(ui.View):

    def __init__(self, author: Union[User, Member], message: Message, embeds: list[Embed]):
        super().__init__(timeout=120)
        self.author = author
        self.message = message
        self.embeds = embeds
        self.current_page = 1
        self.update_buttons()

    def update_buttons(self):
        for button in self.children:
            button.disabled = False
        self.firs_page.disabled = self.prev_page.disabled = self.current_page == 1
        self.next_page.disabled = self.last_page.disabled = self.current_page == len(self.embeds)

    async def edit_page(self, interaction: Interaction):
        await interaction.response.defer()
        self.update_buttons()
        await self.message.edit(embed=self.embeds[self.current_page - 1], view=self)

    @ui.button(label='<<')
    async def firs_page(self, interaction: Interaction, button):
        self.current_page = 1
        await self.edit_page(interaction)

    @ui.button(label='<', style=ButtonStyle.blurple)
    async def prev_page(self, interaction: Interaction, button):
        self.current_page -= 1
        await self.edit_page(interaction)

    @ui.button(label='>', style=ButtonStyle.blurple)
    async def next_page(self, interaction: Interaction, button):
        self.current_page += 1
        await self.edit_page(interaction)

    @ui.button(label='>>')
    async def last_page(self, interaction: Interaction, button):
        self.current_page = len(self.embeds)
        await self.edit_page(interaction)

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message('You can\'t use that.', ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        try:
            await self.message.edit(view=None)
        except HTTPException:
            pass
