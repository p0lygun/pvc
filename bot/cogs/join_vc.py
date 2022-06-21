import discord
from discord.ext import commands
from loguru import logger

from ..bot import PVCBot
from .manage_vc_ui import ManageUI


class JoinHandler(commands.Cog):
    def __init__(self, bot_: PVCBot):
        self.bot = bot_
        self.ui_manager = ManageUI(self.bot)

    @commands.Cog.listener()
    async def on_voice_state_update(self,
                                    member: discord.Member,
                                    before: discord.VoiceState,
                                    after: discord.VoiceState
                                    ):
        if after.channel is not None:
            cid = after.channel.id
            with self.bot.con.get_vc_data(channel_id=cid) as cur:
                # if joined a main channel
                if cur.rowcount:
                    type_ = cur.fetchone()[0]
                    logger.debug(type_)
                    if type_ == "VC-NAME":
                        logger.debug("Creating New VC with type VC-NAME")
                        vc_name = after.channel.name
                    else:
                        vc_name = str(member)

                    tmp_vc = await member.guild.create_voice_channel(
                        name=vc_name,
                        overwrites=after.channel.overwrites,
                        rtc_region=after.channel.rtc_region,
                        user_limit=after.channel.user_limit,
                        category=after.channel.category
                    )
                    await tmp_vc.set_permissions(member, manage_channels=True)

                    await member.move_to(tmp_vc)

                    with self.bot.con.get(user_id=member.id) as cur:
                        vc_id = None
                        if cur.rowcount:
                            vc_id = cur.fetchone()[0]

                    self.bot.con.insert(member.id, tmp_vc.id)
                    if vc_id is not None and vc_id != tmp_vc.id:
                        old_vc = member.guild.get_channel(vc_id)
                        if old_vc:
                            members = old_vc.members
                            if len(members) == 0:
                                logger.debug(f"Old VC for {member} with no members found.. Deleting")
                                await old_vc.delete()
                            else:
                                roles_dict = {member_: member_.top_role for member_ in members}
                                max_user = next(iter(roles_dict))
                                for m, r in roles_dict.items():
                                    if r > roles_dict[max_user]:
                                        max_user = m
                                self.bot.con.insert(user_id=max_user.id, channel_id=vc_id)
                                await old_vc.send(f"Ownership of this Channel is Transferred to {max_user.mention}")
                                await self.ui_manager.update_ui(vc_id, allow_ownership=False)
                    view = self.ui_manager.get_view(tmp_vc.id, timeout=None)
                    msg = await tmp_vc.send(
                        content=f"Manage VC settings here {member.mention}",
                        view=view
                    )
                    view.msg = msg
                else:
                    cur = self.bot.con.get(user_id=member.id)
                    info = cur.fetchone()
                    if cur.rowcount and info[0] == after.channel.id:
                        await self.ui_manager.update_ui(info[0], allow_ownership=False)

        if after.channel is None:
            with self.bot.con.get(user_id=member.id) as cur:
                if cur.rowcount:
                    await self.ui_manager.update_ui(cur.fetchone()[0])
        if before.channel is not None:
            with self.bot.con.get(channel_id=before.channel.id) as cur:
                if cur.rowcount:
                    if len(before.channel.members) == 0:
                        await before.channel.delete()
                        self.bot.con.delete(channel_id=before.channel.id)


def setup(bot: PVCBot):
    bot.add_cog(JoinHandler(bot_=bot))
