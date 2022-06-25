import discord
from discord.ext import commands
from discord.commands import Option

from loguru import logger

from ..utils.helper import project_base_path
from ..bot import PVCBot


async def is_admin(ctx):
    return ctx.user.guild_permissions.administrator


def get_guild_main_vc(ctx: discord.AutocompleteContext):
    bot = ctx.bot
    cur = bot.con.get_vc_data(('channel_id',), {'guild_id': ctx.interaction.guild.id})
    if cur.rowcount:
        return [bot.get_channel(channel_id) for channel_id in cur.fetchall()]
    else:
        return []


def filter_vc_type(ctx: discord.AutocompleteContext):
    types_ = ["VC-NAME", "USERNAME"]
    if ctx.interaction.guild.premium_tier > 0:
        types_.append("ACTIVITY")
    types_.append("CUSTOM")
    return types_


class CreateVC(commands.Cog):

    def __init__(self, bot_: PVCBot):
        self.bot = bot_

    vc = discord.SlashCommandGroup(
        "pvc",
        "Used to handle creation or deletion of pvc(s)",
        default_member_permissions=discord.Permissions(manage_guild=True)
    )
    create = vc.create_subgroup("create", "Creates a VC or a MAIN vc channel")
    delete = vc.create_subgroup("delete", "Deletes a MAIN vc channel")

    @create.command(name="vc", description="Returns the Menu to Create VC")
    async def create_vc(self,
                        ctx: discord.ApplicationContext,
                        name: Option(str, description="Name Of the Voice Channel"),
                        type_: Option(
                            str,
                            description="How the name of the created VC should be handled",
                            autocomplete=discord.utils.basic_autocomplete(filter_vc_type)),
                        region: Option(str,
                                       description="Region in Which channel of this type should be made",
                                       autocomplete=discord.utils.basic_autocomplete(
                                           discord.VoiceRegion._enum_member_names_),
                                       required=False
                                       ),
                        user_limit: Option(int,
                                           description="Number of members that can be in a voice channel",
                                           required=False
                                           ),
                        category: Option(discord.CategoryChannel,
                                         description="Category under which the channel should be made",
                                         required=False
                                         ),
                        custom_name: Option(str,
                                            description="Custom format that will be used to name the child VCs",
                                            required=False,
                                            )

                        ):
        logger.debug(f"Creating a {type_} type VC with name {name} "
                     f"in region {region if region else 'Automatic'}, with user_limit {user_limit}")

        if type_ == "CUSTOM" and custom_name is None:
            await ctx.interaction.response.send_message(
                "Failed to create CUSTOM type VC, as custom name format is not provided",
                delete_after=10
            )
            return

        vc = await ctx.guild.create_voice_channel(
            name=name,
            rtc_region=discord.VoiceRegion[region] if region else None,
            user_limit=user_limit,
            category=category,
        )
        self.bot.con.insert_main(vc.id, type_, ctx.guild.id, custom_name)
        await ctx.respond(f"Successfully Created Main {vc.mention}")

    @delete.command(name='vc', description="Deletes the provided VC")
    async def delete_vc(self,
                        ctx: discord.ApplicationContext,
                        id_: Option(str, description="id of VC to delete")
                        ):
        id_ = int(id_.strip()) if id_.strip().isdigit() else 0
        if id_ == 0:
            await ctx.interaction.response.send_message("Not Valid ID")
            return

        if self.bot.con.exists(('channel_id', id_), 'vc_data'):
            chal = self.bot.get_channel(id_)
            await chal.delete()
            self.bot.con.delete(table='vc_data', conditions={'channel_id': id_})
            logger.debug(f"Successfully deleted {chal}")
            await ctx.interaction.response.send_message(f"Deleted {chal.name}")
        else:
            await ctx.interaction.response.send_message("No VC for your guild in database")


def setup(bot):
    bot.add_cog(CreateVC(bot))
