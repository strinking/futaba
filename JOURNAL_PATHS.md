## Futaba Journal Paths
### Cog management
All contain the attribute `cogname: str`. Failures include `reason: str`, and if it was an error, `error: Exception`.
* `/cog/load`
* `/cog/load/fail`
* `/cog/unload`
* `/cog/unload/fail`
* `/cog/reload`
* `/cog/reload/fail`

### Filter cog
Adding a new content/file filter. Has attributes `hashsum: str`, `description: str`, and `cause: discord.Member`.
* `/filter/content/new/flag`
* `/filter/content/new/block`
* `/filter/content/new/jail`

Removing a group of content filters.
* `/filter/content/remove` - Attributes: `hashsums: List[str]`

Managing text filters. Has attributes `text: str`, `cause: discord.Member`.
Additionally, channel filters have the `channel: discord.TextChannel` attribute.
* `/filter/guild/new/flag`
* `/filter/guild/new/block`
* `/filter/guild/new/jail`
* `/filter/guild/remove`
* `/filter/channel/new/flag`
* `/filter/channel/new/block`
* `/filter/channel/new/jail`
* `/filter/channel/remove`

Managing user filter immunity. Has attributes: `member: discord.Member`, `cause: discord.Member`.
* `/filter/immunity/new` - Adds a user to the immune list.
* `/filter/immunity/remove` - Removes a user from the immune list.

### Journal cog
* `/journal/channel/add` - When a journal output channel is added. Attributes: `channel: discord.TextChannel, path: str, recursive: bool`
* `/journal/channel/remove` - When a journal output channel is removed. Attributes: `channel: discord.TextChannel, path: str`

### Miscellaneous
* `/misc/ping` - Time from receiving a command to sending a message to Discord. Attributs: `ms: float`
* `/misc/emoji/random` - A random emoji was sent. Attributes: `channel: discord.Messageable`, `emoji: discord.Emoji`
* `/misc/admin/shutdown` - Signifies the bot is about to shut down.

### Moderation
Actually handled in the tracking cog. This behavior is in the middle of changing.
All attributes (will) have `member: discord.Member`, `reason: Optional[str]`, `cause: discord.Member`.
* `/moderation/member/kick` - A member was kicked. TODO
* `/moderation/member/ban` - A member was banned. TODO
* `/moderation/member/softban` - A member was soft-banned. TODO
* `/moderation/member/unban` - A member was unbanned. TODO

### Welcome cog
* `/welcome/member/agree` - Member agrees to the rules. Attributes: `user: discord.Member`
* `/welcome/channel/set` - When the welcome change is changed. Attributes: `channel: Optional[discord.TextChannel]`, `cause: discord.Member`
* `/welcome/message/welcome` - The welcome message was set or unset. Attributes: `message: Optional[str]`
* `/welcome/message/goodbye` - The goodbye message was set or unset. Attributes: `message: Optional[str]`
* `/welcome/message/agree` - The agreement message was set or unset. Attributes: `message: Optional[str]`

### Settings cog
* `/settings/prefix` - The bot command prefix was set or unset. Attributes: `prefix: Optional[str]`, `default_prefix: str`
* `/settings/roles/member` - The member role was set or unset. Attributes: `role: Optional[discord.Role]`
* `/settings/roles/guest` - The guest role was set or unset. Attributes: `role: Optional[discord.Role]`
* `/settings/roles/mute` - The mute role was set or unset. Attributes: `role: Optional[discord.Role]`
* `/settings/roles/jail` - The jail role was set or unset. Attributes: `role: Optional[discord.Role]`
