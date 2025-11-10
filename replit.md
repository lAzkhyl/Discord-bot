# Discord Leveling Bot

## Overview

A Discord bot implementing a dual-role leveling system that tracks XP and levels independently for two different user roles. The bot uses an efficient cooldown mechanism to prevent spam while maintaining separate progression paths for users with different roles. It includes level-up notifications, stats display via commands, and persistent storage using Replit's database.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Bot Framework
- **Discord.py with Commands Extension**: Uses the `commands.Bot` class to handle Discord interactions and command processing
- **Gateway Intents**: Requires privileged intents for Server Members and Message Content to track user roles and process messages
- **Command Prefix**: Uses `!` as the command prefix for user commands
- **Message Context Handling**: Bot gracefully handles both server messages and direct messages, ignoring DMs for XP tracking (guild-only feature)

### Data Model
The bot implements a dual-tracking system for role-based progression:

**User Data Structure**:
```json
{
  "user_id": {
    "role_a": {"xp": 0, "level": 0},
    "role_b": {"xp": 0, "level": 0}
  }
}
```

**Key Design Decisions**:
- **Independent Role Tracking**: Each role maintains its own XP and level counter, allowing users with both roles to progress on two separate paths simultaneously
- **JSON Serialization**: User data is stored as JSON strings in the database for easy parsing and type safety
- **User ID as Primary Key**: Uses Discord user IDs (converted to strings) as database keys for direct lookups

### XP and Leveling System

**XP Award Mechanism**:
- Users gain 15 XP per message for each role they have
- Users with both roles earn XP for both progression paths from a single message
- Level progression formula: `100 * (level + 1)` XP required for next level

**Cooldown System**:
- **Problem**: Prevent database spam and ensure fair XP distribution
- **Solution**: 60-second global cooldown per user using in-memory timestamp tracking
- **Efficiency**: Single database read and single write per cooldown period, even when updating both roles
- **Implementation**: `user_cooldowns` dictionary stores `{user_id: last_xp_timestamp}` mappings

**Alternatives Considered**:
- Per-role cooldowns: Rejected to maintain simplicity and prevent users from gaining XP too quickly
- Database-stored cooldowns: Rejected in favor of in-memory storage to reduce database load

**Trade-offs**:
- Pro: Minimal database operations (1 read + 1 write per 60s per user)
- Pro: Simple cooldown logic using Python's `time.time()`
- Con: Cooldown state lost on bot restart (acceptable for this use case)

### Command System

**!level Command**:
- Displays user progression for both roles in a Discord Embed
- Shows current level, current XP, and XP required for next level
- Provides clear visual separation between Role A and Role B stats

### Notification System
- **Level-Up Messages**: Public congratulations messages sent to the channel where leveling occurred
- **Role-Specific Notifications**: Messages specify which role (A or B) achieved the level-up
- **Mention Integration**: Uses Discord mentions to notify the user directly

### Uptime Management

**Keep-Alive Server**:
- **Problem**: Replit may sleep inactive processes
- **Solution**: Flask web server running on port 5000 provides an HTTP endpoint for uptime monitoring
- **Implementation**: Daemon thread prevents blocking the main bot process
- **Endpoint**: Returns simple "Discord Bot is alive!" message at root path

## External Dependencies

### Discord Integration
- **discord.py**: Primary library for Discord bot functionality
  - Handles WebSocket connections to Discord Gateway
  - Provides commands framework and event system
  - Manages intents and permissions

### Data Storage
- **Replit Database**: Key-value store for persistent user data
  - Accessed via `replit` package's `db` object
  - Stores JSON-serialized user progression data
  - No schema migrations needed (schemaless design)

### Web Server
- **Flask**: Lightweight web framework for keep-alive functionality
  - Runs HTTP server on port 5000
  - Minimal resource overhead
  - Thread-based execution to avoid blocking bot

### Environment Configuration
- **Replit Secrets**: Stores sensitive bot token (`DISCORD_TOKEN`)
- **Environment Variables**: Bot token accessed via `os.environ`
- **Manual Configuration**: Role IDs (`ROLE_A_ID`, `ROLE_B_ID`) set directly in code

### Third-Party Services
- **Discord API**: All bot interactions go through Discord's REST and Gateway APIs
- **Replit Platform**: Hosts the bot and provides database infrastructure