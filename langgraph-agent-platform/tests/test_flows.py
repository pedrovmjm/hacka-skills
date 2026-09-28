def test_health_and_agent_catalog(client):
    assert client.get("/health").json() == {"status": "ok", "model": "simulated"}
    agents = client.get("/api/agents").json()
    assert agents[0]["id"] == "assistant-demo"
    assert "send_notification" in agents[0]["tools"]


def test_conversation_uses_the_simulated_model_and_keeps_history(client):
    first = client.post(
        "/api/conversations",
        json={
            "user_id": "ana",
            "agent_id": "assistant-demo",
            "message": "Ola",
        },
    )
    assert first.status_code == 200
    body = first.json()
    assert body["status"] == "completed"
    assert "modelo-simulado: Ola" in body["result"]

    second = client.post(
        "/api/conversations",
        json={
            "user_id": "ana",
            "agent_id": "assistant-demo",
            "message": "policy travel",
            "conversation_id": body["id"],
        },
    ).json()
    assert second["status"] == "completed"
    assert "sete dias" in second["result"]
    assert len(second["messages"]) == 4


def test_notification_waits_for_a_human_decision(client):
    requested = client.post(
        "/api/conversations",
        json={
            "user_id": "ana",
            "agent_id": "assistant-demo",
            "message": "send equipe@example.test: reuniao as 10h",
        },
    ).json()
    assert requested["status"] == "pending_approval"
    assert requested["pending_action"]["tool"] == "send_notification"

    approved = client.post(
        f"/api/approvals/{requested['id']}",
        json={"user_id": "ana", "approved": True},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "completed"
    assert "Notificacao enviada" in approved.json()["result"]

    persisted = client.get(f"/api/conversations/{requested['id']}").json()
    assert persisted["status"] == "completed"
    assert len(persisted["messages"]) == 3


def test_notification_can_be_rejected(client):
    requested = client.post(
        "/api/conversations",
        json={
            "user_id": "ana",
            "agent_id": "assistant-demo",
            "message": "send equipe@example.test: mensagem opcional",
        },
    ).json()
    assert requested["status"] == "pending_approval"

    rejected = client.post(
        f"/api/approvals/{requested['id']}",
        json={"user_id": "ana", "approved": False},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["result"] == "Acao recusada."

    persisted = client.get(f"/api/conversations/{requested['id']}").json()
    assert persisted["status"] == "rejected"


def test_configures_and_uses_an_agent(client):
    configured = client.put(
        "/api/agents/policy-agent",
        json={
            "id": "policy-agent",
            "owner_id": "team-demo",
            "name": "Agente de politicas",
            "system_prompt": "Consulte politicas ficticias.",
            "tools": ["lookup_policy"],
        },
    )
    assert configured.status_code == 200
    assert configured.json()["id"] == "policy-agent"

    response = client.post(
        "/api/conversations",
        json={
            "user_id": "ana",
            "agent_id": "policy-agent",
            "message": "policy security",
        },
    )
    assert response.status_code == 200
    assert "tokens" in response.json()["result"]
