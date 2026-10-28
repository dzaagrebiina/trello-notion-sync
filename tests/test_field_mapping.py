import unittest

from field_mapping import (
    canonical_fingerprint,
    extract_project_page_ids,
    notion_page_fingerprint,
    notion_page_to_trello_fields,
    trello_to_notion_properties,
)
from schema import (
    DESCRIPTION_PROPERTY,
    DUE_DATE_PROPERTY,
    PROJECT_PROPERTY,
    STATUS_PROPERTY,
    TITLE_PROPERTY,
)


class TestTrelloToNotion(unittest.TestCase):
    def test_basic_card(self):
        card = {
            "name": "Fix login bug",
            "desc": "Users can't log in on Safari",
            "due": "2030-01-15T00:00:00.000Z",
            "shortUrl": "https://trello.com/c/example",
            "idLabels": ["label1"],
        }
        props = trello_to_notion_properties(card, list_name="In Progress", project_page_ids=["proj-page-id-3"])

        self.assertEqual(props[TITLE_PROPERTY]["title"][0]["text"]["content"], "Fix login bug")
        self.assertEqual(props[STATUS_PROPERTY]["status"]["name"], "In Progress")
        self.assertEqual(props[DUE_DATE_PROPERTY]["date"]["start"], "2030-01-15")
        self.assertEqual(props[PROJECT_PROPERTY]["relation"], [{"id": "proj-page-id-3"}])

    def test_no_due_date_no_project(self):
        card = {"name": "Untitled task", "desc": "", "due": None, "idLabels": []}
        props = trello_to_notion_properties(card, list_name="Backlog", project_page_ids=[])

        self.assertIsNone(props[DUE_DATE_PROPERTY]["date"])
        self.assertEqual(props[PROJECT_PROPERTY]["relation"], [])

    def test_multiple_project_labels_all_included(self):
        card = {"name": "Cross-project card", "desc": "", "due": None, "idLabels": []}
        props = trello_to_notion_properties(card, list_name="Backlog", project_page_ids=["p1", "p2"])

        self.assertEqual(props[PROJECT_PROPERTY]["relation"], [{"id": "p1"}, {"id": "p2"}])

    def test_status_uses_status_type_not_select(self):
        # Notion's "status" and "select" property types have different API
        # shapes; writing the wrong one is rejected by the API.
        card = {"name": "X", "desc": "", "due": None, "idLabels": []}
        props = trello_to_notion_properties(card, list_name="Done", project_page_ids=[])

        self.assertIn("status", props[STATUS_PROPERTY])
        self.assertNotIn("select", props[STATUS_PROPERTY])

    def test_description_not_synced_by_default(self):
        card = {"name": "X", "desc": "some text", "due": None, "idLabels": []}
        props = trello_to_notion_properties(card, list_name="Backlog", project_page_ids=[])
        self.assertNotIn(DESCRIPTION_PROPERTY, props)


class TestNotionToTrello(unittest.TestCase):
    def test_basic_page(self):
        page = {
            "properties": {
                TITLE_PROPERTY: {"title": [{"plain_text": "Write tests"}]},
                DUE_DATE_PROPERTY: {"date": {"start": "2030-01-20"}},
                STATUS_PROPERTY: {"status": {"name": "In Review"}},
                PROJECT_PROPERTY: {"relation": [{"id": "proj-page-5"}]},
            }
        }
        fields = notion_page_to_trello_fields(
            page,
            list_name_to_id={"In Review": "list_review_id"},
            project_page_id_to_label_id={"proj-page-5": "label_p5_id"},
        )

        self.assertEqual(fields["name"], "Write tests")
        self.assertEqual(fields["due"], "2030-01-20")
        self.assertEqual(fields["id_list"], "list_review_id")
        self.assertEqual(fields["id_labels"], ["label_p5_id"])

    def test_empty_page(self):
        page = {"properties": {TITLE_PROPERTY: {"title": []}}}
        fields = notion_page_to_trello_fields(page, list_name_to_id={}, project_page_id_to_label_id={})

        self.assertEqual(fields["name"], "Untitled")
        self.assertIsNone(fields["due"])
        self.assertNotIn("id_list", fields)
        self.assertNotIn("id_labels", fields)

    def test_unmapped_status_is_skipped(self):
        page = {
            "properties": {
                TITLE_PROPERTY: {"title": [{"plain_text": "X"}]},
                STATUS_PROPERTY: {"status": {"name": "Some New Status"}},
            }
        }
        fields = notion_page_to_trello_fields(page, list_name_to_id={"Backlog": "id1"}, project_page_id_to_label_id={})
        self.assertNotIn("id_list", fields)

    def test_project_relation_with_no_trello_label_match_is_skipped(self):
        page = {
            "properties": {
                TITLE_PROPERTY: {"title": [{"plain_text": "X"}]},
                PROJECT_PROPERTY: {"relation": [{"id": "unmatched-project-id"}]},
            }
        }
        fields = notion_page_to_trello_fields(page, list_name_to_id={}, project_page_id_to_label_id={})
        self.assertNotIn("id_labels", fields)


