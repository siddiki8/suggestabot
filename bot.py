import discord
from discord import app_commands
import sqlite3
import os
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = os.environ.get("DATA_DIR", ".")
DB_PATH = os.path.join(DATA_DIR, "suggestions.db")


@contextmanager
def get_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS suggestions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id    TEXT NOT NULL,
                user_id     TEXT NOT NULL,
                user_name   TEXT NOT NULL,
                movie_name  TEXT NOT NULL,
                is_priority INTEGER NOT NULL DEFAULT 0,
                UNIQUE(guild_id, user_id, movie_name)
            )
        """)


# ── bot setup ────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


@bot.event
async def on_ready():
    init_db()
    await tree.sync()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")


# ── /suggest ─────────────────────────────────────────────────────────────────

@tree.command(name="suggest", description="Add up to 10 movies to your suggestion list at once")
@app_commands.describe(
    movie1="Movie 1",
    movie2="Movie 2",
    movie3="Movie 3",
    movie4="Movie 4",
    movie5="Movie 5",
    movie6="Movie 6",
    movie7="Movie 7",
    movie8="Movie 8",
    movie9="Movie 9",
    movie10="Movie 10",
)
async def suggest(
    interaction: discord.Interaction,
    movie1: str,
    movie2: str | None = None,
    movie3: str | None = None,
    movie4: str | None = None,
    movie5: str | None = None,
    movie6: str | None = None,
    movie7: str | None = None,
    movie8: str | None = None,
    movie9: str | None = None,
    movie10: str | None = None,
):
    if not interaction.guild_id:
        await interaction.response.send_message(
            "This command can only be used inside a server.", ephemeral=True
        )
        return

    guild_id = str(interaction.guild_id)
    user_id = str(interaction.user.id)
    user_name = interaction.user.display_name

    raw = [movie1, movie2, movie3, movie4, movie5, movie6, movie7, movie8, movie9, movie10]
    movies = [m.strip() for m in raw if m and m.strip()]

    added: list[str] = []
    dupes: list[str] = []

    with get_db() as conn:
        for movie_name in movies:
            existing = conn.execute(
                "SELECT id FROM suggestions WHERE guild_id = ? AND user_id = ? AND LOWER(movie_name) = LOWER(?)",
                (guild_id, user_id, movie_name),
            ).fetchone()
            if existing:
                dupes.append(movie_name)
            else:
                conn.execute(
                    "INSERT INTO suggestions (guild_id, user_id, user_name, movie_name) VALUES (?, ?, ?, ?)",
                    (guild_id, user_id, user_name, movie_name),
                )
                added.append(movie_name)
        # Keep display name fresh
        conn.execute(
            "UPDATE suggestions SET user_name = ? WHERE guild_id = ? AND user_id = ?",
            (user_name, guild_id, user_id),
        )

    lines: list[str] = []
    if added:
        lines.append("Added 🎬\n" + "\n".join(f"• {m}" for m in added))
    if dupes:
        lines.append("Already in your list\n" + "\n".join(f"• {m}" for m in dupes))

    await interaction.response.send_message("\n\n".join(lines), ephemeral=True)


# ── /suggestions ──────────────────────────────────────────────────────────────

@tree.command(name="suggestions", description="See all suggested movies for this server")
async def suggestions(interaction: discord.Interaction):
    if not interaction.guild_id:
        await interaction.response.send_message(
            "This command can only be used inside a server.", ephemeral=True
        )
        return

    guild_id = str(interaction.guild_id)

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT user_id, user_name, movie_name, is_priority
            FROM   suggestions
            WHERE  guild_id = ?
            ORDER  BY user_id, is_priority DESC, movie_name COLLATE NOCASE
            """,
            (guild_id,),
        ).fetchall()

    if not rows:
        await interaction.response.send_message(
            "No suggestions yet! Use `/suggest` to add a movie."
        )
        return

    # Group by user_id; user_name is only for display
    seen: list[str] = []
    users: dict[str, dict] = {}
    for row in rows:
        uid = row["user_id"]
        if uid not in users:
            users[uid] = {"name": row["user_name"], "movies": []}
            seen.append(uid)
        entry = (
            f"⭐ **{row['movie_name']}**"
            if row["is_priority"]
            else f"• {row['movie_name']}"
        )
        users[uid]["movies"].append(entry)

    embed = discord.Embed(title="🎬 Movie Suggestions", color=discord.Color.blue())
    for uid in seen:
        value = "\n".join(users[uid]["movies"])
        # Discord field value cap is 1024 chars
        if len(value) > 1024:
            value = value[:1020] + "\n…"
        embed.add_field(name=users[uid]["name"], value=value, inline=False)

    await interaction.response.send_message(embed=embed)


