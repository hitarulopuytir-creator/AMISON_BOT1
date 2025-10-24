# Overview

This is a Discord moderation bot built with discord.py that tracks and manages user warnings across Discord servers. The bot monitors warnings issued by MEE6 (ID: 159985870458322944) and maintains a persistent record of user infractions using JSON file storage. The bot automatically assigns warning level roles (Warn1lvl and Warn2lvl) based on the number of warnings accumulated by each user. The primary purpose is to provide automated warning tracking and role management functionality for Discord server administrators.

## Current Features (October 24, 2025)
- Automatic detection of MEE6 warning messages via embed monitoring
- Persistent warning counter for each user per server using JSON storage
- Automatic role assignment: Warn1lvl after 1 warning, Warn2lvl after 2 warnings
- Role replacement: Warn1lvl is automatically removed when Warn2lvl is assigned
- Clean logging of warn events and role assignments with timestamps
- Multi-server support with isolated data per guild
- Regex-based user ID extraction from MEE6 embed fields
- **NEW**: Complete whitelist ticket system with `/nick` command
- **NEW**: Automatic ticket numbering (заявка-в-белый-список-1, #2, #3, etc.)
- **NEW**: Interactive Discord buttons for ticket management (approve/deny/close/reopen/delete)
- **NEW**: User application history tracking
- **NEW**: Account age verification (flags accounts younger than 30 days)
- **NEW**: Minecraft perma-ban role check (Role ID: 1424009252137205864)
- **NEW**: Automated notifications to log channel for approved/denied applications
- **NEW**: Persistent Views that survive bot restarts
- **NEW**: Flask keepalive server on port 5000 for uptime monitoring

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Bot Framework
- **Technology**: discord.py library with commands extension
- **Rationale**: discord.py is the industry-standard Python library for Discord bot development, providing robust event handling and command management
- **Command Prefix**: `!` for user commands
- **Intents**: Configured for message content and member tracking to enable warning detection

## Data Persistence
- **Storage Solution**: JSON file-based storage (`warns.json`)
- **Structure**: Nested dictionary with guild IDs as top-level keys and user IDs as nested keys
- **Rationale**: File-based storage chosen for simplicity and portability; suitable for small to medium-scale deployments without need for complex database infrastructure
- **Trade-offs**: 
  - Pros: Simple implementation, no external dependencies, easy to backup
  - Cons: Limited scalability, potential race conditions with concurrent writes, no query optimization

## Warning Detection System
- **Approach**: Event-driven monitoring of messages from a specific moderation bot (ID: 159985870458322944)
- **Pattern Matching**: Keyword detection for "warned" or "has been warned" in message content
- **User Extraction**: Leverages Discord's mention system to identify warned users
- **Design Decision**: Passive monitoring rather than active command execution, allowing integration with existing moderation workflows

## Data Model
- **Hierarchical Structure**: 
  - Guild level (server-specific tracking)
  - User level (per-user warning records)
- **Rationale**: Isolation between servers prevents data leakage and ensures proper multi-guild support

# External Dependencies

## Discord API
- **Library**: discord.py
- **Purpose**: Primary interface for Discord bot functionality, event handling, and API communication
- **Features Used**: Message events, member intents, command framework

## Python Standard Library
- **json**: Serialization and deserialization of warning data
- **os**: File system operations for checking file existence
- **datetime**: Timestamp tracking (imported but implementation incomplete in provided code)

## Bot Integration
- **External Bot Monitoring**: Tracks warnings from bot ID 159985870458322944 (appears to be MEE6 or similar moderation bot)
- **Integration Method**: Message content parsing and mention extraction
- **Requirement**: The external bot must mention warned users and include specific keywords in warning messages

## Flask Web Server
- **Technology**: Flask web framework
- **Purpose**: Provides a keepalive endpoint for uptime monitoring services (e.g., UptimeRobot)
- **Port**: 5000 (Replit standard web port)
- **Endpoint**: GET / returns "Bot is alive!"
- **Implementation**: Runs in separate daemon thread to avoid blocking Discord bot

## Whitelist Ticket System (`/nick` command)
- **Purpose**: Complete ticket management system for Minecraft whitelist applications
- **Trigger**: User executes `/nick <desired_nickname>` command
- **Data Storage**: `whitelist_tickets.json` stores all ticket data, numbering, and user history
- **Channel Naming**: `заявка-в-белый-список-{номер}` (e.g., заявка-в-белый-список-1, #2, #3)
- **Automatic Numbering**: Sequential ticket numbers auto-increment per guild

### Workflow:
1. **Ticket Creation**:
   - Creates numbered private channel with restricted permissions
   - Grants access to applicant, admin (ID: 1193894492663713792), mod (ID: 1037412954481639476), and bot
   - Shows detailed embed with verification info including previous application history
   - Mentions admin and mod roles for immediate attention

2. **Verification Checks**:
   - Account creation date (warns if < 30 days old)
   - Minecraft perma-ban role presence (Role ID: 1424009252137205864)
   - Discord join date
   - Previous application count (tracked per user)

3. **Interactive Buttons - Stage 1** (WhitelistDecisionView):
   - 🟢 "Добавлен в белый список" button (admin/mod only)
   - 🔴 "Отказ в белом списке" button (admin/mod only)
   - Upon click: Updates ticket status, sends notification to log channel, transitions to Stage 2

4. **Interactive Buttons - Stage 2** (WhitelistCloseView):
   - 🔴 "Закрыть тикет" button (owner only, ID: 1037411767611052182)
   - Upon click: Restricts channel permissions (only owner can write), transitions to Stage 3

5. **Interactive Buttons - Stage 3** (WhitelistManageView):
   - 🔴 "Удалить тикет" button (owner only) - Deletes channel after 5 second countdown
   - 🟢 "Открыть тикет" button (owner only) - Reopens ticket, restores permissions, returns to Stage 2

6. **Notifications**:
   - Sends formatted embed to log channel (ID: 1431367741553639498)
   - Includes: ticket number, decision (approved/denied), applicant username
   - Color-coded: green for approved, red for denied

### Technical Features:
- **Persistent Views**: All buttons survive bot restarts using custom_id system
- **View Registration**: Existing tickets re-register their views on bot startup
- **Permission Management**: Dynamic channel permission updates for closed/open states
- **Error Handling**: Comprehensive try/except blocks with logging
- **Role Verification**: All button interactions verify user has required role before execution
- **Audit Trail**: All actions logged with timestamps and user information