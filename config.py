"""
Runtime configuration. Every credential and workspace-specific identifier
comes from environment variables (a local .env file in development, config
vars on the host in production) -- nothing secret is ever hard-coded here.
See .env.example for the full list.
"""
import os

from dotenv import load_dotenv

load_dotenv()

TRELLO_API_KEY = os.environ["TRELLO_API_KEY"]
TRELLO_TOKEN = os.environ["TRELLO_TOKEN"]
TRELLO_BOARD_ID = os.environ["TRELLO_BOARD_ID"]

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
NOTION_API_VERSION = "2026-03-11"

# The Notion side is two linked databases, not one flat table:
#   Tasks    -- task-level rows; this is what Trello cards sync to
#   Projects -- one row per project; Tasks.Project is a RELATION to this
# Both are addressed by data_source_id (Notion API 2025-09+), not database_id.
NOTION_TASKS_DATA_SOURCE_ID = os.environ["NOTION_TASKS_DATA_SOURCE_ID"]
NOTION_PROJECTS_DATA_SOURCE_ID = os.environ["NOTION_PROJECTS_DATA_SOURCE_ID"]

# Which Trello list a brand-new card lands in when a new Notion task is
# created without a Status yet. Must match a list name on the board exactly.
DEFAULT_LIST_NAME = os.environ.get("DEFAULT_LIST_NAME", "Backlog")

# Description sync is off by default: only switch it on once you've confirmed
# your Tasks database actually has a rich-text property with that name.
SYNC_DESCRIPTION = os.environ.get("SYNC_DESCRIPTION", "false").lower() == "true"

# How long (seconds) a write we just made is remembered, so the webhook echo
# it triggers on the other platform can be recognized and skipped instead of
# bouncing back and forth forever.
SYNC_ECHO_WINDOW_SECONDS = 10

# Postgres in production (set automatically by the Heroku Postgres add-on);
# local SQLite file otherwise.
DATABASE_URL = os.environ.get("DATABASE_URL")
DATABASE_PATH = os.environ.get("MAPPING_DB_PATH", "mapping.db")
