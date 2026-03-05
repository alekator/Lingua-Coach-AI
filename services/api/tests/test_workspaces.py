from fastapi.testclient import TestClient


def test_workspaces_create_list_switch_and_active(client: TestClient) -> None:
    initial = client.get("/workspaces")
    assert initial.status_code == 200
    assert initial.json()["items"] == []
    assert initial.json()["active_workspace_id"] is None

    first = client.post(
        "/workspaces",
        json={"native_lang": "ru", "target_lang": "en", "goal": "travel", "make_active": True},
    )
    assert first.status_code == 200
    first_ws = first.json()
    assert first_ws["native_lang"] == "ru"
    assert first_ws["target_lang"] == "en"
    assert first_ws["is_active"] is True

    active = client.get("/workspaces/active")
    assert active.status_code == 200
    first_active_user_id = active.json()["active_user_id"]
    assert first_active_user_id != 1

    second = client.post(
        "/workspaces",
        json={"native_lang": "de", "target_lang": "en", "goal": "job", "make_active": False},
    )
    assert second.status_code == 200
    second_ws = second.json()
    assert second_ws["is_active"] is False
    assert second_ws["id"] != first_ws["id"]

    listed = client.get("/workspaces")
    assert listed.status_code == 200
    body = listed.json()
    assert len(body["items"]) == 2
    assert body["active_workspace_id"] == first_ws["id"]

    switched = client.post("/workspaces/switch", json={"workspace_id": second_ws["id"]})
    assert switched.status_code == 200
    switched_body = switched.json()
    assert switched_body["active_workspace_id"] == second_ws["id"]
    assert switched_body["active_user_id"] != first_active_user_id

    active_after = client.get("/workspaces/active")
    assert active_after.status_code == 200
    assert active_after.json()["active_workspace_id"] == second_ws["id"]


def test_workspace_profiles_are_isolated_between_language_pairs(client: TestClient) -> None:
    setup_a = client.post(
        "/profile/setup",
        json={
            "user_id": 1,
            "native_lang": "de",
            "target_lang": "en",
            "level": "A2",
            "goal": "travel",
            "preferences": {},
        },
    )
    assert setup_a.status_code == 200
    user_a = setup_a.json()["user_id"]
    assert user_a != 1

    setup_b = client.post(
        "/profile/setup",
        json={
            "user_id": 1,
            "native_lang": "es",
            "target_lang": "ru",
            "level": "B1",
            "goal": "relocation",
            "preferences": {},
        },
    )
    assert setup_b.status_code == 200
    user_b = setup_b.json()["user_id"]
    assert user_b != 1
    assert user_b != user_a

    bootstrap = client.get("/app/bootstrap")
    assert bootstrap.status_code == 200
    assert bootstrap.json()["user_id"] == user_b

    all_workspaces = client.get("/workspaces")
    assert all_workspaces.status_code == 200
    items = all_workspaces.json()["items"]
    de_en = next(item for item in items if item["native_lang"] == "de" and item["target_lang"] == "en")
    es_ru = next(item for item in items if item["native_lang"] == "es" and item["target_lang"] == "ru")

    switch_a = client.post("/workspaces/switch", json={"workspace_id": de_en["id"]})
    assert switch_a.status_code == 200
    assert switch_a.json()["active_user_id"] == user_a

    profile_a = client.get("/profile", params={"user_id": user_a})
    assert profile_a.status_code == 200
    assert profile_a.json()["native_lang"] == "de"
    assert profile_a.json()["target_lang"] == "en"
    assert profile_a.json()["level"] == "A2"

    switch_b = client.post("/workspaces/switch", json={"workspace_id": es_ru["id"]})
    assert switch_b.status_code == 200
    assert switch_b.json()["active_user_id"] == user_b

    profile_b = client.get("/profile", params={"user_id": user_b})
    assert profile_b.status_code == 200
    assert profile_b.json()["native_lang"] == "es"
    assert profile_b.json()["target_lang"] == "ru"
    assert profile_b.json()["level"] == "B1"


def test_workspace_overview_returns_per_space_metrics(client: TestClient) -> None:
    setup_a = client.post(
        "/profile/setup",
        json={
            "user_id": 1,
            "native_lang": "de",
            "target_lang": "en",
            "level": "A2",
            "goal": "job",
            "preferences": {},
        },
    )
    assert setup_a.status_code == 200
    user_a = setup_a.json()["user_id"]

    setup_b = client.post(
        "/profile/setup",
        json={
            "user_id": 1,
            "native_lang": "es",
            "target_lang": "ru",
            "level": "B1",
            "goal": "travel",
            "preferences": {},
        },
    )
    assert setup_b.status_code == 200
    user_b = setup_b.json()["user_id"]

    vocab = client.post(
        "/vocab/add",
        json={"user_id": user_a, "word": "hiring", "translation": "naim"},
    )
    assert vocab.status_code == 200

    chat_start = client.post("/chat/start", json={"user_id": user_b, "mode": "chat"})
    assert chat_start.status_code == 200

    overview = client.get("/workspaces/overview")
    assert overview.status_code == 200
    payload = overview.json()
    assert payload["owner_user_id"] == 1
    assert len(payload["items"]) == 2

    de_en = next(item for item in payload["items"] if item["native_lang"] == "de" and item["target_lang"] == "en")
    es_ru = next(item for item in payload["items"] if item["native_lang"] == "es" and item["target_lang"] == "ru")

    assert de_en["has_profile"] is True
    assert de_en["goal"] == "job"
    assert de_en["words_learned"] >= 1

    assert es_ru["has_profile"] is True
    assert es_ru["goal"] == "travel"
    assert es_ru["minutes_practiced"] >= 8
