from discord import Embed


class EmbedField:

    def __init__(self, **kwargs):
        self.name: str = kwargs.get('name', 'Name')
        self.text: str = kwargs.get('text', 'Text')
        self.inline: bool = kwargs.get('inline', False)

    def __len__(self):
        return len(self.name) + len(self.text)


class CustomEmbed(Embed):

    def append_field(self, field: EmbedField):
        self.add_field(name=field.name, value=field.text, inline=field.inline)

    def reverse_fields(self):
        try:
            self._fields.reverse()
        except AttributeError:
            pass
