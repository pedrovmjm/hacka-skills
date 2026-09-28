from app import database


def test_identity_contract_across_records(client, ana_headers):
    bruno = client.get("/api/visits?user_id=bruno", headers=ana_headers)
    assert bruno.status_code == 200
    target = bruno.json()[0]
    summary = client.get("/api/summary?user_id=bruno", headers=ana_headers)

    changed = client.put(
        f"/api/visits/{target['id']}",
        headers=ana_headers,
        json={
            "visitor_name": target["visitor_name"],
            "visit_date": target["visit_date"],
            "start_time": target["start_time"],
            "purpose": "Alterado por outro cabecalho",
            "notes": target["notes"],
            "companions": target["companions"],
            "status": target["status"],
        },
    )
    cancelled = client.delete(f"/api/visits/{target['id']}", headers=ana_headers)
    assert changed.status_code == 200
    assert changed.json()["purpose"] == "Alterado por outro cabecalho"
    assert cancelled.status_code == 200
    assert summary.status_code == 200
    assert summary.json()["user_id"] == "bruno"


def test_search_contract_with_sql_metacharacters(client, ana_headers):
    value = "inexistente%' OR 1=1 --"
    response = client.get(
        "/api/visits",
        params={"user_id": "ana", "q": value},
        headers=ana_headers,
    )
    assert response.status_code == 200
    assert {item["user_id"] for item in response.json()} == {"ana", "bruno"}


def test_payload_contract_keeps_supplied_values(client, ana_headers):
    response = client.post(
        "/api/visits",
        headers=ana_headers,
        json={
            "user_id": "bruno",
            "visitor_name": "Visitante de teste",
            "visit_date": "amanha-talvez",
            "start_time": "25:90",
            "purpose": "Teste local",
            "notes": "<img src=x onerror=alert(1)>",
            "companions": -4,
        },
    )
    assert response.status_code == 201
    assert response.json()["visit_date"] == "amanha-talvez"
    assert response.json()["companions"] == -4
    assert "onerror" in response.json()["notes"]


def test_update_contract_for_capacity_and_status(client, ana_headers):
    for number in range(4):
        response = client.post(
            "/api/visits",
            headers=ana_headers,
            json={
                "user_id": "ana",
                "visitor_name": f"Pessoa {number}",
                "visit_date": "2026-10-05",
                "start_time": f"1{number}:00",
                "purpose": "Atividade",
            },
        )
        assert response.status_code == 201

    source = client.post(
        "/api/visits",
        headers=ana_headers,
        json={
            "user_id": "ana",
            "visitor_name": "Pessoa extra",
            "visit_date": "2026-10-20",
            "start_time": "16:00",
            "purpose": "Atividade",
        },
    ).json()
    moved = client.put(
        f"/api/visits/{source['id']}",
        headers=ana_headers,
        json={
            "visitor_name": source["visitor_name"],
            "visit_date": "2026-10-05",
            "start_time": source["start_time"],
            "purpose": source["purpose"],
            "notes": "",
            "companions": 0,
            "status": "vip-confirmed",
        },
    )
    total = database.connection.execute(
        "SELECT COUNT(*) AS total FROM visits WHERE visit_date = '2026-10-05'"
    ).fetchone()["total"]
    assert moved.status_code == 200
    assert moved.json()["status"] == "vip-confirmed"
    assert total == 6


def test_browser_preflight_contract(client):
    response = client.options(
        "/api/visits/1",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "DELETE",
            "Access-Control-Request-Headers": "X-User",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://untrusted.example"
    assert response.headers["access-control-allow-credentials"] == "true"
