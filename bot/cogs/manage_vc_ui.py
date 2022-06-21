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
                 custom_id: str = None,
                 **kwargs
                 ):
        super().__init__(
            label=label,
            emoji=emoji,
            style=discord.ButtonStyle.url if url else style,
            custom_id=custom_id,
            **kwargs
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
    def __init__(self,
                 bot_: PVCBot,
                 channel_id: int,
                 timeout: float | None,
                 allow_ownership: bool = False
                 ):
        self.bot = bot_
        super(UIView, self).__init__(timeout=timeout)
        self.channel_id = channel_id
        self.channel = self.bot.get_channel(self.channel_id)
        cur = self.bot.con.get(channel_id=self.channel_id)
        if cur.rowcount:
            self.owner_id = cur.fetchone()[1]

        self.add_item(Button(
            label="Lock",
            callback=self.toggle_vc_state,
            custom_id=f"lock-{channel_id}"
        ))
        self.add_item(Button(
            label="Rename",
            callback=self.change_vc_name,
            custom_id=f"rename-{channel_id}"
        ))

        self.add_item(Button(
            label="Claim",
            callback=self.transfer_ownership,
            custom_id=f"claim-{channel_id}",
            disabled=not allow_ownership
        ))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.custom_id == f'claim-{self.channel_id}' or interaction.user.id == self.owner_id:
            return True
        await interaction.response.send_message(f"Only <@{self.owner_id}> can change the Settings", ephemeral=True)

    async def change_vc_name(self, interaction: discord.Interaction):
        await interaction.response.send_modal(NewNameInputModal(title="Rename VC", view=self))

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

    async def transfer_ownership(self, interaction: discord.Interaction):
        self.bot.con.insert(
            user_id=interaction.user.id,
            channel_id=interaction.channel_id,
            update='user_id'
        )
        self.owner_id = interaction.user.id
        await interaction.response.send_message(f"{interaction.user.mention} is the new owner of {interaction.channel}")
        self.children[2].disabled = True
        await interaction.message.edit(view=self)


class ManageUI(commands.Cog):
    def __init__(self, bot_: PVCBot):
        self.bot = bot_

    def get_view(self, channel_id: int, timeout: float | None = 180) -> UIView:
        return UIView(self.bot, channel_id, timeout)

    async def update_ui(self, channel_id: int, allow_ownership: bool = True):
        msg = await self.bot.get_channel(channel_id).history(oldest_first=True, limit=1).next()
        view = UIView(self.bot, channel_id=channel_id, timeout=None, allow_ownership=allow_ownership)
        await msg.edit(view=view)


def setup(bot: PVCBot):
    bot.add_cog(ManageUI(bot))


