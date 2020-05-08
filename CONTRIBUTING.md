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

**Command output**  
As mentioned above, all commands will react to the command message to indicate status. The reactions in place are:
* `WHITE HEAVY CHECK MARK` - Command success
* `WARNING SIGN` - (currently unused)
* `CROSS MARK` - Command failed. Either the database didnt' commit, an error occurred, etc.
* `NO ENTRY SIGN` - Command could not be invoked. Generally the user lacks the permissions to invoke it.
* `BLACK QUESTION MARK ORNAMENT` - Invalid argument(s) or argument parse error. A `*Conv` conversion error or some other issue with the argument's value.
* `ELECTRIC PLUG` - Networking issues, such as DNS or socket timeout. The implication is that it is either spurious or a third party's servers are not working.

Commands which express success or failure with additional information should generally use an embed. Text responses are acceptable if they do not have any special formatting and are a single sentence. Embeds are mandatory if user or role mentions are used. The argument is always used as `colour` because that's the original name used by the library, and we've had issues in the past with pylint and `color`.

We have some standard colors for discord embeds:
* `discord.Colour.dark_teal()` - General success or information.
* `discord.Colour.red()` - Failure or error.
* `discord.Colour.dark_red()` - Unusual or exceptional error conditions. Used in cases where it is not the user or bot's fault that the failure occurred.
* `discord.Colour.dark_purple()` - Success, but an exceptional condition. For instance, a list command would use `dark_teal` if there are entries, but a `dark_purple` with a "nothing found"-type message if not.
* (other) - If there is a particular color that is more appropriate, it is used instead. This is mostly for things such as the member and role info commands, where the color of the embed matches the color of the item being described.

Commands should never mention users or roles. Commands should not mention the invoking user (e.g. "@user, here are the configured channels:")

### Code Structure
"Standard" or templated files, like an example configuration file should be in `misc/`.

Features that are global or generic enough to exist everywhere in the bot should be placed in their respective submodule within `futaba/`. New commands or other such behaviors should be modular, and encapsulated within a cog in `futaba/cogs/`, following the templating available there. See existing cogs for examples of how to structure your code.

If your cog is necessary for the proper function of the bot (this is very unlikely to be true), then you must make it a "mandatory" cog. These cannot be loaded/unloaded/reloaded once the bot has started, and are to some extent tied to the `Client` object itself. Currently the only two mandatory cogs are the reloader itself and the journal router.

All other functionality, such as that which depends on specific third-party applications like [Statbot](https://github.com/strinking/statbot), should be an "optional" cog. This means they are placed in `futaba/cogs/optional/`, and must be explicitly enabled in the bot's config or loaded manually by the bot owner.

When you need to store information persistently, a database model should be created in `futaba/sql/`. (NOTE: This will definitely change when [#13](https://github.com/strinking/futaba/issues/13) is merged). A model example can be copied from the template, but the general principle is that the `__init__` declares all the tables, and sets up in-memory caches for tables as needed. Then methods should be created that allow interacting with the table from in a SQL-agnostic, logical way. SQLAlchemy, and especially raw SQL should **never** be present outside of `futaba/sql/models/`.

If you want to set up a delayed task, use Navi, Futaba's internal job scheduler. If your function cannot fit into one of the existing `Task` objects, create a new one and provide a way to serialize/deserialize it into JSON for persistent storage in the database. In rare cases where the delay is very short, an `asyncio.sleep()` may be acceptable. Never use `time.sleep()`, that chokes up the event loop.

### Development and Testing
It is important to address issues that come up with pylint. When in the root, simply:
```
$ pylint futaba
```
Please ensure that your code passes the linting before merging it to master.

When running the bot, it is often a good idea to include the `-d` flag to see debug-level logging messages.
```
$ python3 -m futaba -d config-dev.toml
```
