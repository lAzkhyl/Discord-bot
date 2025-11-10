# Discord Leveling Bot

A Discord bot with a dual-role leveling system that tracks XP and levels separately for two different roles.

## Features

- **Dual-Role Leveling**: Tracks XP and levels independently for "Role A" and "Role B"
- **Efficient XP System**: 60-second cooldown prevents spam and optimizes database usage
- **Smart Database Operations**: Only 1 read and 1 write per user per cooldown period, even when earning XP for both roles
- **Level-Up Notifications**: Automatic congratulations messages specifying which role leveled up
- **Stats Display**: Beautiful embed showing progress for both roles with the `!level` command
- **Persistent Storage**: Uses Replit DB for reliable data storage
- **Always Online**: Flask keep-alive server ensures 24/7 uptime

## Setup Instructions

### 1. Get Your Discord Bot Token

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application (or select an existing one)
3. Go to the "Bot" section
4. Click "Reset Token" and copy your bot token
5. **Important**: Enable the following Privileged Gateway Intents:
   - Server Members Intent
   - Message Content Intent

### 2. Add Token to Replit Secrets

1. In your Replit project, open the "Secrets" tool (lock icon in the left sidebar)
2. Create a new secret:
   - Key: `DISCORD_TOKEN`
   - Value: Paste your bot token

### 3. Configure Role IDs

1. Open `main.py`
2. Find lines 8-9 and replace with your actual role IDs:
   ```python
   ROLE_A_ID = 1234567890123456789  # Replace with your Role A ID
   ROLE_B_ID = 9876543210987654321  # Replace with your Role B ID
   ```

**To get Role IDs:**
- Enable Developer Mode in Discord (User Settings > Advanced > Developer Mode)
- Right-click on a role and select "Copy ID"

### 4. Invite Your Bot to Your Server

Use this URL template (replace `YOUR_CLIENT_ID` with your application's client ID from the Discord Developer Portal):

```
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=2147568640&scope=bot
```

Required permissions:
- Send Messages
- Embed Links
- Read Message History
- Read Messages/View Channels

### 5. Run the Bot

Click the "Run" button in Replit. The bot will start automatically!

## How It Works

### XP System

- Users earn **15 XP per message** (configurable in `main.py`)
- **60-second cooldown** between XP gains to prevent spam
- XP is tracked separately for Role A and Role B
- Users with both roles earn XP for both simultaneously (in a single database operation)

### Leveling Formula

- Level 0 → Level 1: 100 XP
- Level 1 → Level 2: 200 XP
- Level 2 → Level 3: 300 XP
- Formula: `100 × (current_level + 1)`

### Database Structure

User data is stored in Replit DB with this structure:

```json
{
  "USER_ID": {
    "role_a": {"xp": 50, "level": 1},
    "role_b": {"xp": 120, "level": 2}
  }
}
```

## Commands

### `!level`

Displays your current level, XP, and progress for both Role A and Role B in a beautiful embed.

**Example Output:**
```
📊 Username's Level Stats

🔵 Role A
Level: 5
XP: 350/600
Progress: 58%

🟢 Role B
Level: 3
XP: 120/400
Progress: 30%
```

## Customization

You can customize these values in `main.py`:

- `ROLE_A_ID` and `ROLE_B_ID` (lines 8-9): Your role IDs
- `XP_PER_MESSAGE` (line 11): Amount of XP earned per message
- `XP_COOLDOWN` (line 12): Cooldown in seconds between XP gains
- `xp_for_next_level()` function (line 22): Modify the leveling formula

## File Structure

- `main.py`: Main bot code with leveling logic
- `keep_alive.py`: Flask server to keep the bot running 24/7
- `README.md`: This file

## Technical Details

- **Language**: Python 3.11
- **Discord Library**: discord.py 2.6.4
- **Database**: Replit DB (persistent key-value store)
- **Web Server**: Flask (for uptime monitoring)

## Troubleshooting

**Bot not responding?**
- Check that you've added `DISCORD_TOKEN` to Replit Secrets
- Verify that Message Content Intent is enabled in Discord Developer Portal
- Make sure the bot has permission to read and send messages in your server

**XP not being earned?**
- Verify the role IDs are correct in `main.py`
- Check that users have one of the configured roles
- Remember there's a 60-second cooldown between XP gains

**Level-up messages not appearing?**
- Ensure the bot has permission to send messages in the channel
- Check the console logs for any error messages

## Support

For issues or questions, check the Replit console logs for detailed error messages.
