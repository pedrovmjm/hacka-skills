from app import database


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_monthly_attendance_summary_uses_seed_data(client, ana_headers):
    month = database.current_month()
    response = client.get(
        "/api/attendance",
        params={"user_id": "ana", "month": month},
        headers=ana_headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "ana",
        "month": month,
        "goal": 8,
        "present_count": 2,
        "remaining_count": 6,
        "progress_percent": 25,
        "days": response.json()["days"],
    }
    assert len(response.json()["days"]) == 2
    assert set(response.json()["days"][0]) == {
        "id",
        "user_id",
        "attendance_date",
        "status",
        "notes",
        "created_at",
        "updated_at",
    }


def test_marks_updates_and_removes_a_day(client, ana_headers):
    month = database.current_month()
    attendance_date = f"{month}-15"
    created = client.put(
        f"/api/attendance/{attendance_date}",
        headers=ana_headers,
        json={"user_id": "ana", "notes": "Polo"},
    )
    assert created.status_code == 200
    assert created.json()["attendance_date"] == attendance_date
    assert created.json()["status"] == "present"
    created_at = created.json()["created_at"]

    updated = client.put(
        f"/api/attendance/{attendance_date}",
        headers=ana_headers,
        json={"user_id": "ana", "notes": "Observação corrigida"},
    )
    assert updated.status_code == 200
    assert updated.json()["id"] == created.json()["id"]
    assert updated.json()["created_at"] == created_at
    assert updated.json()["status"] == "present"
    assert updated.json()["notes"] == "Observação corrigida"

    removed = client.delete(
        f"/api/attendance/{attendance_date}",
        params={"user_id": "ana"},
        headers=ana_headers,
    )
    assert removed.status_code == 200
    assert removed.json() == {
        "attendance_date": attendance_date,
        "status": "unmarked",
    }
    summary = client.get(
        "/api/attendance",
        params={"user_id": "ana", "month": month},
        headers=ana_headers,
    ).json()
    assert all(day["attendance_date"] != attendance_date for day in summary["days"])


def test_progress_is_capped_at_one_hundred_percent(client, ana_headers):
    month = database.current_month()
    for day in range(11, 20):
        response = client.put(
            f"/api/attendance/{month}-{day}",
            headers=ana_headers,
            json={"user_id": "ana", "notes": ""},
        )
        assert response.status_code == 200

    summary = client.get(
        "/api/attendance",
        params={"user_id": "ana", "month": month},
        headers=ana_headers,
    ).json()
    assert summary["present_count"] == 11
    assert summary["remaining_count"] == 0
    assert summary["progress_percent"] == 100


def test_manager_monthly_view_and_manager_without_team(client, ana_headers):
    month = database.current_month()
    response = client.get(
        "/api/team-attendance",
        params={"manager_id": "ana", "month": month},
        headers=ana_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["manager_id"] == "ana"
    assert body["month"] == month
    assert body["goal"] == 8
    assert body["team_size"] == 3
    assert body["team_present_total"] == 6
    assert body["team_average"] == 2.0
    assert [member["user_id"] for member in body["members"]] == [
        "bruno",
        "carla",
        "diego",
    ]
    assert [member["present_count"] for member in body["members"]] == [2, 4, 0]
    assert all("days" in member for member in body["members"])

    empty = client.get(
        "/api/team-attendance",
        params={"manager_id": "bruno", "month": month},
        headers=ana_headers,
    )
    assert empty.status_code == 200
    assert empty.json()["team_size"] == 0
    assert empty.json()["team_average"] == 0
    assert empty.json()["members"] == []


def test_attendance_endpoints_require_x_user(client):
    month = database.current_month()
    assert client.get(
        "/api/attendance", params={"user_id": "ana", "month": month}
    ).status_code == 422
    assert client.get(
        "/api/team-attendance", params={"manager_id": "ana", "month": month}
    ).status_code == 422
