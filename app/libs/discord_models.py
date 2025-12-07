"""Discord interaction models."""

from __future__ import annotations

from typing import Any, Optional, Callable, Awaitable
from dataclasses import dataclass


@dataclass
class User:
    """Discord user object."""
    id: str
    username: str
    discriminator: str
    avatar: Optional[str] = None
    bot: bool = False
    system: bool = False


@dataclass
class Member:
    """Discord guild member object."""
    user: User
    nick: Optional[str] = None
    roles: list[str] = None
    joined_at: str = ""
    
    def __post_init__(self) -> None:
        if self.roles is None:
            self.roles = []


@dataclass
class Channel:
    """Discord channel object."""
    id: str
    type: int
    name: Optional[str] = None
    parent_id: Optional[str] = None
    
    def is_text(self) -> bool:
        """Check if channel is text-based."""
        return self.type in (0, 5, 10, 11, 12)


@dataclass
class Guild:
    """Discord guild object."""
    id: str
    name: str
    icon: Optional[str] = None
    owner_id: str = ""
    
    def __post_init__(self) -> None:
        if not self.owner_id:
            self.owner_id = ""


class CommandOption:
    """Slash command option."""
    
    def __init__(
        self,
        name: str,
        description: str,
        option_type: int,
        required: bool = False,
        choices: list[dict[str, Any]] | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.option_type = option_type
        self.required = required
        self.choices = choices or []
        self.name_localizations = {}
        self.description_localizations = {}
    
    def set_name_localizations(self, localizations: dict[str, str]) -> CommandOption:
        """Set name localizations."""
        self.name_localizations = localizations
        return self
    
    def set_description_localizations(self, localizations: dict[str, str]) -> CommandOption:
        """Set description localizations."""
        self.description_localizations = localizations
        return self
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to Discord API format."""
        return {
            "type": self.option_type,
            "name": self.name,
            "description": self.description,
            "required": self.required,
            "choices": self.choices,
            "name_localizations": self.name_localizations if self.name_localizations else None,
            "description_localizations": self.description_localizations if self.description_localizations else None,
        }


class SlashCommand:
    """Slash command builder."""
    
    def __init__(self) -> None:
        self.name: str = ""
        self.description: str = ""
        self.options: list[CommandOption] = []
        self.name_localizations: dict[str, str] = {}
        self.description_localizations: dict[str, str] = {}
    
    def set_name(self, name: str) -> SlashCommand:
        """Set command name."""
        self.name = name
        return self
    
    def set_description(self, description: str) -> SlashCommand:
        """Set command description."""
        self.description = description
        return self
    
    def add_string_option(self, builder: Callable[[CommandOption], CommandOption]) -> SlashCommand:
        """Add string option."""
        from discord_types import OptionType
        option = CommandOption("", "", OptionType.STRING)
        builder(option)
        self.options.append(option)
        return self
    
    def set_description_localizations(self, localizations: dict[str, str]) -> SlashCommand:
        """Set description localizations."""
        self.description_localizations = localizations
        return self
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to Discord API format."""
        return {
            "name": self.name,
            "description": self.description,
            "options": [opt.to_dict() for opt in self.options],
            "name_localizations": self.name_localizations if self.name_localizations else None,
            "description_localizations": self.description_localizations if self.description_localizations else None,
        }


class Interaction:
    """Discord interaction object."""
    
    def __init__(self, data: dict[str, Any]) -> None:
        self.raw_data = data
        self.id: str = data.get("id", "")
        self.type: int = data.get("type", 0)
        self.data: dict[str, Any] = data.get("data", {})
        self.guild_id: Optional[str] = data.get("guild_id")
        self.channel_id: Optional[str] = data.get("channel_id")
        self.member: Optional[Member] = self._parse_member(data.get("member"))
        self.user: Optional[User] = self._parse_user(data.get("user"))
        self.token: str = data.get("token", "")
        self.app_id: str = data.get("application_id", "")
        self.responded: bool = False
        # modal related
        self.custom_id: Optional[str] = self.data.get("custom_id") or self.data.get("id")
        self._fields: dict[str, str] = {}
        # parse modal components if present
        comps = self.data.get("components") or self.data.get("components")
        if comps:
            try:
                for action_row in comps:
                    for comp in action_row.get("components", []):
                        cid = comp.get("custom_id")
                        # value may be present directly on submit payload
                        val = comp.get("value") or comp.get("default") or comp.get("value")
                        if cid and val is not None:
                            self._fields[cid] = val
            except Exception:
                pass
    
    @staticmethod
    def _parse_user(user_data: dict[str, Any] | None) -> Optional[User]:
        """Parse user data."""
        if not user_data:
            return None
        return User(
            id=user_data.get("id", ""),
            username=user_data.get("username", ""),
            discriminator=user_data.get("discriminator", "0"),
            avatar=user_data.get("avatar"),
            bot=user_data.get("bot", False),
        )
    
    @staticmethod
    def _parse_member(member_data: dict[str, Any] | None) -> Optional[Member]:
        """Parse member data."""
        if not member_data:
            return None
        user_data = member_data.get("user")
        user = Interaction._parse_user(user_data) if user_data else None
        return Member(
            user=user or User("", "", ""),
            nick=member_data.get("nick"),
            roles=member_data.get("roles", []),
            joined_at=member_data.get("joined_at", ""),
        )
    
    def is_command(self) -> bool:
        """Check if interaction is command."""
        from discord_types import InteractionType
        return self.type == InteractionType.APPLICATION_COMMAND
    
    def is_chat_input_command(self) -> bool:
        """Check if interaction is chat input command."""
        return self.is_command()
    
    def get_string(self, name: str, required: bool = False) -> Optional[str]:
        """Get string option value."""
        options = self.data.get("options", [])
        for option in options:
            if option.get("name") == name:
                return option.get("value")
        if required:
            raise ValueError(f"Required option '{name}' not found")
        return None
    
    @property
    def command_id(self) -> str:
        """Get command ID."""
        return self.data.get("id", "")
    
    @property
    def command_name(self) -> str:
        """Get command name."""
        return self.data.get("name", "")

    # Modal helpers
    def is_modal_submit(self) -> bool:
        from discord_types import InteractionType
        return self.type == InteractionType.MODAL_SUBMIT

    def get_text_input_value(self, custom_id: str) -> Optional[str]:
        return self._fields.get(custom_id)

    async def show_modal(self, modal: "ModalBuilder") -> None:
        """Show a modal to this interaction (delegates to client)."""
        if hasattr(self, "_client") and getattr(self, "_client") is not None:
            await self._client.show_modal(self, modal)


class Embed:
    """Discord embed object."""
    
    def __init__(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: int = 0,
    ) -> None:
        self.title = title
        self.description = description
        self.color = color
        self.fields: list[dict[str, Any]] = []
        self.footer: Optional[dict[str, str]] = None
        self.timestamp: Optional[str] = None
    
    def set_title(self, title: str) -> Embed:
        """Set title."""
        self.title = title
        return self
    
    def set_description(self, description: str) -> Embed:
        """Set description."""
        self.description = description
        return self
    
    def set_color(self, color: int) -> Embed:
        """Set color."""
        self.color = color
        return self
    
    def add_field(self, name: str, value: str, inline: bool = False) -> Embed:
        """Add field."""
        self.fields.append({"name": name, "value": value, "inline": inline})
        return self
    
    def set_footer(self, text: str, icon_url: Optional[str] = None) -> Embed:
        """Set footer."""
        self.footer = {"text": text}
        if icon_url:
            self.footer["icon_url"] = icon_url
        return self
    
    def set_timestamp(self, timestamp: str) -> Embed:
        """Set timestamp."""
        self.timestamp = timestamp
        return self
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to Discord API format."""
        data: dict[str, Any] = {}
        if self.title:
            data["title"] = self.title
        if self.description:
            data["description"] = self.description
        if self.color:
            data["color"] = self.color
        if self.fields:
            data["fields"] = self.fields
        if self.footer:
            data["footer"] = self.footer
        if self.timestamp:
            data["timestamp"] = self.timestamp
        return data


class TextInputBuilder:
    def __init__(self) -> None:
        self.custom_id: str = ""
        self.style: int = 1
        self.placeholder: str | None = None
        self.required: bool = True
        self.label: str | None = None

    def setCustomId(self, cid: str) -> "TextInputBuilder":
        self.custom_id = cid
        return self

    def setStyle(self, style: int) -> "TextInputBuilder":
        self.style = style
        return self

    def setPlaceholder(self, placeholder: str) -> "TextInputBuilder":
        self.placeholder = placeholder
        return self

    def setRequired(self, required: bool) -> "TextInputBuilder":
        self.required = required
        return self

    def setLabel(self, label: str) -> "TextInputBuilder":
        self.label = label
        return self

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "type": 4,
            "custom_id": self.custom_id,
            "style": self.style,
            "required": self.required,
        }
        if self.placeholder:
            data["placeholder"] = self.placeholder
        if self.label:
            data["label"] = self.label
        return data


class LabelBuilder:
    def __init__(self) -> None:
        self.label: str = ""
        self.description: str = ""
        self.text_input: TextInputBuilder | None = None

    def setLabel(self, label: str) -> "LabelBuilder":
        self.label = label
        return self

    def setDescription(self, desc: str) -> "LabelBuilder":
        self.description = desc
        return self

    def setTextInputComponent(self, input_comp: TextInputBuilder) -> "LabelBuilder":
        self.text_input = input_comp
        return self

    def to_dict(self) -> dict[str, Any]:
        # Wrap the input into an action row
        if not self.text_input:
            raise ValueError("No text input set")
        return {"type": 1, "components": [self.text_input.to_dict()]}


class ModalBuilder:
    def __init__(self) -> None:
        self.title: str = ""
        self.custom_id: str = ""
        self.components: list[dict[str, Any]] = []

    def setTitle(self, title: str) -> "ModalBuilder":
        self.title = title
        return self

    def setCustomId(self, cid: str) -> "ModalBuilder":
        self.custom_id = cid
        return self

    def addLabelComponents(self, label: LabelBuilder) -> "ModalBuilder":
        self.components.append(label.to_dict())
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "custom_id": self.custom_id,
            "components": self.components,
        }
