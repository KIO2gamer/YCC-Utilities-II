from discord.ui import View, Button


class BanAppealView(View):

    def __init__(self, appeal_url: str):
        super().__init__()
        self.add_item(Button(label='Appeal Ban', url=appeal_url))
