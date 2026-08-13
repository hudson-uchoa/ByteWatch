# ByteWatch

**ByteWatch** is a Discord bot designed to manage, monitor, and log software development and study sessions directly through Discord.

It was created as a personal tool to track coding progress individually or collaboratively, with a focus on **simplicity, low friction, and useful productivity insights**.

## ✨ Features

* ⏱️ **Session Tracking** — Accurately tracks the time spent during development and study sessions.
* ⏸️ **Pause & Resume** — Sessions can be paused and resumed whenever necessary.
* 💤 **Automatic Idle Timeout** — Paused sessions are automatically terminated after 2 hours.
* 📁 **Project Management** — Create projects, track completion percentages, and associate coding sessions with specific projects and objectives.
* 🔍 **Real-Time Status** — Check the elapsed time, project, programming language, and other details of an active session without stopping it.
* 💻 **Programming Language Tracking** — Records the programming language used during each session.
* 🤖 **AI Usage Logging & Analytics** — Tracks the use of AI coding assistants and calculates AI dependency based on the time spent using AI compared to the total session.

  * ChatGPT
  * GitHub Copilot
  * Google Gemini
  * Claude
  * Cursor
* 🗄️ **Local Database** — Uses SQLite for lightweight, fast, and local data storage.
* 📊 **Weekly Ranking & AI Analytics** — Displays a weekly leaderboard with total logged time and AI dependency metrics.
* 📅 **Weekly Summary** — Automatically sends a development summary every Sunday to the configured Discord channel.
* 📝 **Error Logging** — Records unhandled errors in `bytewatch.log` for easier troubleshooting.

## 🎮 Commands

| Command             | Description                                                                                 |
| :------------------ | :------------------------------------------------------------------------------------------ |
| `/start`            | Starts a new development session, prompting for project and programming language selection. |
| `/status`           | Displays real-time information and elapsed time for the active session without stopping it. |
| `/pause`            | Pauses the active session.                                                                  |
| `/resume`           | Resumes a previously paused session.                                                        |
| `/stop`             | Stops the active session, collects AI usage information, and saves the final statistics.    |
| `/ranking`          | Displays the weekly leaderboard with total logged time and AI dependency metrics.           |
| `/project create`   | Creates a new project and sets its initial completion percentage.                           |
| `/project progress` | Updates the completion percentage of an existing project.                                   |
| `/project list`     | Lists all active projects with their current progress.                                      |

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

Make sure **Python 3** is installed on your system.

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

Replace the values with your Discord bot token and the ID of the Discord channel where ByteWatch should send its automated reports.

> **⚠️ Security:** Never commit your `.env` file or expose your Discord bot token.

### 4. Run the bot

Start ByteWatch with:

```bash
python bot.py
```

If everything is configured correctly, the bot will connect to Discord and become available for use.

## 🗄️ Database

ByteWatch uses **SQLite3** as its local database, storing both development sessions and project information.

The database is stored locally in:

```text
bytewatch.db
```

This allows ByteWatch to operate without requiring an external database server, keeping the project lightweight and easy to deploy.

The database stores information such as:

* Development sessions
* Session duration
* Programming languages
* Projects
* Project progress
* AI usage data
* User statistics

## 🤖 AI Dependency Analytics

One of ByteWatch's main features is its ability to track the use of AI coding assistants during development sessions.

When a session is stopped, ByteWatch collects information about which AI tools were used and records the corresponding usage data.

This information is used to calculate an **AI dependency percentage**, allowing developers to compare their independent coding time against the time assisted by AI tools.

The data can then be displayed through the weekly ranking and summary.

Supported AI assistants include:

* ChatGPT
* GitHub Copilot
* Google Gemini
* Claude
* Cursor

## 📁 Project Management

ByteWatch allows development and study sessions to be organized around individual projects.

Projects can have:

* A name
* A completion percentage
* Associated development sessions
* Progress visualization

Example workflow:

```text
/project create
        ↓
Select project
        ↓
Set project progress
        ↓
/start
        ↓
Select project
        ↓
Select programming language
        ↓
Start session
```

Project progress can be updated at any time using:

```text
/project progress
```

Active projects can be viewed with:

```text
/project list
```

## 📊 Weekly Statistics

ByteWatch automatically tracks development activity throughout the week.

Weekly statistics include:

* Total time spent coding or studying
* Programming languages used
* Projects worked on
* User rankings
* AI usage
* AI dependency percentage

The weekly ranking tracks activity **from Monday onward**.

A detailed weekly summary is automatically sent to the configured Discord channel every **Sunday**.

## 📝 Logging

Unhandled errors and internal events are recorded in:

```text
bytewatch.log
```

This makes it easier to diagnose problems without cluttering the Discord interface.

## 🔒 Security

The following files contain local or sensitive information and should **not** be committed to Git:

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

The project is actively evolving and may receive additional features, statistics, integrations, and quality-of-life improvements over time.

## 📄 License

This project does not currently specify a license.
