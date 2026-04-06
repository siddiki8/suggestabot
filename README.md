# Suggestabot

A simple Discord bot for collecting and prioritising movie suggestions, scoped per server.

## Commands

| Command | Description |
|---|---|
| `/suggest <movie>` | Add a movie to your personal suggestion list |
| `/suggestions` | Show all suggested movies grouped by user. Priority picks are starred. |
| `/prio` | Open an ephemeral button menu to star one of your movies as your priority pick (click it again to remove) |

## Local Development

### Prerequisites
- Python 3.11+
- A Discord bot token (see [setup guide](#discord-setup) below)

### Install & run

```bash
# clone the repo
git clone <your-repo-url>
cd Suggestabot

# create a virtual environment (use uv or plain venv)
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt

# configure env
cp .env.example .env
# edit .env and add your DISCORD_TOKEN

python bot.py
```

The SQLite database (`suggestions.db`) is created automatically on first run in the directory set by `DATA_DIR` (defaults to `.`).

---

## Discord Setup

1. Go to [https://discord.com/developers/applications](https://discord.com/developers/applications) and click **New Application**. Give it a name (e.g. *Suggestabot*).
2. In the left sidebar go to **Bot** → click **Add Bot**.
3. Under **Token** click **Reset Token**, copy it. This is your `DISCORD_TOKEN`.
4. Under **Privileged Gateway Intents** — no extra intents are needed. Leave them all off.
5. In the left sidebar go to **OAuth2 → URL Generator**.
   - Under **Scopes** check: `bot` and `applications.commands`
   - Under **Bot Permissions** check: `Send Messages`, `Embed Links`, `Use Slash Commands`
6. Copy the generated URL, open it in your browser, and add the bot to your server.

---

## Railway Deployment

### 1. Persistent Volume

Suggestabot stores data in a SQLite file. You need a persistent volume so data survives redeploys.

1. In your Railway project, open the service → **Volumes** tab.
2. Click **Add Volume**, set the mount path to `/data`.

### 2. Environment Variables

In the service → **Variables** tab, add:

| Variable | Value |
|---|---|
| `DISCORD_TOKEN` | Your bot token from the Discord dev portal |
| `DATA_DIR` | `/data` |

### 3. Deploy from GitHub

1. In Railway click **New Project → Deploy from GitHub repo**.
2. Select your repository. Railway auto-detects Python via `requirements.txt` and uses the `startCommand` in `railway.toml`.
3. Trigger a deploy (or it starts automatically). Watch the **Logs** tab for `Logged in as …`.

Slash commands are synced globally on every startup. They may take up to **1 hour** to appear in Discord for the first time.

---

## Project Structure

```
.
├── bot.py            # All bot logic
├── requirements.txt  # Python dependencies
├── railway.toml      # Railway build/deploy config
├── .env.example      # Template for local env vars
└── .gitignore
```
