"""Discord bot client."""

from __future__ import annotations

import asyncio
import aiohttp
import json
from typing import Callable, Awaitable, Optional, Any
from datetime import datetime

from discord_types import GatewayIntentBits, InteractionType, InteractionResponseType, Events
from discord_models import Interaction, User, Channel, Guild, SlashCommand, Embed


class Client:
    """Discord bot client."""
    
    def __init__(self, *, intents: GatewayIntentBits | int = 0) -> None:
        self.intents = intents
        self.token: Optional[str] = None
        self.user: Optional[User] = None
        self.application_id: Optional[str] = None
        self.http_client: Optional[aiohttp.ClientSession] = None
        
        # Event handlers
        self._event_handlers: dict[str, list[Callable]] = {}
        self._once_handlers: dict[str, list[Callable]] = {}
        self._interaction_handlers: dict[str, Callable] = {}
        
        # Commands
        self.commands: list[tuple[SlashCommand, Callable]] = []
        self.tree = CommandTree(self)
    
    def event(self, func: Callable) -> Callable:
        """Register event handler."""
        event_name = func.__name__
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        self._event_handlers[event_name].append(func)
        return func

    def once(self, event_name: str, func: Callable) -> None:
        """Register a one-time event handler."""
        if event_name not in self._once_handlers:
            self._once_handlers[event_name] = []
        self._once_handlers[event_name].append(func)
    
    async def emit(self, event_name: str, *args: Any, **kwargs: Any) -> None:
        """Emit event."""
        handlers = self._event_handlers.get(event_name, [])
        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                await handler(*args, **kwargs)
            else:
                handler(*args, **kwargs)
        # handle once handlers
        once_handlers = self._once_handlers.get(event_name, [])
        if once_handlers:
            for handler in once_handlers:
                if asyncio.iscoroutinefunction(handler):
                    await handler(*args, **kwargs)
                else:
                    handler(*args, **kwargs)
            # clear once handlers after running
            self._once_handlers[event_name] = []
    
    async def run(self, token: str) -> None:
        """Start bot."""
        self.token = token
        self.http_client = aiohttp.ClientSession()
        
        try:
            # Get bot info
            headers = {"Authorization": f"Bot {token}"}
            async with self.http_client.get(
                "https://discordapp.com/api/v10/users/@me",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.user = User(
                        id=data.get("id", ""),
                        username=data.get("username", ""),
                        discriminator=data.get("discriminator", "0"),
                        avatar=data.get("avatar"),
                        bot=True,
                    )
                    self.application_id = data.get("id")
            
            # Start event loop
            await self.emit("ready")
            
            # Register commands
            if self.commands:
                await self._register_commands()
            
            # Keep running
            await asyncio.sleep(3600 * 24)  # Keep running
        finally:
            await self.http_client.aclose()
    
    async def _register_commands(self) -> None:
        """Register slash commands."""
        if not self.application_id or not self.token:
            return
        
        headers = {"Authorization": f"Bot {self.token}"}
        commands_data = [cmd.to_dict() for cmd, _ in self.commands]
        
        url = f"https://discordapp.com/api/v10/applications/{self.application_id}/commands"
        async with self.http_client.put(url, json=commands_data, headers=headers) as resp:
            if resp.status == 200:
                registered = await resp.json()
                for reg_cmd in registered:
                    cmd_id = reg_cmd.get("id")
                    for cmd, handler in self.commands:
                        if cmd.name == reg_cmd.get("name"):
                            self._interaction_handlers[cmd_id] = handler
    
    async def handle_interaction(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle incoming interaction."""
        interaction = Interaction(data)
        # attach client reference for modal show
        interaction._client = self
        # emit interaction create for listeners (e.g. modal waiters)
        await self.emit(Events.INTERACTION_CREATE, interaction)
        
        # Handle PING
        if interaction.type == InteractionType.PING:
            return {
                "type": InteractionResponseType.PONG,
            }
        
        # Handle APPLICATION_COMMAND
        if interaction.type == InteractionType.APPLICATION_COMMAND:
            handler = self._interaction_handlers.get(interaction.command_id)
            if handler:
                await handler(interaction)
                return {"type": InteractionResponseType.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE}

        # Handle MODAL SUBMIT
        if interaction.type == InteractionType.MODAL_SUBMIT:
            # leave to listeners that were registered via once/event
            return {"type": InteractionResponseType.PONG}

        return {"type": InteractionResponseType.PONG}
    
    async def send_interaction_response(
        self,
        interaction: Interaction,
        response_type: int,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        """Send interaction response."""
        if not self.token or interaction.responded:
            return
        
        headers = {"Authorization": f"Bot {self.token}"}
        url = f"https://discordapp.com/api/v10/interactions/{interaction.id}/{interaction.token}/callback"
        
        payload = {"type": response_type}
        if data:
            payload["data"] = data
        
        async with self.http_client.post(url, json=payload, headers=headers) as resp:
            if resp.status == 204:
                interaction.responded = True
    
    async def edit_interaction_response(
        self,
        interaction: Interaction,
        content: Optional[str] = None,
        embed: Optional[Embed] = None,
    ) -> None:
        """Edit interaction response."""
        if not self.token:
            return
        
        headers = {"Authorization": f"Bot {self.token}"}
        url = f"https://discordapp.com/api/v10/webhooks/{self.application_id}/{interaction.token}/messages/@original"
        
        data: dict[str, Any] = {}
        if content:
            data["content"] = content
        if embed:
            data["embeds"] = [embed.to_dict()]
        
        async with self.http_client.patch(url, json=data, headers=headers) as resp:
            pass


class CommandTree:
    """Command tree for managing slash commands."""
    
    def __init__(self, client: Client) -> None:
        self.client = client
    
    def command(
        self,
        *,
        name: str = "",
        description: str = "",
    ) -> Callable:
        """Decorator to register slash command."""
        def decorator(func: Callable) -> Callable:
            cmd = SlashCommand()
            cmd.set_name(name or func.__name__)
            cmd.set_description(description or func.__doc__ or "")
            
            self.client.commands.append((cmd, func))
            return func
        return decorator
    
    async def sync(self) -> None:
        """Sync commands with Discord."""
        if self.client.http_client:
            await self.client._register_commands()
