## Futaba Journal Paths
### Cog management
All contain the attribute `cogname: str`. Failures include `reason: str`, and if it was an error, `error: Exception`.
* `/cog/load`
* `/cog/load/fail`
* `/cog/unload`
* `/cog/unload/fail`
* `/cog/reload`
* `/cog/reload/fail`

### Journal cog
* `/journal/channel/add` - When a journal output channel is added. Attributes: `channel: discord.TextChannel, path: str, recursive: bool`
* `/journal/channel/remove` - When a journal output channel is removed. Attributes: `channel: discord.TextChannel, path: str`

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
