import discord
from discord.ext import commands
from loguru import logger


from ..bot import PVCBot


def slug_label(label: str):
    return label.replace(' ', '').strip().lower()


class Button(discord.ui.Button):
    def __init__(self,
                 label: str,
                 emoji: discord.PartialEmoji = None,
                 url: str = None,
                 callback: callable = None,
                 style: discord.ButtonStyle = discord.ButtonStyle.primary,
                 custom_id: str=None,
                 ):
        super().__init__(
            label=label,
            emoji=emoji,
            style=discord.ButtonStyle.url if url else style,
            custom_id=custom_id
        )
        self.callback_ = callback

    async def callback(self, interaction: discord.Interaction):
        if self.callback_:
            await self.callback_(interaction)


class NewNameInputModal(discord.ui.Modal):
    def __init__(self, view: discord.ui.View, *args, **kwargs):
        super().__init__(
            discord.ui.InputText(
                label="Enter new VC Name",
                style=discord.InputTextStyle.short,
            ),
            *args,
            **kwargs,
        )
        self.view = view

    async def callback(self, interaction: discord.Interaction):
        new_name = self.children[0].value
        if new_name:
            await interaction.channel.edit(name=new_name)
        await interaction.response.defer()


class UIView(discord.ui.View):
    def __init__(self, bot_: PVCBot, channel_id: int, timeout: float):
        self.bot = bot_
        super(UIView, self).__init__(timeout=timeout)
        self.channel_id = channel_id
        self.channel = self.bot.get_channel(self.channel_id)
        cur = self.bot.con.get(channel_id=self.channel_id)
        logger.debug(cur.rowcount)
        if cur.rowcount:
            self.owner_id = cur.fetchone()[1]

        self.add_item(Button(
            label="Lock VC",
            callback=self.toggle_vc_state,
            custom_id=f"toggle-lock-{channel_id}"
        ))
        self.add_item(Button(
            label="Change VC Name",
            callback=self.change_vc_name,
            custom_id=f"change-vc-name-{channel_id}"
        ))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.owner_id:
            return True
        await interaction.response.send_message(f"Only <@{self.owner_id}> can change the Settings", ephemeral=True)

    async def change_vc_name(self, interaction: discord.Interaction):
        await interaction.response.send_modal(NewNameInputModal(title="Change VC name", view=self))

    async def toggle_vc_state(self, interaction: discord.Interaction):
        await interaction.response.defer()
        vc = self.channel
        c = vc.overwrites_for(interaction.guild.default_role).connect
        btn = self.children[0]
        if c is None or c:
            overwrites = discord.PermissionOverwrite(connect=False)
            btn.label = "Unlock VC"
        else:
            overwrites = discord.PermissionOverwrite(connect=True)
            btn.label = "Lock VC"

        await vc.set_permissions(interaction.guild.default_role, overwrite=overwrites)
        await interaction.message.edit(view=self)


class ManageUI(commands.Cog):
    def __init__(self, bot_: PVCBot):
        self.bot = bot_

    def get_view(self, channel_id: int, timeout: float | None = 180) -> UIView:
        return UIView(self.bot, channel_id, timeout)


def setup(bot: PVCBot):
    bot.add_cog(ManageUI(bot))


