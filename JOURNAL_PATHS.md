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

Filter violations:
Signifies a violation of a text or name filter. Has attributes `filter_type: FilterType`, `filter_text: str`, `flagged: str`:
* `/filter/text/flag`
* `/filter/text/block`
* `/filter/text/jail`
* `/filter/username/flag`
* `/filter/username/block`
* `/filter/username/jail`
* `/filter/nickname/flag`
* `/filter/nickname/block`
* `/filter/nickname/jail`

Jump links for filter violations. Same attributes as above.
* `/filter/jump/text/flag`
* `/filter/jump/text/block`
* `/filter/jump/text/jail`
* `/filter/jump/username/flag`
* `/filter/jump/username/block`
* `/filter/jump/username/jail`
* `/filter/jump/nickname/flag`
* `/filter/jump/nickname/block`
* `/filter/jump/nickname/jail`

Signifies any violation of a file filter. Has attributes `filter_type: FilterType`, `url: str`.
* `/filter/file/flag`
* `/filter/file/block`
* `/filter/file/jail`

Jump links for file violations. Same attributes as above.
* `/filter/file/flag`
* `/filter/file/block`
* `/filter/file/jail`

Managing user filter immunity. Has attributes: `member: discord.Member`, `cause: discord.Member`.
* `/filter/immunity/new` - Adds a user to the immune list.
* `/filter/immunity/remove` - Removes a user from the immune list.

### Information cog
* `/alias/member/update` - Whenever a member is updated and that information is tracked by the alias logger. Attributes: `before, after: discord.Member`, `changes: MemberChanges`.
* `/alias/alt/add` - A possible alt account is added. Attributes: `users: List[discord.Member, 2]`.
* `/alias/alt/clear` - Removes all alt accounts associated to the user. Attributes: `user: discord.Member`.

### Journal cog
* `/journal/channel/add` - When a journal output channel is added. Attributes: `channel: discord.TextChannel, path: str, recursive: bool`
* `/journal/channel/remove` - When a journal output channel is removed. Attributes: `channel: discord.TextChannel, path: str`
* `/journal/channel/move` - When a journal output channel is moved. Attributes: `old_channel: discord.TextChannel, new_channel: discord.TextChannel, path: str, recursive: bool`
* `/journal/user/add` - When a journal output is added to a user. Attributes: `user: discord.Member, path: str, recursive: bool`
* `/journal/user/remove` - When a journal output is removed from a user. Attributes: `user: discord.Member, path: str`

### Miscellaneous
* `/misc/ping` - Time from receiving a command to sending a message to Discord. Attributs: `ms: float`
* `/misc/emoji/random` - A random emoji was sent. Attributes: `channel: discord.Messageable`, `emoji: discord.Emoji`
* `/debug/error/runtime` - A deliberately raised `RuntimeError`.
* `/debug/error/network` - A deliberately raised `aiohttp.ClientError`.
* `/debug/admin/shutdown` - Signifies the bot is about to shut down.
* `/mentionable/enforce` - A person was renicked to make their name mentionable. Attributes: `member: discord.Member`, `prefix: str`, `nick: str`.

### Moderation
Actually handled in the tracking cog. This behavior is in the middle of changing.
All attributes have `member: discord.Member`, `reason: Optional[str]`, `cause: discord.Member`.
* `/moderation/member/kick` - A member was kicked. TODO
* `/moderation/member/ban` - A member was banned. TODO
* `/moderation/member/softban` - A member was soft-banned. TODO
* `/moderation/member/unban` - A member was unbanned. TODO

### Cleanup
Commands for deleting messages in bulk based on certain criteria.
All attributes have `channel: discord.TextChannel`, `messages: List[discord.Message]`, `cause: discord.Member`.
* `/moderation/cleanup/count` - Deletes the given number of messages. Attributes: `count: int`.
* `/dump/moderation/cleanup/count` - Contains the deleted messages in JSON form. Attributes: `messages: dict`.
* `/moderation/cleanup/id` - Deletes messages until you hit the limit or pass the given ID. Attributes: `message_id: int`.
* `/dump/moderation/cleanup/id` - Contains the deleted messages in JSON form. Attributes: `messages: dict`.
* `/moderation/cleanup/user` - Deletes the last &lt;count&gt; messages from the given user. Attributes: `count: int`, `user: discord.Member`.
* `/dump/moderation/cleanup/user` - Contains the deleted messages in JSON form. Attributes: `messages: dict`.
* `/moderation/cleanup/text` - Deletes the last given &lt;count&gt; messages that contain the given text. Attributes: `count: int`, `text: str`.
* `/dump/moderation/cleanup/text` - Contains the deleted messages in JSON form. Attributes: `messages: dict`.

