import os
import discord
from discord.ext import commands
from discord import app_commands

# ─────────────────────────────────────────────
#  ROLE IDs
# ─────────────────────────────────────────────
ROLES = {
    "middleman":          1488599831957078106,
    "senior_middleman":   1481040491821793521,
    "middleman_manager":  1481040491012423784,
    "moderator":          1481040488319680533,
    "head_mod":           1481040487459852390,
    "lead_coordinator":   1481040479880478892,
    "administrator":      1487553808748773528,
    "co_founder":         1495416016954593311,
    "op_manager":         1481040477695381650,
    "chief":              1487844624583360665,
    "team_lead":          1487830791831683285,
    "lead_commander":     1494198661079629915,
    "director":           1487511134629007360,
    "president":          1481040472309891092,
}

# Ordered hierarchy from lowest to highest
HIERARCHY = [
    "middleman",
    "senior_middleman",
    "middleman_manager",
    "moderator",
    "head_mod",
    "lead_coordinator",
    "administrator",
    "co_founder",
    "op_manager",
    "chief",
    "team_lead",
    "lead_commander",
    "director",
    "president",
]

# What each staff role can promote UP TO (inclusive)
PROMOTE_PERMISSIONS = {
    "administrator":  ["middleman"],
    "co_founder":     ["middleman", "senior_middleman"],
    "op_manager":     HIERARCHY[:HIERARCHY.index("co_founder") + 1],
    "chief":          HIERARCHY[:HIERARCHY.index("op_manager") + 1],
    "team_lead":      HIERARCHY[:HIERARCHY.index("chief") + 1],
    "lead_commander": HIERARCHY[:HIERARCHY.index("team_lead") + 1],
    "director":       HIERARCHY[:HIERARCHY.index("lead_commander") + 1],
    "president":      HIERARCHY[:HIERARCHY.index("director") + 1],
}

DISPLAY_NAMES = {
    "middleman":         "Middleman",
    "senior_middleman":  "Senior Middleman",
    "middleman_manager": "Middleman Manager",
    "moderator":         "Moderator",
    "head_mod":          "Head Mod",
    "lead_coordinator":  "Lead Coordinator",
    "administrator":     "Administrator",
    "co_founder":        "Co-Founder",
    "op_manager":        "Operation Manager",
    "chief":             "Chief",
    "team_lead":         "Team Lead",
    "lead_commander":    "Lead Commander",
    "director":          "Director",
    "president":         "President",
}

STAFF_EMOJI = {
    "administrator":  "🔴",
    "co_founder":     "🟠",
    "op_manager":     "🟡",
    "chief":          "🟢",
    "team_lead":      "🔵",
    "lead_commander": "🟣",
    "director":       "⚫",
    "president":      "👑",
}

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def get_staff_role(member: discord.Member) -> str | None:
    """Return the highest staff role key the member holds, or None."""
    member_role_ids = {r.id for r in member.roles}
    for key in reversed(HIERARCHY):
        if key in PROMOTE_PERMISSIONS and ROLES[key] in member_role_ids:
            return key
    return None

def can_promote(staff_key: str, target_key: str) -> bool:
    allowed = PROMOTE_PERMISSIONS.get(staff_key, [])
    return target_key in allowed

# ─────────────────────────────────────────────
#  BOT SETUP
# ─────────────────────────────────────────────

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ─────────────────────────────────────────────
#  /managerole  — info embed
# ─────────────────────────────────────────────

@tree.command(name="managerole", description="View the full role hierarchy and promotion permissions.")
async def managerole(interaction: discord.Interaction):
    embed = discord.Embed(
        title="👑 Role Hierarchy & Promotion Permissions",
        color=0x2b2d31,
    )

    for staff_key, allowed_keys in PROMOTE_PERMISSIONS.items():
        role_id  = ROLES[staff_key]
        emoji    = STAFF_EMOJI.get(staff_key, "•")
        label    = DISPLAY_NAMES[staff_key]
        mentions = " ".join(f"<@&{ROLES[k]}>" for k in allowed_keys)
        embed.add_field(
            name=f"{emoji} {label} — <@&{role_id}>",
            value=f"Can promote: {mentions}" if mentions else "No promote permissions.",
            inline=False,
        )

    embed.add_field(
        name="─────────────────",
        value="**Promotable roles (low → high)**\n" +
              "\n".join(f"`{i+1}.` <@&{ROLES[k]}> — {DISPLAY_NAMES[k]}"
                        for i, k in enumerate(HIERARCHY)),
        inline=False,
    )
    embed.set_footer(text="Only staff listed above can use /promote.")
    await interaction.response.send_message(embed=embed)

