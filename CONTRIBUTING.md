## Contributing to Futaba
Futaba is a Discord bot for the [Programming server](https://discord.gg/010z0Kw1A9ql5c1Qe). Inspired by previous bot efforts in the server, will aim to be more usable for members and maintainable for coders.

Before you start coding, make sure you've read the [README](README)'s instructions so you have all the software you need installed on your machine.

### Design Philosophy
**Guild agnostic and portable**  
The bot should never assume it is in a certain guild or set of guilds, or that those guilds have particular features, (e.g. a role called XYZ, or certain emojis). If guild-specific items are necessary, they should be configurable.

**Configurable and persistent**  
All settings in the bot which a moderation team would want to have under their control should be configurable. Anything that is changed or set in the bot should be persistent, that is should survive an unexpected restart. This should even be true of scheduled tasks, such as jailing a user for 24 hours. Whenever a command returns successfully, the user should be confident that the data is durably stored.

**Augment the Discord client**  
There are several deficiences in the usability of the Discord client, such as items that make routine moderation tasks more difficult. For instance, getting a clickable mention of a user in a private channel (as not to actually notify them) is not easy: you must either manually make a mention (which requires knowing their ID), or searching for one of their posts for the sole purpose of clicking on their name. The bot should find pain points for users and moderators alike, and add seamless features that address those concerns where possible.

**Utilize the Discord API in its fullest**  
Some pieces of information are available via the API, but are either difficult or impossible to access from the client itself. When relevant, information should be gathered and displayed to the user in a meaningful way.

**Uniform command style**  
Commands should be usable in the same style, both in terms of invocation and responses. For Futaba specifically, commands should have a sensible command, aliased shortcuts, or be grouped into a command group that has the same properties. They should all react to any command in a standard way based on how the command was carried out (or not). When multiple pieces of information need to be outputted, an embed should be used that makes it easy to pick out pieces of information a user wants.

### Code Structure
"Standard" or templated files, like an example configuration file should be in `misc/`.

Features that are global or generic enough to exist everywhere in the bot should be placed in their respective submodule within `futaba/`. New commands or other such behaviors should be modular, and encapsulated within a cog in `futaba/cogs/`, following the templating available there. See existing cogs for examples of how to structure your code.

If your cog is necessary for the proper function of the bot (this is very unlikely to be true), then you must make it a "mandatory" cog. These cannot be loaded/unloaded/reloaded once the bot has started, and are to some extent tied to the `Client` object itself. Currently the only two mandatory cogs are the reloader itself and the journal router.

When you need to store information persistently, a database model should be created in `futaba/sql/`. (NOTE: This will definitely change when [#13](https://github.com/strinking/futaba/issues/13) is merged). A model example can be copied from the template, but the general principle is that the `__init__` declares all the tables, and sets up in-memory caches for tables as needed. Then methods should be created that allow interacting with the table from in a SQL-agnostic, logical way. SQLAlchemy, and especially raw SQL should **never** be present outside of `futaba/sql/models/`.

### Development and Testing
It is important to ensure no issues come up with pylint. When in the root, simply:
```
$ pylint futaba
```

When running the bot, it is often a good idea to include the `-d` flag to see debug-level logging messages.
```
$ python3 -m futaba -d config-dev.toml
```
