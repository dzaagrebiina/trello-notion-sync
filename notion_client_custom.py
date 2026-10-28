"""
Thin wrapper around the Notion REST API. Named *_custom so it never shadows
the official `notion_client` package if that's installed in the same
environment.
"""
import requests

from config import (
    NOTION_API_VERSION,
    NOTION_PROJECTS_DATA_SOURCE_ID,
    NOTION_TASKS_DATA_SOURCE_ID,
    NOTION_TOKEN,
)
from schema import PROJECTS_TITLE_PROPERTY

BASE_URL = "https://api.notion.com/v1"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_API_VERSION,
    "Content-Type": "application/json",
}


def query_data_source(data_source_id: str, filter_: dict = None) -> list:
    payload = {"filter": filter_} if filter_ else {}
    resp = requests.post(
        f"{BASE_URL}/data_sources/{data_source_id}/query",
        headers=HEADERS,
        json=payload,
    )
    resp.raise_for_status()
    return resp.json()["results"]


def get_projects() -> dict:
    """Returns {project_name: page_id} for every row in the Projects
    database. Used to resolve Trello project labels to the real Notion
    relation target, since Tasks.Project is a relation, not a select.

    Names are stripped of leading/trailing whitespace -- a trailing space in
    a Notion title is invisible in the UI but breaks an exact-string match
    against a Trello label that doesn't have one. This was a real production
    incident: one project's label silently stopped syncing because its
    Notion title ended in a space nobody could see."""
    results = query_data_source(NOTION_PROJECTS_DATA_SOURCE_ID)
    projects = {}
    for page in results:
        title = page["properties"].get(PROJECTS_TITLE_PROPERTY, {}).get("title", [])
        name = "".join(t["plain_text"] for t in title).strip() if title else None
        if name:
            projects[name] = page["id"]
    return projects


def get_page(page_id: str) -> dict:
    resp = requests.get(f"{BASE_URL}/pages/{page_id}", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def create_task_page(properties: dict) -> dict:
    """Creates a new row in the Tasks database specifically -- Trello cards
    only ever create tasks, never projects."""
    resp = requests.post(
        f"{BASE_URL}/pages",
        headers=HEADERS,
        json={
            "parent": {"data_source_id": NOTION_TASKS_DATA_SOURCE_ID},
            "properties": properties,
        },
    )
    resp.raise_for_status()
    return resp.json()


def update_page(page_id: str, properties: dict) -> dict:
    resp = requests.patch(
        f"{BASE_URL}/pages/{page_id}",
        headers=HEADERS,
        json={"properties": properties},
    )
    resp.raise_for_status()
    return resp.json()
