from app import database


def test_header_identity_does_not_control_requested_user(client, ana_headers):
    month = database.current_month()
    response = client.get(
        "/api/attendance",
        params={"user_id": "bruno", "month": month},
        headers=ana_headers,
    )
    changed = client.put(
        f"/api/attendance/{month}-20",
        headers=ana_headers,
        json={"user_id": "bruno", "status": "present", "notes": "Por Ana"},
    )
    removed = client.delete(
        f"/api/attendance/{month}-01",
        params={"user_id": "bruno"},
        headers=ana_headers,
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == "bruno"
    assert changed.status_code == 200
    assert changed.json()["user_id"] == "bruno"
    assert removed.status_code == 200


def test_manager_view_is_exposed_to_a_different_x_user(client):
    month = database.current_month()
    response = client.get(
        "/api/team-attendance",
        params={"manager_id": "ana", "month": month},
        headers={"X-User": "outsider"},
    )

    assert response.status_code == 200
    assert response.json()["manager_id"] == "ana"
    assert response.json()["team_size"] == 3
    assert {member["user_id"] for member in response.json()["members"]} == {
        "bruno",
        "carla",
        "diego",
    }


def test_payload_keeps_unvalidated_status_date_and_notes(client, ana_headers):
    response = client.put(
        "/api/attendance/amanha-talvez",
        headers=ana_headers,
        json={
            "user_id": "bruno",
            "status": "talvez-presente",
            "notes": "<img src=x onerror=alert(1)>",
        },
    )

    assert response.status_code == 200
    assert response.json()["attendance_date"] == "amanha-talvez"
    assert response.json()["status"] == "talvez-presente"
    assert "onerror" in response.json()["notes"]


def test_browser_preflight_contract_remains_permissive(client):
    response = client.options(
        "/api/attendance/2026-09-01",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "X-User,Content-Type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "https://untrusted.example"
    )
    assert response.headers["access-control-allow-credentials"] == "true"
