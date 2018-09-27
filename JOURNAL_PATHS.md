## Futaba Journal Paths
### Cog management
All contain the attribute `cogname`. Failures include `reason`, and if it was an error, `error`.
* `/cog/load`
* `/cog/load/fail`
* `/cog/unload`
* `/cog/unload/fail`
* `/cog/reload`
* `/cog/reload/fail`

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
