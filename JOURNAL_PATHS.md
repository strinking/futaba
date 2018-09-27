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
