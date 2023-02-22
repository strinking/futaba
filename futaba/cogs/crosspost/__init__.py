from discord.ext.commands.bot import Bot

from .core import Crosspost


# Setup for when cog is loaded
async def setup(bot: Bot):
    cog = Crosspost(bot)
    await bot.add_cog(cog)


# Remove all the cogs when cog is unloaded
async def teardown(bot: Bot):
    await bot.remove_cog(Crosspost.__name__)
