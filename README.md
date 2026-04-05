# YURXZ Rejoin v9 — Discord Bot Control

Automation tool for Roblox Rejoin with Android Rooted + Termux support. Controls multiple Roblox instances and executors (Delta/Fluxus/etc.) via a Discord Bot interface.

## 🛠️ Installation

### 1. Requirements
- **Termux** (on Android) or a Shell environment with **su** (Root access).
- **Python 3.x** installed.
- **Root access** (Required for screenshot, ADB commands, and file injection).

### 2. Install Dependencies
Run the following commands in Termux to prepare your environment and install the required libraries:

```bash
pkg update && pkg upgrade
pkg install python
termux-setup-storage
pip install requests python-dotenv psutil websocket-client
```

## 🚀 How to Run

### 1. Setup Config
Run the setup command to configure your Discord Bot Token and Channel ID:

```bash
python bot.py setup
```

Follow the on-screen instructions to create a bot on the Discord Developer Portal and invite it to your server.

### 2. Start the Bot
After setup, run the bot script normally:

```bash
python bot.py
```

The bot will automatically:
- Connect to Discord Gateway.
- Send a **Control Panel** to your specified channel.
- Monitor Roblox status and handle rejoin commands.

## 🎮 Features
- **Control Panel**: Start/Stop rejoin and everything from Discord buttons.
- **Add AutoExec**: Upload Lua scripts directly to `/storage/emulated/0/Delta/Autoexecute/`.
- **Remove AE**: List and delete auto-execute scripts.
- **Selective Rejoin**: Launch specific accounts (if configured).
- **Live Monitoring**: See status (In-Game, Loading, etc.) updated in real-time.
- **Screenshot**: Take device screenshots remotely.

---
**Note**: This tool requires **su** binary to be available in the PATH for root command execution.