### Welcome cog
Join management:
* `/welcome/member/agree` - Member agrees to the rules. Attributes: `user: discord.Member`.
* `/welcome/channel/set` - When the welcome change is changed. Attributes: `channel: Optional[discord.TextChannel]`, `cause: discord.Member`.
* `/welcome/message/welcome` - The welcome message was set or unset. Attributes: `message: Optional[str]`.
* `/welcome/message/goodbye` - The goodbye message was set or unset. Attributes: `message: Optional[str]`.
* `/welcome/message/agree` - The agreement message was set or unset. Attributes: `message: Optional[str]`.

Role reapplication:
* `/roles/reapply` - Reapplying roles to a member. Attributes: `member: discord.Member`, `roles: Tuple[discord.Role]`.
* `/roles/save` - Saving updated roles for a member. Attributes: `member: discord.Member`.

Prune:
* `/welcome/prune` - Displays the number of members that were removed from the server `members: [discord.Member]`

### Self-assignable roles cog
* `/roles/self/add` - A member added some self-assignable roles to themselves. Attributes: `roles: List[discord.Role]`.
* `/roles/self/remove` - A member removed some self-assignable roles from themselves. Attributes: `roles: List[discord.Role]`.
* `/roles/joinable/add` - Some role(s) were set as "joinable". Attributes: `roles: List[discord.Role]`.
* `/roles/joinable/remove` - Some role(s) were set as "unjoinable". Attributes: `roles: List[discord.Role]`.
* `/roles/channel/set` - The channels permitted for bot commands was changed. Attributes: `channels: List[discord.TextChannel]`.

### Settings cog
* `/settings/prefix` - The bot command prefix was set or unset. Attributes: `prefix: Optional[str]`, `default\_prefix: str`
* `/settings/roles/member` - The member role was set or unset. Attributes: `role: Optional[discord.Role]`
* `/settings/roles/guest` - The guest role was set or unset. Attributes: `role: Optional[discord.Role]`
* `/settings/roles/mute` - The mute role was set or unset. Attributes: `role: Optional[discord.Role]`
* `/settings/roles/jail` - The jail role was set or unset. Attributes: `role: Optional[discord.Role]`

### Tracker cog
* `/tracking/message/new` - A new message was sent. Attributes: `message: discord.Message`
* `/tracking/jump/message/new` - Jump link for new message. Same attributes.
* `/tracking/full/message/new` - Full message content for new message, with jump link. Same attributes.
* `/tracking/message/edit` - A message was edited. Attributes: `before: discord.Message`, `after: discord.Message`
* `/tracking/jump/message/edit` - Jump link for edited message. Same attributes.
* `/tracking/full/message/edit` - Full message content for edited message, with jump link. Same attributes.
* `/tracking/message/delete` - A message was deleted. Attributes: `message: discord.Message`, `cause: MessageDeletionReason`
* `/tracking/jump/message/delete` - Jump link for deleted message. Same attributes.
* `/tracking/full/message/delete` - Full message content for deleted message, with jump link. Same attributes.
* `/tracking/reaction/add` - A reaction was added to a message. Attributes: `reaction: discord.Reaction`, `user: discord.User`
* `/tracking/jump/reaction/add` - Jump link for reacted message. Attributes: `message: discord.Message`
* `/tracking/reaction/remove` - A reaction was removed to a message. Attributes: `reaction: discord.Reaction`, `user: discord.User`
* `/tracking/jump/reaction/remove` - Jump link for reacted message. Attributes: `message: discord.Message`
* `/tracking/reaction/clear` - All reactions were cleared from a message. Attributes: `message: discord.Message`, `reactions: List[discord.Reaction]`
* `/tracking/jump/reactions/clear` - Jump link for reacted message. Attributes: `message: discord.Message`
* `/tracking/channel/new` - Guild channel was created. Attributes: `channel: discord.GuildChannel`
* `/tracking/channel/delete` - Guild channel was deleted. Attributes: `channel: discord.GuildChannel`
* `/tracking/member/join` - Member joined the guild. Attributes: `member: discord.Member`
* `/tracking/member/leave` - Member left the guild. Includes kicks, bans, etc. Attributes: `member: discord.Member`, `cause: MemberLeaveReason`.
* `/tracking/member/update` - This path does not exist. To get information on when members are updated, use paths `/roles/save` and `/alias/member/update`.