# ─────────────────────────────────────────────
#  /promote  — give a role to a member
# ─────────────────────────────────────────────

@tree.command(name="promote", description="Promote a member to a role (subject to your permissions).")
@app_commands.describe(
    member="The member to promote.",
    role="The role to assign.",
)
async def promote(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    staff_key = get_staff_role(interaction.user)

    if staff_key is None:
        await interaction.response.send_message(
            "❌ You don't have a staff role that allows promotions.", ephemeral=True
        )
        return

    role_key = next((k for k, rid in ROLES.items() if rid == role.id), None)
    if role_key is None:
        await interaction.response.send_message(
            "❌ That role is not part of the managed hierarchy.", ephemeral=True
        )
        return

    if not can_promote(staff_key, role_key):
        max_allowed = PROMOTE_PERMISSIONS[staff_key][-1] if PROMOTE_PERMISSIONS[staff_key] else "none"
        await interaction.response.send_message(
            f"❌ Your role (`{DISPLAY_NAMES[staff_key]}`) cannot promote to `{DISPLAY_NAMES[role_key]}`.\n"
            f"Your highest promotable role is `{DISPLAY_NAMES[max_allowed]}`.",
            ephemeral=True,
        )
        return

    if role in member.roles:
        await interaction.response.send_message(
            f"⚠️ {member.mention} already has {role.mention}.", ephemeral=True
        )
        return

    try:
        await member.add_roles(role, reason=f"Promoted by {interaction.user} ({DISPLAY_NAMES[staff_key]})")
        embed = discord.Embed(
            title="✅ Promotion Successful",
            description=f"{member.mention} has been promoted to {role.mention}.",
            color=0x57f287,
        )
        embed.set_footer(text=f"Promoted by {interaction.user.display_name} ({DISPLAY_NAMES[staff_key]})")
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to assign that role. Make sure my role is above it in the server settings.",
            ephemeral=True,
        )

# ─────────────────────────────────────────────
#  /demote  — remove a role from a member
# ─────────────────────────────────────────────

@tree.command(name="demote", description="Demote a member by removing a managed role.")
@app_commands.describe(
    member="The member to demote.",
    role="The role to remove.",
)
async def demote(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    staff_key = get_staff_role(interaction.user)

    if staff_key is None:
        await interaction.response.send_message(
            "❌ You don't have a staff role that allows demotions.", ephemeral=True
        )
        return

    role_key = next((k for k, rid in ROLES.items() if rid == role.id), None)
    if role_key is None:
        await interaction.response.send_message(
            "❌ That role is not part of the managed hierarchy.", ephemeral=True
        )
        return

    if not can_promote(staff_key, role_key):
        await interaction.response.send_message(
            f"❌ You don't have permission to manage `{DISPLAY_NAMES[role_key]}`.", ephemeral=True
        )
        return

    if role not in member.roles:
        await interaction.response.send_message(
            f"⚠️ {member.mention} doesn't have {role.mention}.", ephemeral=True
        )
        return

    try:
        await member.remove_roles(role, reason=f"Demoted by {interaction.user} ({DISPLAY_NAMES[staff_key]})")
        embed = discord.Embed(
            title="🔻 Demotion Successful",
            description=f"{member.mention} has been removed from {role.mention}.",
            color=0xed4245,
        )
        embed.set_footer(text=f"Demoted by {interaction.user.display_name} ({DISPLAY_NAMES[staff_key]})")
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to remove that role.",
            ephemeral=True,
        )

# ─────────────────────────────────────────────
#  STARTUP
# ─────────────────────────────────────────────

@bot.event
async def on_ready():
    try:
        synced = await tree.sync()
        print(f"✅ Logged in as {bot.user} — synced {len(synced)} global slash command(s).")
    except Exception as e:
        print(f"❌ Failed to sync slash commands: {e}")

# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN environment variable is not set. "
            "Set it before running: export DISCORD_TOKEN=your_token_here"
        )
    bot.run(TOKEN)