# ── /prio ─────────────────────────────────────────────────────────────────────

@tree.command(name="prio", description="Set (or remove) your priority movie")
async def prio(interaction: discord.Interaction):
    if not interaction.guild_id:
        await interaction.response.send_message(
            "This command can only be used inside a server.", ephemeral=True
        )
        return

    guild_id = str(interaction.guild_id)
    user_id = str(interaction.user.id)

    with get_db() as conn:
        movies = conn.execute(
            """
            SELECT movie_name, is_priority
            FROM   suggestions
            WHERE  guild_id = ? AND user_id = ?
            ORDER  BY movie_name COLLATE NOCASE
            """,
            (guild_id, user_id),
        ).fetchall()

    if not movies:
        await interaction.response.send_message(
            "You haven't suggested any movies yet. Use `/suggest` to add one.",
            ephemeral=True,
        )
        return

    current_prio = next((m["movie_name"] for m in movies if m["is_priority"]), None)

    embed = discord.Embed(
        title="⭐ Set Your Priority Movie",
        description=(
            "Select a movie to highlight it in `/suggestions`.\n"
            "Clicking your current priority will remove it."
        ),
        color=discord.Color.gold(),
    )
    embed.add_field(
        name="Current Priority",
        value=f"⭐ {current_prio}" if current_prio else "None",
        inline=False,
    )

    capped = list(movies[:25])
    view = PrioView(capped, guild_id, user_id)

    if len(movies) > 25:
        embed.set_footer(text="Showing first 25 movies only.")

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ── UI components ─────────────────────────────────────────────────────────────

class PrioView(discord.ui.View):
    def __init__(self, movies, guild_id: str, user_id: str):
        super().__init__(timeout=120)
        for movie in movies:
            label = movie["movie_name"]
            if len(label) > 80:
                label = label[:77] + "…"
            self.add_item(
                PrioButton(
                    label=label,
                    movie_name=movie["movie_name"],
                    is_current=bool(movie["is_priority"]),
                    guild_id=guild_id,
                    user_id=user_id,
                )
            )


class PrioButton(discord.ui.Button):
    def __init__(
        self,
        label: str,
        movie_name: str,
        is_current: bool,
        guild_id: str,
        user_id: str,
    ):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.success if is_current else discord.ButtonStyle.secondary,
        )
        self.movie_name = movie_name
        self.is_current = is_current
        self.guild_id = guild_id
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        # Ephemeral messages are only visible to the invoking user, but guard anyway
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "This menu isn't yours.", ephemeral=True
            )
            return

        with get_db() as conn:
            conn.execute(
                "UPDATE suggestions SET is_priority = 0 WHERE guild_id = ? AND user_id = ?",
                (self.guild_id, self.user_id),
            )
            if not self.is_current:
                conn.execute(
                    "UPDATE suggestions SET is_priority = 1 WHERE guild_id = ? AND user_id = ? AND movie_name = ?",
                    (self.guild_id, self.user_id, self.movie_name),
                )

        if self.is_current:
            await interaction.response.send_message(
                f"Removed priority from **{self.movie_name}**.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"**{self.movie_name}** is now your priority! ⭐", ephemeral=True
            )


# ── entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN environment variable is not set.")
    bot.run(token)
