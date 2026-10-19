import pytest

from app.core.sanitize import sanitize_text

TASKS = "/api/v1/tasks"


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("<script>alert(1)</script>Buy milk", "Buy milk"),
        ("<b>bold</b> text", "bold text"),
        ("<img src=x onerror=alert(1)>hi", "hi"),
        ("<style>body{display:none}</style>visible", "visible"),
        ("<!-- hidden -->shown", "shown"),
        ("<<script>script>alert(1)//<</script>/script>", ""),
        ("a < b and c > d", "a < b and c > d"),
        ("Tom &amp; Jerry", "Tom &amp; Jerry"),
        ("  padded  ", "padded"),
        ("bell\x07 and null\x00", "bell and null"),
        ("right\u202eto-left", "rightto-left"),
        ("line1\r\nline2", "line1\nline2"),
    ],
)
def test_sanitize_text(raw, expected):
    assert sanitize_text(raw) == expected


def test_sanitize_is_idempotent():
    once = sanitize_text("<b>x</b> <i>y</i> a < b")
    assert sanitize_text(once) == once


def test_single_line_mode_collapses_line_breaks():
    assert sanitize_text("a\n\n  b\tc", multiline=False) == "a b c"


def test_html_in_title_and_description_is_stripped_on_create(client, auth_headers):
    response = client.post(
        TASKS,
        headers=auth_headers,
        json={
            "title": "<b>Buy</b> milk<script>steal()</script>",
            "description": "<img src=x onerror=alert(1)>Two litres",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Buy milk"
    assert body["description"] == "Two litres"


def test_title_that_is_only_markup_is_rejected(client, auth_headers):
    response = client.post(TASKS, headers=auth_headers, json={"title": "<b></b><script>x</script>"})
    assert response.status_code == 422
    assert response.json()["details"][0]["field"] == "title"


def test_description_over_limit_is_rejected(client, auth_headers):
    response = client.post(
        TASKS, headers=auth_headers, json={"title": "ok", "description": "x" * 5001}
    )
    assert response.status_code == 422


def test_title_over_limit_is_rejected(client, auth_headers):
    response = client.post(TASKS, headers=auth_headers, json={"title": "x" * 201})
    assert response.status_code == 422


def test_blank_description_becomes_null(client, auth_headers):
    response = client.post(TASKS, headers=auth_headers, json={"title": "ok", "description": "   "})
    assert response.status_code == 201
    assert response.json()["description"] is None


def test_update_sanitizes_and_empty_description_clears_it(client, auth_headers):
    created = client.post(
        TASKS, headers=auth_headers, json={"title": "ok", "description": "keep me"}
    ).json()
    url = f"{TASKS}/{created['id']}"

    cleaned = client.patch(url, headers=auth_headers, json={"description": "<b>new</b>"})
    assert cleaned.json()["description"] == "new"

    cleared = client.patch(url, headers=auth_headers, json={"description": ""})
    assert cleared.json()["description"] is None


def test_update_with_markup_only_title_is_rejected(client, auth_headers):
    created = client.post(TASKS, headers=auth_headers, json={"title": "ok"}).json()
    response = client.patch(
        f"{TASKS}/{created['id']}", headers=auth_headers, json={"title": "<i></i>"}
    )
    assert response.status_code == 422


def test_sql_injection_strings_are_stored_and_searched_as_plain_text(client, auth_headers):
    payload = "'; DROP TABLE tasks; --"
    client.post(TASKS, headers=auth_headers, json={"title": payload})
    listing = client.get(TASKS, headers=auth_headers, params={"search": payload})
    assert listing.status_code == 200
    assert [t["title"] for t in listing.json()["items"]] == [payload]
    assert client.get(TASKS, headers=auth_headers).json()["total"] == 1


def test_search_wildcards_match_literally(client, auth_headers):
    for title in ["100% done", "plain task", "snake_case"]:
        client.post(TASKS, headers=auth_headers, json={"title": title})

    percent = client.get(TASKS, headers=auth_headers, params={"search": "%"}).json()
    underscore = client.get(TASKS, headers=auth_headers, params={"search": "_"}).json()
    assert [t["title"] for t in percent["items"]] == ["100% done"]
    assert [t["title"] for t in underscore["items"]] == ["snake_case"]
