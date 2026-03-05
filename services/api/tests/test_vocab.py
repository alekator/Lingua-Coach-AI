from __future__ import annotations

from fastapi.testclient import TestClient


def test_vocab_add_and_list(client: TestClient) -> None:
    added = client.post(
        "/vocab/add",
        json={
            "user_id": 501,
            "word": "achieve",
            "translation": "to achieve",
            "example": "I want to achieve my goals.",
        },
    )
    assert added.status_code == 200
    body = added.json()
    assert body["word"] == "achieve"
    assert body["interval_days"] == 1
    assert body["ease"] == 2.5

    listing = client.get("/vocab", params={"user_id": 501})
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert len(items) == 1
    assert items[0]["word"] == "achieve"


def test_vocab_review_next_and_submit(client: TestClient) -> None:
    added = client.post(
        "/vocab/add",
        json={
            "user_id": 777,
            "word": "mistake",
            "translation": "error",
        },
    )
    vocab_item_id = added.json()["id"]

    first_next = client.post("/vocab/review/next", json={"user_id": 777})
    assert first_next.status_code == 200
    next_payload = first_next.json()
    assert next_payload["has_item"] is True
    assert next_payload["item"]["id"] == vocab_item_id

    submit = client.post(
        "/vocab/review/submit",
        json={"user_id": 777, "vocab_item_id": vocab_item_id, "rating": "good"},
    )
    assert submit.status_code == 200
    submit_payload = submit.json()
    assert submit_payload["interval_days"] >= 2
    assert submit_payload["ease"] >= 2.5
