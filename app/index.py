from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Awaitable, Callable

# Import custom Discord library
from libs import Client, GatewayIntentBits, Embed, Interaction, SlashCommand

from libs.readHTML import read_html
from libs import Events

BASE_DIR = Path(__file__).resolve().parent
SECRET: dict[str, Any] = json.loads((BASE_DIR.parent / "secret.json").read_text(encoding="utf-8"))
CONFIG: dict[str, Any] = json.loads((BASE_DIR.parent / "config.json").read_text(encoding="utf-8"))
DB: dict[str, Any] = json.loads((BASE_DIR.parent / "db.json").read_text(encoding="utf-8"))

MAX_LEN = CONFIG.get("max_len") or 1500
UPDATE_TIMEWAIT = (CONFIG.get("update_timewait") or 2500) / 1000.0

intents = GatewayIntentBits.GUILDS | GatewayIntentBits.GUILD_MESSAGES | GatewayIntentBits.MESSAGE_CONTENT

bot = Client(intents=intents)
log_channel: Any = None
followup_list: list[Any] = []

ReplyFunc = Callable[[str], Awaitable[None]]


class ReplyOptions:
    """Reply options for handling long responses."""
    def __init__(self) -> None:
        self.followup_list: list[Any] = []


def limit_len(text: str) -> str:
    return text[:MAX_LEN]


