import discord
from discord.ext import commands, tasks
from discord import app_commands

from dotenv import load_dotenv

import os
import json
from datetime import datetime, timezone, timedelta


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

ENV_FILE = os.path.join(
    BASE_DIR,
    ".env"
)

SCHEDULE_FILE = os.path.join(
    BASE_DIR,
    "schedules.json"
)

ROLE_FILE = os.path.join(
    BASE_DIR,
    "scheduler_roles.json"
)


# ============================================================
# LOAD TOKEN
# ============================================================

load_dotenv(ENV_FILE)

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError(
        "❌ DISCORD_TOKEN could not be read.\n\n"
        f"Python checked:\n{ENV_FILE}\n\n"
        "Make sure your .env contains:\n"
        "DISCORD_TOKEN=YOUR_BOT_TOKEN"
    )
# ============================================================
# TIMEZONE
# ============================================================

# India Standard Time = UTC + 5:30
IST = timezone(
    timedelta(
        hours=5,
        minutes=30
    )
)


# ============================================================
# SETTINGS
# ============================================================

MESSAGES_PER_PAGE = 5

CHECK_INTERVAL = 10


# ============================================================
# BOT
# ============================================================

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ============================================================
# LOAD SCHEDULES
# ============================================================

def load_schedules():

    if not os.path.exists(SCHEDULE_FILE):
        return []

    try:

        with open(
            SCHEDULE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

            if not isinstance(data, list):
                return []

            return data

    except Exception as error:

        print(
            f"⚠️ Could not read schedules.json: {error}"
        )

        return []


def save_schedules():

    try:

        with open(
            SCHEDULE_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                schedules,
                file,
                indent=4
            )

    except Exception as error:

        print(
            f"❌ Could not save schedules: {error}"
        )


schedules = load_schedules()


# ============================================================
# LOAD ROLE SETTINGS
# ============================================================

def load_roles():

    if not os.path.exists(ROLE_FILE):
        return {}

    try:

        with open(
            ROLE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

            if not isinstance(data, dict):
                return {}

            return data

    except Exception as error:

        print(
            f"⚠️ Could not read scheduler_roles.json: {error}"
        )

        return {}


def save_roles():

    try:

        with open(
            ROLE_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                scheduler_roles,
                file,
                indent=4
            )

    except Exception as error:

        print(
            f"❌ Could not save scheduler roles: {error}"
        )


scheduler_roles = load_roles()


# ============================================================
# ROLE HELPERS
# ============================================================

def get_guild_roles(guild_id):

    guild_id = str(guild_id)

    if guild_id not in scheduler_roles:
        scheduler_roles[guild_id] = []

    return scheduler_roles[guild_id]


def has_scheduler_permission(
    interaction: discord.Interaction
):

    if not interaction.guild:
        return False

    # --------------------------------------------------------
    # Server administrators always have access
    # --------------------------------------------------------

    if interaction.user.guild_permissions.administrator:
        return True

    # --------------------------------------------------------
    # Manage Server users always have access
    # --------------------------------------------------------

    if interaction.user.guild_permissions.manage_guild:
        return True

    # --------------------------------------------------------
    # Check configured scheduler roles
    # --------------------------------------------------------

    allowed_roles = get_guild_roles(
        interaction.guild.id
    )

    user_role_ids = {
        str(role.id)
        for role in interaction.user.roles
    }

    return bool(
        user_role_ids.intersection(
            set(allowed_roles)
        )
    )


# ============================================================
# ID SYSTEM
# ============================================================

def get_next_schedule_id():

    if not schedules:
        return 1

    return max(
        schedule["id"]
        for schedule in schedules
    ) + 1


# ============================================================
# TIME FUNCTIONS
# ============================================================

def parse_ist_datetime(
    date_string,
    time_string
):

    try:

        dt = datetime.strptime(
            f"{date_string} {time_string}",
            "%Y-%m-%d %H:%M"
        )

        return dt.replace(
            tzinfo=IST
        )

    except ValueError:

        return None


def timestamp_to_ist(timestamp):

    return datetime.fromtimestamp(
        timestamp,
        tz=IST
    )


def format_datetime(timestamp):

    dt = timestamp_to_ist(
        timestamp
    )

    return dt.strftime(
        "%d %b %Y • %I:%M %p IST"
    )


def format_short_datetime(timestamp):

    dt = timestamp_to_ist(
        timestamp
    )

    return dt.strftime(
        "%d %b • %I:%M %p"
    )


# ============================================================
# REPEAT FUNCTIONS
# ============================================================

def repeat_name(repeat):

    if repeat == "daily":
        return "🔁 Daily"

    if repeat == "weekly":
        return "🔁 Weekly"

    return "▶️ Once"


def next_repeat_time(
    timestamp,
    repeat
):

    if repeat == "daily":

        return timestamp + 86400

    if repeat == "weekly":

        return timestamp + (86400 * 7)

    return None


# ============================================================
# GET GUILD SCHEDULES
# ============================================================

def get_guild_schedules(guild_id):

    return [
        schedule
        for schedule in schedules
        if schedule["guild_id"] == guild_id
    ]


# ============================================================
# SCHEDULER EMBED
# ============================================================

def create_scheduler_embed(
    guild_id,
    page=0
):

    guild_schedules = get_guild_schedules(
        guild_id
    )

    total_pages = max(
        1,
        (
            len(guild_schedules)
            + MESSAGES_PER_PAGE
            - 1
        )
        // MESSAGES_PER_PAGE
    )

    page = max(
        0,
        min(
            page,
            total_pages - 1
        )
    )

    start = (
        page
        * MESSAGES_PER_PAGE
    )

    end = (
        start
        + MESSAGES_PER_PAGE
    )

    page_items = guild_schedules[
        start:end
    ]

    embed = discord.Embed(
        title="📅 Message Scheduler",
        description=(
            "Manage your scheduled messages "
            "using the buttons below.\n\n"
            "🇮🇳 **All times are in IST.**"
        ),
        color=discord.Color.blurple()
    )

    if not page_items:

        embed.add_field(
            name="📭 No Scheduled Messages",
            value=(
                "There are no scheduled messages yet.\n\n"
                "Click **➕ Add Message** to create one."
            ),
            inline=False
        )

    else:

        for schedule in page_items:

            message = schedule["message"]

            if len(message) > 180:

                message = (
                    message[:177]
                    + "..."
                )

            embed.add_field(
                name=(
                    f"#{schedule['id']} • "
                    f"{repeat_name(schedule.get('repeat', 'once'))}"
                ),
                value=(
                    f"📢 <#{schedule['channel_id']}>\n"
                    f"🕐 {format_datetime(schedule['timestamp'])}\n"
                    f"📝 {message}"
                ),
                inline=False
            )

    embed.set_footer(
        text=(
            f"Page {page + 1}/{total_pages} • "
            f"{len(guild_schedules)} scheduled message(s)"
        )
    )

    return embed, total_pages


# ============================================================
# REFRESH PANEL
# ============================================================

async def refresh_panel(
    interaction,
    page
):

    embed, _ = create_scheduler_embed(
        interaction.guild.id,
        page
    )

    await interaction.response.edit_message(
        embed=embed,
        view=SchedulerPanel(
            interaction.guild.id,
            page
        )
    )


# ============================================================
# SCHEDULER PANEL
# ============================================================

class SchedulerPanel(
    discord.ui.View
):

    def __init__(
        self,
        guild_id,
        page=0
    ):

        super().__init__(
            timeout=600
        )

        self.guild_id = guild_id
        self.page = page

        guild_schedules = get_guild_schedules(
            guild_id
        )

        total_pages = max(
            1,
            (
                len(guild_schedules)
                + MESSAGES_PER_PAGE
                - 1
            )
            // MESSAGES_PER_PAGE
        )

        self.previous_button.disabled = (
            page <= 0
        )

        self.next_button.disabled = (
            page >= total_pages - 1
        )

    # ========================================================
    # PREVIOUS
    # ========================================================

    @discord.ui.button(
        label="Previous",
        emoji="◀️",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def previous_button(
        self,
        interaction,
        button
    ):

        if not has_scheduler_permission(
            interaction
        ):

            await interaction.response.send_message(
                "❌ You don't have permission to use the scheduler.",
                ephemeral=True
            )

            return

        await refresh_panel(
            interaction,
            self.page - 1
        )

    # ========================================================
    # NEXT
    # ========================================================

    @discord.ui.button(
        label="Next",
        emoji="▶️",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def next_button(
        self,
        interaction,
        button
    ):

        if not has_scheduler_permission(
            interaction
        ):

            await interaction.response.send_message(
                "❌ You don't have permission to use the scheduler.",
                ephemeral=True
            )

            return

        await refresh_panel(
            interaction,
            self.page + 1
        )

    # ========================================================
    # ADD
    # ========================================================

    @discord.ui.button(
        label="Add Message",
        emoji="➕",
        style=discord.ButtonStyle.success,
        row=1
    )
    async def add_button(
        self,
        interaction,
        button
    ):

        if not has_scheduler_permission(
            interaction
        ):

            await interaction.response.send_message(
                "❌ You don't have permission to schedule messages.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "📢 **Choose the channel:**",
            view=AddScheduleChannelView(
                interaction.guild.id
            ),
            ephemeral=True
        )

    # ========================================================
    # EDIT
    # ========================================================

    @discord.ui.button(
        label="Edit",
        emoji="✏️",
        style=discord.ButtonStyle.primary,
        row=1
    )
    async def edit_button(
        self,
        interaction,
        button
    ):

        if not has_scheduler_permission(
            interaction
        ):

            await interaction.response.send_message(
                "❌ You don't have permission.",
                ephemeral=True
            )

            return

        guild_schedules = get_guild_schedules(
            interaction.guild.id
        )

        if not guild_schedules:

            await interaction.response.send_message(
                "❌ There are no scheduled messages.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "✏️ **Choose the message to edit:**",
            view=EditScheduleSelectView(
                interaction.guild.id
            ),
            ephemeral=True
        )

    # ========================================================
    # DELETE
    # ========================================================

    @discord.ui.button(
        label="Delete",
        emoji="🗑️",
        style=discord.ButtonStyle.danger,
        row=1
    )
    async def delete_button(
        self,
        interaction,
        button
    ):

        if not has_scheduler_permission(
            interaction
        ):

            await interaction.response.send_message(
                "❌ You don't have permission.",
                ephemeral=True
            )

            return

        guild_schedules = get_guild_schedules(
            interaction.guild.id
        )

        if not guild_schedules:

            await interaction.response.send_message(
                "❌ There are no scheduled messages.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "🗑️ **Choose the message to delete:**",
            view=DeleteScheduleSelectView(
                interaction.guild.id
            ),
            ephemeral=True
        )

    # ========================================================
    # REFRESH
    # ========================================================

    @discord.ui.button(
        label="Refresh",
        emoji="🔄",
        style=discord.ButtonStyle.secondary,
        row=2
    )
    async def refresh_button(
        self,
        interaction,
        button
    ):

        if not has_scheduler_permission(
            interaction
        ):

            await interaction.response.send_message(
                "❌ You don't have permission.",
                ephemeral=True
            )

            return

        embed, _ = create_scheduler_embed(
            interaction.guild.id,
            self.page
        )

        await interaction.response.edit_message(
            embed=embed,
            view=SchedulerPanel(
                interaction.guild.id,
                self.page
            )
        )


# ============================================================
# ADD CHANNEL VIEW
# ============================================================

class AddScheduleChannelView(
    discord.ui.View
):

    def __init__(
        self,
        guild_id
    ):

        super().__init__(
            timeout=300
        )

        self.guild_id = guild_id

        self.channel_id = None

        self.repeat_type = "once"

        # ----------------------------------------------------
        # CHANNEL SELECTOR
        # ----------------------------------------------------

        self.channel_selector = discord.ui.ChannelSelect(
            placeholder="📢 Select a channel...",
            channel_types=[
                discord.ChannelType.text,
                discord.ChannelType.news
            ],
            min_values=1,
            max_values=1,
            row=0
        )

        self.channel_selector.callback = (
            self.channel_selected
        )

        self.add_item(
            self.channel_selector
        )

        # ----------------------------------------------------
        # REPEAT SELECTOR
        # ----------------------------------------------------

        self.repeat_selector = discord.ui.Select(
            placeholder="🔁 How often should it repeat?",
            options=[
                discord.SelectOption(
                    label="Once",
                    value="once",
                    emoji="▶️",
                    description="Send the message one time."
                ),
                discord.SelectOption(
                    label="Every day",
                    value="daily",
                    emoji="📅",
                    description="Send it every day."
                ),
                discord.SelectOption(
                    label="Every week",
                    value="weekly",
                    emoji="🗓️",
                    description="Send it every week."
                )
            ],
            row=1
        )

        self.repeat_selector.callback = (
            self.repeat_selected
        )

        self.add_item(
            self.repeat_selector
        )

        # ----------------------------------------------------
        # CONTINUE BUTTON
        # ----------------------------------------------------

        self.continue_button = discord.ui.Button(
            label="Continue",
            emoji="➡️",
            style=discord.ButtonStyle.success,
            disabled=True,
            row=2
        )

        self.continue_button.callback = (
            self.continue_pressed
        )

        self.add_item(
            self.continue_button
        )

    # ========================================================
    # CHANNEL SELECTED
    # ========================================================

    async def channel_selected(
        self,
        interaction
    ):

        self.channel_id = (
            self.channel_selector.values[0].id
        )

        self.continue_button.disabled = False

        await interaction.response.edit_message(
            content=(
                f"📢 **Selected:** <#{self.channel_id}>\n\n"
                "🔁 Choose how often the message should "
                "be sent.\n\n"
                "Then click **➡️ Continue**."
            ),
            view=self
        )

    # ========================================================
    # REPEAT SELECTED
    # ========================================================

    async def repeat_selected(
        self,
        interaction
    ):

        self.repeat_type = (
            self.repeat_selector.values[0]
        )

        await interaction.response.defer()

    # ========================================================
    # CONTINUE
    # ========================================================

    async def continue_pressed(
        self,
        interaction
    ):

        if not self.channel_id:

            await interaction.response.send_message(
                "❌ Please select a channel first.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            AddScheduleModal(
                self.channel_id,
                self.repeat_type
            )
        )


# ============================================================
# ADD MESSAGE MODAL
# ============================================================

class AddScheduleModal(
    discord.ui.Modal,
    title="Add Scheduled Message"
):

    message = discord.ui.TextInput(
        label="Message",
        placeholder="What should the bot send?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )

    date = discord.ui.TextInput(
        label="Date (IST)",
        placeholder="YYYY-MM-DD  e.g. 2026-08-25",
        required=True,
        max_length=10
    )

    time = discord.ui.TextInput(
        label="Time (IST)",
        placeholder="HH:MM  e.g. 20:30",
        required=True,
        max_length=5
    )

    def __init__(
        self,
        channel_id,
        repeat_type
    ):

        super().__init__()

        self.channel_id = channel_id

        self.repeat_type = repeat_type

    async def on_submit(
        self,
        interaction
    ):

        dt = parse_ist_datetime(
            self.date.value.strip(),
            self.time.value.strip()
        )

        if not dt:

            await interaction.response.send_message(
                (
                    "❌ Invalid date/time.\n\n"
                    "Date must be `YYYY-MM-DD`\n"
                    "Time must be `HH:MM`"
                ),
                ephemeral=True
            )

            return

        if (
            dt.timestamp()
            <= datetime.now(
                timezone.utc
            ).timestamp()
        ):

            await interaction.response.send_message(
                "❌ That date/time has already passed.",
                ephemeral=True
            )

            return

        channel = interaction.guild.get_channel(
            self.channel_id
        )

        if not channel:

            await interaction.response.send_message(
                "❌ I couldn't find that channel.",
                ephemeral=True
            )

            return

        schedule = {

            "id": get_next_schedule_id(),

            "guild_id": interaction.guild.id,

            "channel_id": channel.id,

            "message": self.message.value,

            "timestamp": dt.timestamp(),

            "repeat": self.repeat_type
        }

        schedules.append(
            schedule
        )

        save_schedules()

        await interaction.response.send_message(
            (
                "✅ **Message scheduled!**\n\n"
                f"🆔 ID: **#{schedule['id']}**\n"
                f"📢 Channel: {channel.mention}\n"
                f"🕐 Time: **{format_datetime(schedule['timestamp'])}**\n"
                f"🔁 Repeat: **{repeat_name(self.repeat_type)}**"
            ),
            ephemeral=True
        )


# ============================================================
# EDIT SELECT
# ============================================================

class EditScheduleSelect(
    discord.ui.Select
):

    def __init__(
        self,
        guild_id
    ):

        self.guild_id = guild_id

        guild_schedules = get_guild_schedules(
            guild_id
        )

        options = []

        for schedule in guild_schedules[:25]:

            message = schedule["message"]

            if len(message) > 70:

                message = (
                    message[:67]
                    + "..."
                )

            options.append(
                discord.SelectOption(
                    label=(
                        f"#{schedule['id']} • "
                        f"{format_short_datetime(schedule['timestamp'])}"
                    ),
                    description=message,
                    value=str(
                        schedule["id"]
                    ),
                    emoji="✏️"
                )
            )

        super().__init__(
            placeholder="Choose a scheduled message...",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(
        self,
        interaction
    ):

        schedule_id = int(
            self.values[0]
        )

        schedule = next(
            (
                item
                for item in schedules
                if item["id"] == schedule_id
                and item["guild_id"]
                == self.guild_id
            ),
            None
        )

        if not schedule:

            await interaction.response.send_message(
                "❌ Schedule not found.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            EditScheduleModal(
                schedule
            )
        )


class EditScheduleSelectView(
    discord.ui.View
):

    def __init__(
        self,
        guild_id
    ):

        super().__init__(
            timeout=300
        )

        self.add_item(
            EditScheduleSelect(
                guild_id
            )
        )


# ============================================================
# EDIT MODAL
# ============================================================

class EditScheduleModal(
    discord.ui.Modal,
    title="Edit Scheduled Message"
):

    message = discord.ui.TextInput(
        label="Message",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )

    date = discord.ui.TextInput(
        label="Date (IST)",
        placeholder="YYYY-MM-DD",
        required=True,
        max_length=10
    )

    time = discord.ui.TextInput(
        label="Time (IST)",
        placeholder="HH:MM",
        required=True,
        max_length=5
    )

    def __init__(
        self,
        schedule
    ):

        super().__init__()

        self.schedule = schedule

        self.message.default = (
            schedule["message"]
        )

        dt = timestamp_to_ist(
            schedule["timestamp"]
        )

        self.date.default = (
            dt.strftime("%Y-%m-%d")
        )

        self.time.default = (
            dt.strftime("%H:%M")
        )

    async def on_submit(
        self,
        interaction
    ):

        dt = parse_ist_datetime(
            self.date.value.strip(),
            self.time.value.strip()
        )

        if not dt:

            await interaction.response.send_message(
                "❌ Invalid date/time.",
                ephemeral=True
            )

            return

        if (
            dt.timestamp()
            <= datetime.now(
                timezone.utc
            ).timestamp()
        ):

            await interaction.response.send_message(
                "❌ That date/time has already passed.",
                ephemeral=True
            )

            return

        self.schedule["message"] = (
            self.message.value
        )

        self.schedule["timestamp"] = (
            dt.timestamp()
        )

        save_schedules()

        await interaction.response.send_message(
            (
                f"✅ **Schedule #{self.schedule['id']} updated!**\n\n"
                f"🕐 New time: "
                f"**{format_datetime(self.schedule['timestamp'])}**"
            ),
            ephemeral=True
        )


# ============================================================
# DELETE SELECT
# ============================================================

class DeleteScheduleSelect(
    discord.ui.Select
):

    def __init__(
        self,
        guild_id
    ):

        self.guild_id = guild_id

        guild_schedules = get_guild_schedules(
            guild_id
        )

        options = []

        for schedule in guild_schedules[:25]:

            message = schedule["message"]

            if len(message) > 70:

                message = (
                    message[:67]
                    + "..."
                )

            options.append(
                discord.SelectOption(
                    label=(
                        f"Delete #{schedule['id']}"
                    ),
                    description=message,
                    value=str(
                        schedule["id"]
                    ),
                    emoji="🗑️"
                )
            )

        super().__init__(
            placeholder="Choose a message to delete...",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(
        self,
        interaction
    ):

        schedule_id = int(
            self.values[0]
        )

        schedule = next(
            (
                item
                for item in schedules
                if item["id"] == schedule_id
                and item["guild_id"]
                == self.guild_id
            ),
            None
        )

        if not schedule:

            await interaction.response.send_message(
                "❌ Schedule not found.",
                ephemeral=True
            )

            return

        schedules.remove(
            schedule
        )

        save_schedules()

        await interaction.response.send_message(
            f"🗑️ **Schedule #{schedule_id} deleted.**",
            ephemeral=True
        )


class DeleteScheduleSelectView(
    discord.ui.View
):

    def __init__(
        self,
        guild_id
    ):

        super().__init__(
            timeout=300
        )

        self.add_item(
            DeleteScheduleSelect(
                guild_id
            )
        )


# ============================================================
# SCHEDULER LOOP
# ============================================================

@tasks.loop(
    seconds=CHECK_INTERVAL
)
async def scheduler_loop():

    now = datetime.now(
        timezone.utc
    ).timestamp()

    due_schedules = [
        schedule
        for schedule in schedules
        if schedule["timestamp"] <= now
    ]

    changed = False

    for schedule in due_schedules:

        channel = bot.get_channel(
            schedule["channel_id"]
        )

        # ----------------------------------------------------
        # SEND
        # ----------------------------------------------------

        if channel:

            try:

                await channel.send(
                    schedule["message"]
                )

                print(
                    f"✅ Sent scheduled message "
                    f"#{schedule['id']}"
                )

            except discord.Forbidden:

                print(
                    f"❌ No permission to send in "
                    f"channel {schedule['channel_id']}"
                )

            except discord.HTTPException as error:

                print(
                    f"❌ Discord error: {error}"
                )

        else:

            print(
                f"⚠️ Channel {schedule['channel_id']} "
                f"could not be found."
            )

        # ----------------------------------------------------
        # REPEAT
        # ----------------------------------------------------

        repeat = schedule.get(
            "repeat",
            "once"
        )

        next_timestamp = next_repeat_time(
            schedule["timestamp"],
            repeat
        )

        if next_timestamp:

            while next_timestamp <= now:

                next_timestamp = next_repeat_time(
                    next_timestamp,
                    repeat
                )

            schedule["timestamp"] = (
                next_timestamp
            )

        else:

            schedules.remove(
                schedule
            )

        changed = True

    if changed:

        save_schedules()


@scheduler_loop.before_loop
async def before_scheduler_loop():

    await bot.wait_until_ready()


# ============================================================
# BOT READY
# ============================================================

@bot.event
async def on_ready():

    print(
        "=========================================="
    )

    print(
        f"✅ Logged in as {bot.user}"
    )

    print(
        f"🆔 Bot ID: {bot.user.id}"
    )

    print(
        f"📅 Loaded schedules: {len(schedules)}"
    )

    print(
        "🇮🇳 Timezone: IST (UTC+5:30)"
    )

    print(
        "=========================================="
    )

    try:

        synced = await bot.tree.sync()

        print(
            f"✅ Synced {len(synced)} slash command(s)"
        )

    except Exception as error:

        print(
            f"❌ Slash command sync error: {error}"
        )

    if not scheduler_loop.is_running():

        scheduler_loop.start()


# ============================================================
# /SCHEDULER
# ============================================================

@bot.tree.command(
    name="scheduler",
    description="Open the scheduled message manager."
)
async def scheduler(
    interaction: discord.Interaction
):

    if not has_scheduler_permission(
        interaction
    ):

        await interaction.response.send_message(
            (
                "❌ **You don't have permission to use "
                "the message scheduler.**\n\n"
                "Ask a server administrator to give "
                "you the scheduler role."
            ),
            ephemeral=True
        )

        return

    embed, _ = create_scheduler_embed(
        interaction.guild.id
    )

    # Ephemeral means only the person opening it
    # can see the scheduler panel.

    await interaction.response.send_message(
        embed=embed,
        view=SchedulerPanel(
            interaction.guild.id
        ),
        ephemeral=True
    )


# ============================================================
# SCHEDULER ROLE GROUP
# ============================================================

scheduler_role_group = app_commands.Group(
    name="scheduler-role",
    description="Manage who can use the scheduler."
)


# ============================================================
# /SCHEDULER-ROLE ADD
# ============================================================

@scheduler_role_group.command(
    name="add",
    description="Allow a role to use the scheduler."
)
@app_commands.describe(
    role="The role that should be allowed to schedule messages."
)
async def scheduler_role_add(
    interaction: discord.Interaction,
    role: discord.Role
):

    # Only Manage Server can change scheduler roles.

    if not interaction.guild:

        await interaction.response.send_message(
            "❌ This command can only be used in a server.",
            ephemeral=True
        )

        return

    if not interaction.user.guild_permissions.manage_guild:

        await interaction.response.send_message(
            (
                "❌ You need the **Manage Server** "
                "permission to manage scheduler roles."
            ),
            ephemeral=True
        )

        return

    guild_id = str(
        interaction.guild.id
    )

    if guild_id not in scheduler_roles:

        scheduler_roles[guild_id] = []

    role_id = str(
        role.id
    )

    if role_id in scheduler_roles[guild_id]:

        await interaction.response.send_message(
            f"ℹ️ {role.mention} already has scheduler access.",
            ephemeral=True
        )

        return

    scheduler_roles[guild_id].append(
        role_id
    )

    save_roles()

    await interaction.response.send_message(
        (
            f"✅ {role.mention} can now use the "
            "message scheduler."
        ),
        ephemeral=True
    )


# ============================================================
# /SCHEDULER-ROLE REMOVE
# ============================================================

@scheduler_role_group.command(
    name="remove",
    description="Remove a role's scheduler access."
)
@app_commands.describe(
    role="The role that should no longer use the scheduler."
)
async def scheduler_role_remove(
    interaction: discord.Interaction,
    role: discord.Role
):

    if not interaction.guild:

        await interaction.response.send_message(
            "❌ This command can only be used in a server.",
            ephemeral=True
        )

        return

    if not interaction.user.guild_permissions.manage_guild:

        await interaction.response.send_message(
            (
                "❌ You need the **Manage Server** "
                "permission to manage scheduler roles."
            ),
            ephemeral=True
        )

        return

    guild_id = str(
        interaction.guild.id
    )

    role_id = str(
        role.id
    )

    if (
        guild_id not in scheduler_roles
        or role_id not in scheduler_roles[guild_id]
    ):

        await interaction.response.send_message(
            f"ℹ️ {role.mention} isn't a scheduler role.",
            ephemeral=True
        )

        return

    scheduler_roles[guild_id].remove(
        role_id
    )

    save_roles()

    await interaction.response.send_message(
        (
            f"✅ {role.mention} can no longer use "
            "the message scheduler."
        ),
        ephemeral=True
    )


# ============================================================
# /SCHEDULER-ROLE LIST
# ============================================================

@scheduler_role_group.command(
    name="list",
    description="Show the roles that can use the scheduler."
)
async def scheduler_role_list(
    interaction: discord.Interaction
):

    if not interaction.guild:

        await interaction.response.send_message(
            "❌ This command can only be used in a server.",
            ephemeral=True
        )

        return

    if not interaction.user.guild_permissions.manage_guild:

        await interaction.response.send_message(
            (
                "❌ You need the **Manage Server** "
                "permission to view scheduler roles."
            ),
            ephemeral=True
        )

        return

    allowed_roles = get_guild_roles(
        interaction.guild.id
    )

    embed = discord.Embed(
        title="Scheduler Roles",
        color=discord.Color.blurple()
    )

    if not allowed_roles:

        embed.description = (
            "No scheduler roles have been configured.\n\n"
            "Only users with **Manage Server** or "
            "**Administrator** can currently use the scheduler."
        )

    else:

        role_mentions = []

        for role_id in allowed_roles:

            role = interaction.guild.get_role(
                int(role_id)
            )

            if role:

                role_mentions.append(
                    role.mention
                )

        if role_mentions:

            embed.description = (
                "The following roles can use the scheduler:\n\n"
                + "\n".join(
                    f"• {role}"
                    for role in role_mentions
                )
            )

        else:

            embed.description = (
                "The configured scheduler roles no longer exist."
            )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# ADD ROLE GROUP TO TREE
# ============================================================

bot.tree.add_command(
    scheduler_role_group
)


# ============================================================
# GLOBAL ERROR HANDLER
# ============================================================

@bot.event
async def on_error(
    event,
    *args,
    **kwargs
):

    print(
        f"❌ Error in event: {event}"
    )


# ============================================================
# START
# ============================================================

print(
    "🚀 Starting Message Scheduler..."
)

bot.run(TOKEN)