from .core import Spam

# Setup for when cog is loaded
def setup(bot):
    cog = Spam(bot)
    bot.add_cog(cog)

# Remove all the cogs when cog is unloaded
def teardown(bot):
    bot.remove_cog(Spam.__name__)

