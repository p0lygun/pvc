import discord
from discord.ext import commands
from loguru import logger

from ..bot import PVCBot


class JoinHandler(commands.Cog):
    def __init__(self, bot_: PVCBot):
        self.bot = bot_

    @commands.Cog.listener()
    async def on_voice_state_update(self,
                                    member: discord.Member,
                                    before: discord.VoiceState,
                                    after: discord.VoiceState
                                    ):
        if after.channel is not None:
            cid = after.channel.id
            logger.debug(f"{member} joined {after.channel.name}")
            cur = self.bot.con.get_vc_data(channel_id=cid)
            if cur.rowcount:
                type_ = cur.fetchone()[0]
                logger.debug(type_)
                if type_ == "VC-NAME":
                    logger.debug("Creating New VC with type VC-NAME")
                    vc_name = after.channel.name
                else:
                    vc_name = str(member)

                overwrite = discord.PermissionOverwrite()
                overwrite.manage_channels = True

                tmp_vc = await member.guild.create_voice_channel(
                    name=vc_name,
                    overwrites={member: overwrite},
                    rtc_region=after.channel.rtc_region,
                    user_limit=after.channel.user_limit,
                    category=after.channel.category
                )

                await member.move_to(tmp_vc)
                self.bot.con.insert(member.id, tmp_vc.id)
            return

        if before.channel is not None:
            cur = self.bot.con.get(user_id=member.id)
            if cur.rowcount and cur.fetchone()[0] == before.channel.id:
                if len(before.channel.members) == 0:
                    await before.channel.delete()
                    self.bot.con.delete(user_id=member.id)


def setup(bot: PVCBot):
    bot.add_cog(JoinHandler(bot_=bot))
