"""
Notion property names the sync reads and writes.

Kept separate from config.py on purpose: config.py requires credentials to
import, but the pure translation logic in field_mapping.py (and its unit
tests) only needs these names. Each one can be overridden with an
environment variable if your Notion databases use different property names.
"""
import os

from dotenv import load_dotenv

load_dotenv()

# Tasks database
TITLE_PROPERTY = os.environ.get("NOTION_TITLE_PROPERTY", "Name")
STATUS_PROPERTY = os.environ.get("NOTION_STATUS_PROPERTY", "Status")  # must be Notion's "status" type, not "select"
DUE_DATE_PROPERTY = os.environ.get("NOTION_DUE_DATE_PROPERTY", "Due Date")
PROJECT_PROPERTY = os.environ.get("NOTION_PROJECT_PROPERTY", "Project")  # relation -> Projects database
DESCRIPTION_PROPERTY = os.environ.get("NOTION_DESCRIPTION_PROPERTY", "Description")

# Projects database
PROJECTS_TITLE_PROPERTY = os.environ.get("NOTION_PROJECTS_TITLE_PROPERTY", "Name")
