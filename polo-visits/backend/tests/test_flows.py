def test_lists_demo_visits_and_summary(client, ana_headers):
    visits = client.get("/api/visits?user_id=ana", headers=ana_headers)
    assert visits.status_code == 200
    assert len(visits.json()) == 2
    assert {item["status"] for item in visits.json()} == {"scheduled", "completed"}

    summary = client.get("/api/summary?user_id=ana", headers=ana_headers)
    assert summary.status_code == 200
    assert summary.json()["scheduled"] == 1
    assert summary.json()["completed"] == 1

    search = client.get(
        "/api/visits",
        params={"user_id": "ana", "q": "Aula"},
        headers=ana_headers,
    )
    assert search.status_code == 200
    assert len(search.json()) == 1
    assert search.json()[0]["purpose"] == "Aula presencial"


def test_schedules_edits_and_cancels_a_visit(client, ana_headers):
    created = client.post(
        "/api/visits",
        headers=ana_headers,
        json={
            "user_id": "ana",
            "visitor_name": "Ana Demo",
            "visit_date": "2026-10-15",
            "start_time": "13:30",
            "purpose": "Laboratorio presencial",
            "notes": "Levar notebook de teste",
            "companions": 0,
        },
    )
    assert created.status_code == 201
    visit_id = created.json()["id"]

    updated = client.put(
        f"/api/visits/{visit_id}",
        headers=ana_headers,
        json={
            "visitor_name": "Ana Demo",
            "visit_date": "2026-10-16",
            "start_time": "15:00",
            "purpose": "Laboratorio presencial - turma B",
            "notes": "Horario atualizado",
            "companions": 1,
            "status": "scheduled",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["visit_date"] == "2026-10-16"

    cancelled = client.delete(f"/api/visits/{visit_id}", headers=ana_headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    summary = client.get("/api/summary?user_id=ana", headers=ana_headers).json()
    assert summary["cancelled"] == 1
