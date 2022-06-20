import discord
from discord.ext import commands
from discord.commands import Option

from loguru import logger

from ..utils.helper import project_base_path
from ..bot import PVCBot


async def is_admin(ctx):
    return ctx.user.guild_permissions.administrator


class CreateVC(commands.Cog):

    def __init__(self, bot_: PVCBot):
        self.bot = bot_

    vc = discord.SlashCommandGroup(
        "pvc",
        "Used to handle creation or deletion of pvc(s)",
        default_member_permissions=discord.Permissions(manage_guild=True)
    )
    create = vc.create_subgroup("create", "Creates a VC or a MAIN vc channel")

    @create.command(description="Returns the Menu to Create VC")
    async def main(self,
                   ctx: discord.ApplicationContext,
                   name: Option(str, description="Name Of the Voice Channel"),
                   type_: Option(
                       str,
                       description="How the name of the created VC should be handled",
                       autocomplete=discord.utils.basic_autocomplete(
                           ["VC-NAME", "USERNAME"]
                       )),
                   region: Option(str,
                                  description="Region in Which channel of this type should be made",
                                  autocomplete=discord.utils.basic_autocomplete(
                                      discord.VoiceRegion._enum_member_names_),
                                  required=False
                                  ),
                   user_limit: Option(int,
                                      description="Number of members that can be in a voice channel",
                                      required=False
                                      )
                   ):
        logger.debug(f"Creating a {type_} type VC with name {name} "
                     f"in region {region if region else 'Automatic'}, with user_limit {user_limit}")

        vc = await ctx.guild.create_voice_channel(
            name=name,
            rtc_region=discord.VoiceRegion[region] if region else None,
            user_limit=user_limit
        )
        self.bot.con.insert_main(vc.id, type_)
        await ctx.respond(f"Successfully Created Main {vc.mention}")


def setup(bot):
    bot.add_cog(CreateVC(bot))
