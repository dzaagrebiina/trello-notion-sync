"""
Pure translation functions between Trello card fields and Notion task page
properties. No network calls here on purpose -- it's what makes this file
testable without hitting either API.

Schema notes (learned the hard way against a live workspace):
- Status is Notion's "status" property TYPE, not "select" -- the two use
  different API shapes ({"status": {...}} vs {"select": {...}}), and writing
  the wrong one fails with a validation error.
- "Project" is a RELATION to a separate Projects database -- every value is a
  Notion page_id, resolved via a name -> page_id map built from
  notion_client_custom.get_projects(). Trello project labels are matched to
  Notion project rows by name.
- Description sync is gated behind a flag so the tool never silently writes
  to a property that hasn't been verified to exist.
"""
from schema import (
    DESCRIPTION_PROPERTY,
    DUE_DATE_PROPERTY,
    PROJECT_PROPERTY,
    STATUS_PROPERTY,
    TITLE_PROPERTY,
)


def trello_to_notion_properties(
    card: dict,
    *,
    list_name: str,
    project_page_ids: list,
    sync_description: bool = False,
) -> dict:
    """Build a Notion 'properties' payload from a Trello card dict (as
    returned by trello_client.get_card) plus the resolved list name and
    Project relation target(s)."""
    properties = {
        TITLE_PROPERTY: {"title": [{"text": {"content": card["name"]}}]},
        STATUS_PROPERTY: {"status": {"name": list_name}} if list_name else {"status": None},
    }

    if card.get("due"):
        properties[DUE_DATE_PROPERTY] = {"date": {"start": card["due"][:10]}}
    else:
        properties[DUE_DATE_PROPERTY] = {"date": None}

    properties[PROJECT_PROPERTY] = {"relation": [{"id": pid} for pid in project_page_ids]}

    if sync_description:
        properties[DESCRIPTION_PROPERTY] = {"rich_text": [{"text": {"content": card.get("desc") or ""}}]}

    return properties


def notion_page_to_trello_fields(
    page: dict,
    *,
    list_name_to_id: dict,
    project_page_id_to_label_id: dict,
    sync_description: bool = False,
) -> dict:
    """Build a dict of Trello update fields from a Notion task page's
    properties."""
    props = page["properties"]
    fields = {}

    title = props.get(TITLE_PROPERTY, {}).get("title", [])
    fields["name"] = "".join(t["plain_text"] for t in title) if title else "Untitled"

    if sync_description:
        desc = props.get(DESCRIPTION_PROPERTY, {}).get("rich_text", [])
        fields["desc"] = "".join(t["plain_text"] for t in desc) if desc else ""

    date_prop = props.get(DUE_DATE_PROPERTY, {}).get("date")
    fields["due"] = date_prop["start"] if date_prop else None

    status = props.get(STATUS_PROPERTY, {}).get("status")
    if status and status["name"] in list_name_to_id:
        fields["id_list"] = list_name_to_id[status["name"]]

    project_relations = props.get(PROJECT_PROPERTY, {}).get("relation", [])
    label_ids = [
        project_page_id_to_label_id[r["id"]]
        for r in project_relations
        if r["id"] in project_page_id_to_label_id
    ]
    if label_ids:
        fields["id_labels"] = label_ids

    return fields


def extract_project_page_ids(card: dict, label_id_to_name: dict, project_name_to_page_id: dict) -> list:
    """Trello card's project labels -> matching Notion Project page ids.
    A label with no matching Notion project (name mismatch, or project not
    yet created in Notion) is silently skipped -- callers log this upstream
    so mismatches surface instead of disappearing quietly.

    Both sides are whitespace-stripped before matching -- a trailing space
    on either a Trello label or a Notion project title is invisible in
    either UI but breaks an exact-string match otherwise (see
    notion_client_custom.get_projects for the incident that surfaced this)."""
    label_names = [label_id_to_name[lid].strip() for lid in card.get("idLabels", []) if lid in label_id_to_name]
    return [project_name_to_page_id[name] for name in label_names if name in project_name_to_page_id]


def canonical_fingerprint(*, status_name, due_date, project_page_ids) -> dict:
    """A direction-independent snapshot of a task's synced fields.

    Both sync directions must build this from the SAME shape before calling
    mapping_store.is_echo/mark_written. An earlier version called mark_written
    with the raw Notion 'properties' payload (Trello->Notion direction) but
    is_echo with the raw Trello 'fields' payload (Notion->Trello direction) --
    two structurally different dicts for the same underlying state, so the
    hashes could never match and echoes were never actually recognized. That
    let a single Trello move ping-pong back and forth, which made cards
    appear to "revert on their own."
    """
    return {
        "status": status_name,
        "due": due_date,
        "projects": sorted(project_page_ids) if project_page_ids else [],
    }


def notion_page_fingerprint(page: dict) -> dict:
    """Same canonical fingerprint, derived directly from a raw Notion page's
    properties (used on the Notion->Trello side, where we already have the
    Notion-shaped data and don't need to round-trip through Trello ids)."""
    props = page["properties"]
    status = props.get(STATUS_PROPERTY, {}).get("status")
    status_name = status["name"] if status else None
    date_prop = props.get(DUE_DATE_PROPERTY, {}).get("date")
    due_date = date_prop["start"] if date_prop else None
    project_ids = [r["id"] for r in props.get(PROJECT_PROPERTY, {}).get("relation", [])]
    return canonical_fingerprint(status_name=status_name, due_date=due_date, project_page_ids=project_ids)