class TestExtractProjectPageIds(unittest.TestCase):
    def test_matches_known_project(self):
        card = {"idLabels": ["l1", "l2"]}
        label_id_to_name = {"l1": "Project Alpha", "l2": "Unrelated Label"}
        project_name_to_page_id = {"Project Alpha": "page-abc"}

        result = extract_project_page_ids(card, label_id_to_name, project_name_to_page_id)
        self.assertEqual(result, ["page-abc"])

    def test_label_with_no_matching_project_is_skipped(self):
        card = {"idLabels": ["l1"]}
        label_id_to_name = {"l1": "Some Label With No Notion Project"}
        result = extract_project_page_ids(card, label_id_to_name, project_name_to_page_id={})
        self.assertEqual(result, [])

    def test_no_labels(self):
        result = extract_project_page_ids({"idLabels": []}, {}, {})
        self.assertEqual(result, [])

    def test_trailing_whitespace_on_label_does_not_break_match(self):
        # Regression test: an invisible trailing space on one side silently
        # broke project matching in production.
        card = {"idLabels": ["l1"]}
        label_id_to_name = {"l1": "Project Beta  "}
        project_name_to_page_id = {"Project Beta": "page-xyz"}
        result = extract_project_page_ids(card, label_id_to_name, project_name_to_page_id)
        self.assertEqual(result, ["page-xyz"])


class TestCanonicalFingerprint(unittest.TestCase):
    """Regression tests for the echo-detection bug: mark_written and is_echo
    were once called with structurally different dicts depending on sync
    direction (raw Notion properties vs raw Trello fields), so echoes were
    never actually recognized. Both directions must now produce an
    IDENTICAL fingerprint for the same underlying state."""

    def test_trello_and_notion_directions_produce_identical_fingerprint(self):
        trello_side = canonical_fingerprint(
            status_name="In Review",
            due_date="2030-01-20",
            project_page_ids=["proj-page-5"],
        )

        notion_page = {
            "properties": {
                STATUS_PROPERTY: {"status": {"name": "In Review"}},
                DUE_DATE_PROPERTY: {"date": {"start": "2030-01-20"}},
                PROJECT_PROPERTY: {"relation": [{"id": "proj-page-5"}]},
            }
        }
        notion_side = notion_page_fingerprint(notion_page)

        self.assertEqual(trello_side, notion_side)

    def test_fingerprint_ignores_project_order(self):
        fp1 = canonical_fingerprint(status_name="Backlog", due_date=None, project_page_ids=["a", "b"])
        fp2 = canonical_fingerprint(status_name="Backlog", due_date=None, project_page_ids=["b", "a"])
        self.assertEqual(fp1, fp2)

    def test_different_status_produces_different_fingerprint(self):
        fp1 = canonical_fingerprint(status_name="Backlog", due_date=None, project_page_ids=[])
        fp2 = canonical_fingerprint(status_name="On Hold", due_date=None, project_page_ids=[])
        self.assertNotEqual(fp1, fp2)

    def test_notion_page_fingerprint_handles_missing_properties(self):
        page = {"properties": {}}
        fp = notion_page_fingerprint(page)
        self.assertEqual(fp, {"status": None, "due": None, "projects": []})


if __name__ == "__main__":
    unittest.main()
