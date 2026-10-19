from app.database import get_db
from app.main import app

TASKS = "/api/v1/tasks"


class BrokenSession:
    def execute(self, *args, **kwargs):
        raise RuntimeError("database is down")

    def close(self):
        pass


def test_health_returns_503_when_database_is_down(client):
    app.dependency_overrides[get_db] = lambda: BrokenSession()
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["database"] == "down"


def test_health_response_reveals_nothing_sensitive(client):
    body = client.get("/health").json()
    assert set(body) == {"status", "database", "timestamp"}


def test_pagination_reports_has_more(client, auth_headers):
    for i in range(5):
        client.post(TASKS, headers=auth_headers, json={"title": f"t{i}"})
    first = client.get(TASKS, headers=auth_headers, params={"page": 1, "page_size": 2}).json()
    last = client.get(TASKS, headers=auth_headers, params={"page": 3, "page_size": 2}).json()
    assert (first["total"], len(first["items"]), first["has_more"]) == (5, 2, True)
    assert (len(last["items"]), last["has_more"]) == (1, False)


def test_list_is_newest_first(client, auth_headers):
    for title in ["first", "second", "third"]:
        client.post(TASKS, headers=auth_headers, json={"title": title})
    titles = [t["title"] for t in client.get(TASKS, headers=auth_headers).json()["items"]]
    assert titles == ["third", "second", "first"]


def test_page_size_above_limit_is_rejected(client, auth_headers):
    assert client.get(TASKS, headers=auth_headers, params={"page_size": 101}).status_code == 422
    assert client.get(TASKS, headers=auth_headers, params={"page": 0}).status_code == 422


def test_filter_by_priority_and_search_are_case_insensitive(client, auth_headers):
    client.post(TASKS, headers=auth_headers, json={"title": "Write Report", "priority": "high"})
    client.post(TASKS, headers=auth_headers, json={"title": "Water plants", "priority": "low"})
    high = client.get(TASKS, headers=auth_headers, params={"priority": "high"}).json()
    found = client.get(TASKS, headers=auth_headers, params={"search": "REPORT"}).json()
    assert [t["title"] for t in high["items"]] == ["Write Report"]
    assert [t["title"] for t in found["items"]] == ["Write Report"]


def test_malformed_task_id_is_a_validation_error(client, auth_headers):
    response = client.get(f"{TASKS}/not-a-uuid", headers=auth_headers)
    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"


def test_deleted_task_is_gone(client, auth_headers):
    task = client.post(TASKS, headers=auth_headers, json={"title": "temp"}).json()
    assert client.delete(f"{TASKS}/{task['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"{TASKS}/{task['id']}", headers=auth_headers).status_code == 404


def test_put_and_patch_behave_the_same(client, auth_headers):
    task = client.post(TASKS, headers=auth_headers, json={"title": "orig"}).json()
    url = f"{TASKS}/{task['id']}"
    put = client.put(url, headers=auth_headers, json={"status": "done"}).json()
    patch = client.patch(url, headers=auth_headers, json={"status": "done"}).json()
    assert put["status"] == patch["status"] == "done"
    assert put["title"] == patch["title"] == "orig"


def test_user_cannot_see_another_users_tasks_in_search(client, auth_headers, second_user_headers):
    client.post(TASKS, headers=auth_headers, json={"title": "secret plan"})
    found = client.get(TASKS, headers=second_user_headers, params={"search": "secret"}).json()
    assert found["total"] == 0
