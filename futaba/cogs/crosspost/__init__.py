from .core import Crosspost


# Setup for when cog is loaded
def setup(bot):
    cog = Crosspost(bot)
    bot.add_cog(cog)


# Remove all the cogs when cog is unloaded
def teardown(bot):
    bot.remove_cog(Crosspost.__name__)
