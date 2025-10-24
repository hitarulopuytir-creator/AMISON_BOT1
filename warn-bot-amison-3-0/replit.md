# Overview

This is a Discord moderation bot built with discord.py that provides automated warning tracking and management across Discord servers. The bot monitors warnings issued by MEE6 (a popular Discord moderation bot) and maintains persistent warning counts for users. It features automatic role assignment based on warning thresholds, nickname verification workflows, and account age checks to support server moderation efforts.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Bot Framework
- **Technology**: discord.py library with commands extension
- **Rationale**: discord.py is the industry-standard Python library for Discord bot development, offering robust event handling, command management, and comprehensive Discord API coverage
- **Command Prefix**: `!` for text-based commands
- **Intents Configuration**: 
  - Message content intent enabled for warning detection
  - Members intent enabled for user tracking and role management
- **Design Pattern**: Event-driven architecture monitoring messages from MEE6 (bot ID: 159985870458322944)

## Warning Detection & Processing
- **Detection Method**: Passive monitoring of MEE6 embed messages containing warning keywords
- **Pattern Matching**: Regex-based extraction of user IDs from MEE6 embed fields
- **User Identification**: Leverages Discord mention parsing to identify warned users
- **Design Decision**: Passive integration approach allows the bot to work alongside existing moderation workflows without replacing MEE6

## Automated Role Management
- **Role Assignment Logic**:
  - 1 warning → Assign "Warn1lvl" role
  - 2 warnings → Replace "Warn1lvl" with "Warn2lvl" role
- **Rationale**: Tiered warning system provides visual indicators of user warning status and enables permission-based restrictions
- **Implementation**: Event-triggered role updates ensure immediate feedback to moderators and users

## Whitelist Ticket System
- **Command**: `/nick` command for comprehensive whitelist application management
- **Channel Naming**: Sequential numbering `заявка-в-белый-список-{#}` (e.g., #1, #2, #3)
- **Data Storage**: `whitelist_tickets.json` for persistent ticket tracking and user history
- **Role Access**: 
  - Administration role (ID: 1193894492663713792)
  - Moderation role (ID: 1037412954481639476)
  - Owner role (ID: 1037411767611052182) for ticket management
- **Security Checks**:
  - Account age verification (flags accounts younger than 30 days)
  - Minecraft perma-ban role check (Role ID: 1424009252137205864)
  - User application history tracking
- **Interactive Workflow**:
  1. Admin/mod buttons: Approve or deny applications
  2. Owner controls: Close, reopen, or delete tickets
  3. Permission management: Closed tickets restrict writing to owner only
  4. Automated notifications: Log channel (ID: 1431367741553639498) receives decision updates
- **Persistent Views**: All interactive buttons survive bot restarts via custom_id system
- **Rationale**: Prevents ban evasion, tracks repeat applicants, provides structured approval workflow

## Data Persistence
- **Storage Solution**: JSON file-based storage (`warns.json`)
- **Schema Structure**: 
  ```
  {
    "guild_id": {
      "user_id": warning_count
    }
  }
  ```
- **Multi-Server Isolation**: Guild-level data separation ensures warnings don't carry across servers
- **Rationale**: File-based storage chosen for simplicity, portability, and zero external database dependencies
- **Trade-offs**:
  - Pros: Simple implementation, easy backup/restore, no infrastructure overhead
  - Cons: Limited scalability, no concurrent write protection, manual file management required
- **Alternative Considered**: SQLite database would provide better scalability but adds complexity for small-scale deployments

## Uptime Monitoring
- **Service**: Flask web server running on port 5000
- **Endpoint**: Single `/` route returning "Bot is alive!" status message
- **Threading**: Runs in daemon thread to avoid blocking Discord bot operations
- **Rationale**: Enables integration with uptime monitoring services (e.g., UptimeRobot) to ensure bot availability
- **Error Handling**: OSError catching prevents port conflicts from crashing the bot

## Logging & Observability
- **Timestamp Format**: `YYYY-MM-DD HH:MM:SS` for all log entries
- **Logged Events**:
  - Warning detections and role assignments
  - Flask server startup failures
- **Rationale**: Timestamped logging enables debugging and audit trail creation

# External Dependencies

## Discord API Integration
- **Library**: discord.py (Python Discord API wrapper)
- **Purpose**: Primary interface for all Discord bot operations including message monitoring, role management, and command handling
- **Version Management**: Specified in requirements.txt

## MEE6 Bot Integration
- **Bot ID**: 159985870458322944
- **Integration Type**: Message monitoring (passive)
- **Purpose**: Detects warning events issued by MEE6 to trigger automated responses
- **Dependency Level**: Critical - bot functionality depends on MEE6's message format

## Web Framework
- **Library**: Flask
- **Purpose**: Lightweight HTTP server for uptime monitoring endpoints
- **Port**: 5000 (hardcoded)
- **Usage**: Minimal - single health check endpoint

## Configuration Management
- **Library**: python-dotenv
- **Purpose**: Environment variable management for sensitive configuration (e.g., Discord bot token)
- **Security**: Prevents hardcoding credentials in source code

## Role Configuration
- **Warn1lvl Role**: Assigned after first warning (role name-based lookup)
- **Warn2lvl Role**: Assigned after second warning, replaces Warn1lvl
- **Administration Role**: ID 1193894492663713792 (for /nick command notifications)
- **Moderation Role**: ID 1037412954481639476 (for /nick command notifications)
- **Minecraft Perma-ban Role**: ID 1424009252137205864 (ban evasion detection)
- **Dependency**: Requires manual role creation in Discord servers with exact name matches for warning roles