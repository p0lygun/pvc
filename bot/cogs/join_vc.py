import json

import discord
from discord.ext import commands
from loguru import logger

from ..bot import PVCBot
from .manage_vc_ui import ManageUI
from ..utils.helper import random_emoji
from ..libs.validtypes import ChannelNames


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
            with self.bot.con.get_vc_data(('type', 'name_format'), {'channel_id': cid}) as cur:
                # if joined a main channel
                if cur.rowcount:
                    name_format: str
                    type_, name_format = cur.fetchone()
                    if type_ == "VC-NAME":
                        vc_name = after.channel.name
                    elif type_ == ChannelNames.custom or type_ == ChannelNames.increment:
                        if name_format:
                            vc_name = name_format.replace(
                                "$user$", member.name
                            ).replace(
                                "$tag$",
                                str(member.discriminator)
                            ).replace(
                                "$rmoji$",
                                random_emoji()
                            ).replace(
                                "$self$",
                                after.channel.name
                            )
                            if type_ == ChannelNames.increment:
                                curr = self.bot.con.get(
                                    ('child_list',),
                                    {'parent_channel_id': cid},
                                    table="increment_vc_data"
                                )
                                if cur.rowcount:
                                    child_list = json.loads(curr.fetchone()[0])
                                    curr.close()
                                    if before.channel is not None and before.channel.id in child_list:
                                        if len(before.channel.members) == 0:
                                            child_list[child_list.index(before.channel.id)] = 0
                                    try:
                                        index = child_list.index(0)
                                        to_append = False
                                    except ValueError:
                                        index = len(child_list)
                                        to_append = True
                                    if index != -1:
                                        vc_name = vc_name.replace("$index$", str(index + 1))

                        else:
                            vc_name = str(member)
                    else:
                        vc_name = str(member)

                    tmp_vc = await member.guild.create_voice_channel(
                        name=vc_name,
                        overwrites=after.channel.overwrites,
                        rtc_region=after.channel.rtc_region,
                        user_limit=after.channel.user_limit,
                        category=after.channel.category
                    )
                    if type_ == "INCREMENT":
                        if not to_append:
                            child_list[index] = tmp_vc.id
                        else:
                            child_list.append(tmp_vc.id)
                        self.bot.con.update(
                            'increment_vc_data',
                            ('parent_channel_id', cid),
                            child_list=json.dumps(child_list)
                        ).close()

                    await tmp_vc.set_permissions(member, manage_channels=True)

                    await member.move_to(tmp_vc)

                    with self.bot.con.get(("channel_id",), conditions={'user_id': member.id}) as cur:
                        vc_id = None
                        if cur.rowcount:
                            vc_id = cur.fetchone()[0]

                    self.bot.con.insert(member.id, tmp_vc.id, cid, msg_id=None, )
                    view = self.ui_manager.get_view(tmp_vc.id, timeout=None)
                    msg = await tmp_vc.send(
                        content=f"Manage VC settings here {member.mention}",
                        view=view
                    )
                    view.msg = msg
                    with self.bot.con.update('bot_data', ('user_id', member.id), msg_id=msg.id,
                                             returning='msg_id') as curr:
                        if curr.rowcount:
                            old_msg_id = curr.fetchone()[0]
                    if vc_id is not None and vc_id != tmp_vc.id:
                        old_vc = member.guild.get_channel(vc_id)
                        if old_vc:
                            members = old_vc.members
                            if len(members) == 0:
                                logger.debug(f"Old VC for {member} with no members found.. Deleting")
                                await old_vc.delete()
                            else:
                                member_: discord.Member
                                roles_dict = {
                                    member_: member_.top_role for member_ in members
                                    if not self.bot.con.exists(('user_id', member_.id))
                                }
                                max_user = next(iter(roles_dict))
                                for m, r in roles_dict.items():
                                    if r > roles_dict[max_user]:
                                        max_user = m
                                self.bot.con.insert(
                                    user_id=max_user.id,
                                    channel_id=vc_id,
                                    parent_channel_id=cid,
                                    msg_id=old_msg_id
                                )
                                await old_vc.send(f"Ownership of this Channel is Transferred to {max_user.mention}")
                                await self.ui_manager.update_ui(vc_id, allow_ownership=False)
                # moved from a main voice channel
                if before.channel is not None and self.bot.con.exists(('channel_id', before.channel.id), 'vc_data'):
                    logger.debug(f"User {member} moved to {after.channel.name}{cid}")
                # joined from  a separate chal
                else:
                    cur = self.bot.con.get(("channel_id",), conditions={'user_id': member.id})
                    info = cur.fetchone()
                    if cur.rowcount and info[0] == after.channel.id:
                        await self.ui_manager.update_ui(info[0], allow_ownership=False)

        if after.channel is None:
            with self.bot.con.get(("channel_id",), conditions={'user_id': member.id}) as cur:
                if cur.rowcount:
                    info = cur.fetchone()
                    await self.ui_manager.update_ui(info[0])
        if before.channel is not None:
            if len(before.channel.members) == 0:
                if self.bot.con.exists(('channel_id', before.channel.id), 'bot_data'):
                    with self.bot.con.get(('parent_channel_id',), {'channel_id': before.channel.id}, 'bot_data') as cur:
                        parent_channel_id = cur.fetchone()[0] if cur.rowcount else None

                    await before.channel.delete()
                    self.bot.con.delete(table='bot_data', conditions={'channel_id': before.channel.id})
                    if parent_channel_id is not None:
                        parent_channel_id: int
                        child_list: list | None
                        with self.bot.con.get(
                                ('child_list',),
                                {'parent_channel_id': parent_channel_id},
                                'increment_vc_data') as cur:
                            child_list = json.loads(cur.fetchone()[0]) if cur.rowcount else None

                        if child_list and before.channel.id in child_list:
                            child_list[child_list.index(before.channel.id)] = 0
                            self.bot.con.update(
                                'increment_vc_data',
                                ('parent_channel_id', parent_channel_id),
                                child_list=json.dumps(child_list)
                            ).close()


def setup(bot: PVCBot):
    bot.add_cog(JoinHandler(bot_=bot))