async def replyer(
    interaction: Interaction,
    options: str | dict[str, Any],
    other_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Handle long replies by splitting and posting multiple messages."""
    if other_options is None:
        other_options = {"followup_list": []}
    
    if not other_options.get("followup_list"):
        other_options["followup_list"] = []
    
    # Get content string
    if isinstance(options, str):
        content = options
        options_dict = {"content": content}
    else:
        content = options.get("content", "")
        options_dict = options
    
    # Split content if too long
    content_list: list[str] = []
    while content:
        content_list.append(content[:MAX_LEN])
        content = content[MAX_LEN:]
    
    # Send/edit messages
    for i, chunk in enumerate(content_list):
        if i == 0:
            # Edit original reply
            nw_options = dict(options_dict)
            nw_options["content"] = chunk
            await bot.edit_interaction_response(interaction, content=chunk)
        else:
            # Send follow-up messages
            nw_options: dict[str, Any] = {}
            if isinstance(options_dict, dict):
                for key in options_dict:
                    if key == "content":
                        nw_options["content"] = chunk
                    elif key in ("embeds", "components", "files"):
                        nw_options[key] = []
                    else:
                        nw_options[key] = dict(options_dict[key])
            else:
                nw_options["content"] = chunk
            
            # Track follow-up messages
            if len(other_options["followup_list"]) < i:
                # Create new follow-up
                other_options["followup_list"].append(nw_options)
            else:
                # Update existing follow-up
                other_options["followup_list"][i - 1] = nw_options
    
    return other_options


async def send_log(color: int, *data: Any) -> None:
    """Send formatted log message to log channel."""
    global log_channel
    if not log_channel:
        return

    try:
        content = ""
        for item in data:
            if isinstance(item, str):
                content += item
            else:
                content += json.dumps(item, indent=2)
            content += " "

        if len(content) > MAX_LEN:
            import io
            import time
            # For custom library, we'll just log to console for now
            print(f"Log (file): {content[:100]}...")
        else:
            embed = Embed(color=color)
            embed.set_description(f"```\n{content}\n```")
            embed.set_footer(
                text="DChatGPT ੭ ˙ᗜ˙ )੭ 🥑",
                icon_url="https://gravatar.com/avatar/24c497d6a7c9d41e4963a20fe1aa9bc205824d816b1382be070afe2e57e723f6.jpg?s=1080",
            )
            print(f"Log: {content}")
    except Exception as e:
        print(f"Error sending log: {e}")


async def call_ai(
    user_id: str,
    question: str,
    reply_func: ReplyFunc,
    edit_func: ReplyFunc,
    error_func: ReplyFunc | None = None,
) -> None:
    """Call OpenAI API and stream responses."""
    user_token = DB.get(user_id, {}).get("openai_token") if DB.get(user_id) else None
    if not user_token:
        user_token = SECRET.get("llm_apikey")

    if not user_token:
        await reply_func("[AI didn't respond]")
        if error_func:
            await error_func("You have not set your OpenAI token yet. Please set it first.")
        return

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=user_token)
    nwstr = ""
    await reply_func("Question received. Communicating with AI...")
    print(f"User question: {question}")

    flag = True

    async def edit_loop() -> None:
        nonlocal flag
        while flag:
            await asyncio.sleep(UPDATE_TIMEWAIT)
            display = nwstr + "[AI is thinking]" if nwstr else "[AI is thinking]"
            await edit_func(display)

    edit_task = asyncio.create_task(edit_loop())

    try:
        stream = await client.chat.completions.create(
            model=CONFIG.get("model") or "gpt-5-nano",
            messages=[{"role": "user", "content": question}],
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                delta = chunk.choices[0].delta.content
                if isinstance(delta, str):
                    nwstr += delta
                    print({"receive_chunk": delta, "current_response": nwstr})

        flag = False
        await asyncio.sleep(UPDATE_TIMEWAIT)
        if not nwstr:
            nwstr = "[AI didn't respond]"
        await edit_func(limit_len(nwstr))
    except Exception as e:
        flag = False
        if error_func:
            await error_func("An error occurred while communicating with AI.")
    finally:
        edit_task.cancel()
        try:
            await edit_task
        except asyncio.CancelledError:
            pass


@bot.event
async def ready() -> None:
    """Bot ready event handler."""
    global log_channel
    print(f"Logged in as {bot.user.username}#{bot.user.discriminator}!")
    await send_log(0x00FF00, "Bot is now online.")
    await send_log(0x00FF00, "p.s. you may need to refresh your Discord client to see slash commands.")
    await bot.tree.sync()


@bot.tree.command(name="askai", description="Ask AI a question")
async def askai(interaction: Interaction) -> None:
    """Ask AI a question command."""
    question = interaction.get_string("question", required=True)
    if not question:
        return

    # Defer response
    await bot.send_interaction_response(interaction, 5)  # DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE
    opt: dict[str, Any] | None = None

    async def reply_func(text: str) -> None:
        nonlocal opt
        opt = await replyer(interaction, text, opt)

    async def edit_func(text: str) -> None:
        nonlocal opt
        opt = await replyer(interaction, text, opt)

    async def error_func(error: str) -> None:
        embed = Embed(title="Error", description=error, color=0xFF0000)
        await bot.edit_interaction_response(interaction, embed=embed)

    await call_ai(str(interaction.user.id), question, reply_func, edit_func, error_func)


@bot.tree.command(name="readhtml", description="Read and decode HTML content from a URL")
async def readhtml(interaction: Interaction) -> None:
    """Read HTML from URL command."""
    url = interaction.get_string("url", required=True)
    if not url:
        return

    # Defer response
    await bot.send_interaction_response(interaction, 5)

    try:
        html_content = await read_html(url)
        if not html_content:
            html_content = "[No content extracted from the HTML page.]"
    except Exception:
        html_content = "[Failed to read or decode HTML content.]"

    await bot.edit_interaction_response(interaction, content=limit_len(html_content))


@bot.tree.command(name="testlongreply", description="Test long reply")
async def testlongreply(interaction: Interaction) -> None:
    """Test long reply command."""
    # Defer response
    await bot.send_interaction_response(interaction, 5)
    
    opt: dict[str, Any] | None = None
    
    # Generate long test string
    test_str = ""
    for i in range(0, 400, 5):
        if i % 100 == 0:
            test_str += f"==[{str(i).zfill(4)}]==----------==========----------==========\n"
        test_str += f"-# [{str(i).zfill(4)}]----------==========----------==========\n"
    
    # Reply with long content
    opt = await replyer(interaction, test_str, opt)
    opt = await replyer(interaction, test_str, opt)


@bot.tree.command(name="set_token", description="Set your OpenAI API token")
async def set_token(interaction: Interaction) -> None:
    """Set OpenAI API token command."""
    # Defer response
    await bot.send_interaction_response(interaction, 5)
    # Build modal
    from libs import ModalBuilder, LabelBuilder, TextInputBuilder

    form = ModalBuilder().setTitle("Set your OpenAI API token").setCustomId("set_openai_token_modal")
    input_comp = TextInputBuilder().setCustomId("openai_token_input").setStyle(1).setPlaceholder("sk-XXXXX...").setRequired(False).setLabel("OpenAI API token (leave blank to remove):")
    label = LabelBuilder().setLabel("OpenAI API token (leave blank to remove):").setDescription("You can get your token from https://platform.openai.com/account/api-keys").setTextInputComponent(input_comp)
    form.addLabelComponents(label)

    # Show modal
    await interaction.show_modal(form)

    # Wait for the modal submit event once
    async def modal_handler(modal_interaction: Interaction) -> None:
        try:
            if not modal_interaction.is_modal_submit():
                return
            if modal_interaction.data.get("custom_id") != "set_openai_token_modal" and modal_interaction.custom_id != "set_openai_token_modal":
                return
            openai_token = modal_interaction.get_text_input_value("openai_token_input") or ""
            if not DB.get(modal_interaction.user.id):
                DB[modal_interaction.user.id] = {}
            if openai_token.strip() == "":
                DB[modal_interaction.user.id].pop("openai_token", None)
                (BASE_DIR.parent / "db.json").write_text(json.dumps(DB), encoding="utf-8")
                await bot.send_interaction_response(modal_interaction, 4, data={"content": "Your OpenAI API token has been removed.", "flags": 64})
                return
            DB[modal_interaction.user.id]["openai_token"] = openai_token.strip()
            (BASE_DIR.parent / "db.json").write_text(json.dumps(DB), encoding="utf-8")
            await bot.send_interaction_response(modal_interaction, 4, data={"content": "Your OpenAI API token has been set successfully.", "flags": 64})
        except Exception as e:
            try:
                await bot.send_interaction_response(modal_interaction, 4, data={"content": "Failed to set token.", "flags": 64})
            except Exception:
                pass

    bot.once(Events.INTERACTION_CREATE, modal_handler)


@bot.tree.command(name="webconculusion", description="make a conculusion of the web page from a URL")
async def webconculusion(interaction: Interaction) -> None:
    """Web page conclusion command."""
    url = interaction.get_string("url", required=True)
    if not url:
        return

    # Defer response
    await bot.send_interaction_response(interaction, 5)

    try:
        html_content = await read_html(url)
    except Exception:
        await bot.edit_interaction_response(interaction, content="[Failed to read or decode HTML content.]")
        return

    async def reply_func(text: str) -> None:
        await bot.edit_interaction_response(interaction, content=limit_len(text))

    async def edit_func(text: str) -> None:
        await bot.edit_interaction_response(interaction, content=limit_len(text))

    async def error_func(error: str) -> None:
        embed = Embed(title="Error", description=error, color=0xFF0000)
        await bot.edit_interaction_response(interaction, embed=embed)

    await call_ai(
        str(interaction.user.id),
        f"make conculusion:\n{html_content}",
        reply_func,
        edit_func,
        error_func,
    )


if __name__ == "__main__":
    try:
        asyncio.run(bot.run(SECRET.get("dc_apikey")))
    except KeyboardInterrupt:
        print("Bot stopped.")
