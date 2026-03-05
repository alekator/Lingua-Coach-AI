from fastapi.testclient import TestClient


def test_bootstrap_first_run_creates_local_user(client: TestClient) -> None:
    response = client.get("/app/bootstrap")
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == 1
    assert body["has_profile"] is False
    assert body["needs_onboarding"] is True
    assert body["next_step"] == "onboarding"
    assert body["owner_user_id"] == 1
    assert body["active_workspace_id"] is None


def test_bootstrap_after_profile_setup_goes_to_dashboard(client: TestClient) -> None:
    setup = client.post(
        "/profile/setup",
        json={
            "user_id": 1,
            "native_lang": "ru",
            "target_lang": "en",
            "level": "A2",
            "goal": "travel",
            "preferences": {},
        },
    )
    assert setup.status_code == 200

    response = client.get("/app/bootstrap")
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] != 1
    assert body["has_profile"] is True
    assert body["needs_onboarding"] is False
    assert body["next_step"] == "dashboard"
    assert body["owner_user_id"] == 1
    assert body["active_workspace_id"] is not None
