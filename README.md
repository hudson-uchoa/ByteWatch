# ByteWatch

**ByteWatch** is a Discord bot designed to manage, monitor, and log software development and study sessions directly through Discord.

It was created as a personal tool to track coding progress individually or collaboratively, with a focus on **simplicity, low friction, and useful statistics**.

## ✨ Features

* ⏱️ **Session Tracking** — Accurately tracks the time spent during development or study sessions.
* ⏸️ **Pause & Resume** — Sessions can be paused and resumed whenever necessary.
* 💤 **Automatic Idle Timeout** — Paused sessions are automatically terminated after 2 hours.
* 💻 **Programming Language Tracking** — Records the programming language used during each session.
* 🤖 **AI Usage Logging** — Tracks the use of AI coding assistants such as:

  * ChatGPT
  * GitHub Copilot
  * Google Gemini
  * Claude
  * Cursor
* 🗄️ **Local Database** — Uses SQLite for lightweight, fast, and local data storage.
* 📊 **Weekly Ranking** — Displays a leaderboard with the total time logged by each user during the current week.
* 📅 **Weekly Summary** — Automatically sends a summary every Sunday with development statistics.
* 📝 **Error Logging** — Records unhandled errors in `bytewatch.log` for easier troubleshooting.

## 🎮 Commands

| Command    | Description                                                                           |
| ---------- | ------------------------------------------------------------------------------------- |
| `/start`   | Starts a new development session and opens the language selection menu.               |
| `/pause`   | Pauses the active session.                                                            |
| `/resume`  | Resumes a previously paused session.                                                  |
| `/stop`    | Stops the active session and collects AI usage information before saving the session. |
| `/ranking` | Displays the weekly leaderboard with the total time logged by each user since Monday. |

## 🛠️ Tech Stack

* **Language:** Python 3
* **Discord Library:** [discord.py](https://discordpy.readthedocs.io/)
* **Database:** SQLite3
* **Configuration:** python-dotenv

## 📁 Project Structure

```text
ByteWatch/
├── bot.py
├── bytewatch.db
├── bytewatch.log
├── .env
├── .gitignore
└── README.md
```

> `bytewatch.db`, `bytewatch.log`, and `.env` are local files and should not be committed to the repository.

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/hudson-uchoa/ByteWatch.git
cd ByteWatch
```

### 2. Install the dependencies

Make sure Python 3 is installed on your system.

Then install the required packages:

```bash
python -m pip install discord.py python-dotenv
```

### 3. Configure the environment

Create a `.env` file in the root directory of the project:

```env
DISCORD_TOKEN=your_bot_token_here
DISCORD_CHANNEL_ID=your_channel_id_here
```

Replace the values with your Discord bot token and the ID of the channel where ByteWatch should send its automated reports.

**Never commit your `.env` file or expose your Discord bot token.**

### 4. Run the bot

Start ByteWatch with:

```bash
python bot.py
```

If everything is configured correctly, the bot will connect to Discord and become available for use.

## 🗄️ Database

ByteWatch uses **SQLite3** as its local database.

The database is stored in:

```text
bytewatch.db
```

This allows ByteWatch to operate without requiring an external database server, making it lightweight and easy to deploy for personal use.

## 📊 Weekly Statistics

ByteWatch automatically keeps track of development activity throughout the week.

The weekly statistics include information such as:

* Total time spent coding or studying
* Programming languages used
* User rankings
* AI assistant usage

A weekly summary is automatically sent to the configured Discord channel every **Sunday**.

## 📝 Logging

Unhandled errors and internal events are recorded in:

```text
bytewatch.log
```

This makes it easier to diagnose problems without cluttering the Discord interface.

## 🔒 Security

The following files contain local or sensitive data and should **not** be committed to Git:

```text
.env
bytewatch.db
bytewatch.log
```

A recommended `.gitignore` is:

```gitignore
.env
bytewatch.db
bytewatch.log
__pycache__/
*.pyc
.venv/
venv/
```

## 📌 Project Status

ByteWatch is currently a personal project focused on tracking development and study productivity through Discord.

The project may evolve over time with additional statistics, commands, integrations, and quality-of-life improvements.
