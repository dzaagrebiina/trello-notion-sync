"""
Test environment setup -- import this BEFORE any module that reads config.py.

- Dummy credentials so config.py can be imported. No test ever makes a real
  network call: every API client is mocked.
- Forces the mapping store onto a throwaway SQLite file, so running the
  tests can never touch a real database even if a local .env sets
  DATABASE_URL (load_dotenv never overrides variables that are already set).
"""
import os
import tempfile

for _name in (
    "TRELLO_API_KEY",
    "TRELLO_TOKEN",
    "TRELLO_BOARD_ID",
    "NOTION_TOKEN",
    "NOTION_TASKS_DATA_SOURCE_ID",
    "NOTION_PROJECTS_DATA_SOURCE_ID",
):
    os.environ.setdefault(_name, "dummy")

os.environ["DATABASE_URL"] = ""
os.environ["MAPPING_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_mapping.db")
