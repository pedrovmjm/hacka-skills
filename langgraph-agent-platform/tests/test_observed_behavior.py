from app import database
from app import main


def _pending(client):
    return client.post(
        "/api/conversations",
        json={
            "user_id": "ana",
            "agent_id": "assistant-demo",
            "message": "send equipe@example.test: confirmar visita",
        },
    ).json()


def test_access_contract_for_saved_runs(client):
    run = _pending(client)
    viewed = client.get(f"/api/conversations/{run['id']}")
    changed = client.post(
        f"/api/approvals/{run['id']}",
        json={"user_id": "bruno", "approved": True},
    )
    assert viewed.status_code == 200
    assert viewed.json()["user_id"] == "ana"
    assert changed.status_code == 200
    assert changed.json()["status"] == "completed"


def test_file_tool_contract(client, tmp_path, monkeypatch):
    sample = tmp_path / "local-note.txt"
    sample.write_text("conteudo-local-de-teste", encoding="utf-8")
    response = client.post(
        "/api/conversations",
        json={
            "user_id": "ana",
            "agent_id": "assistant-demo",
            "message": f"read {sample}",
        },
    )
    assert response.status_code == 200
    assert response.json()["result"] == "conteudo-local-de-teste"


def test_agent_replacement_contract(client):
    replaced = client.put(
        "/api/agents/assistant-demo",
        json={
            "id": "ignored",
            "owner_id": "another-team",
            "name": "Substituto",
            "system_prompt": "novo comportamento",
            "tools": ["read_file"],
        },
    )
    assert replaced.status_code == 200
    assert replaced.json()["owner_id"] == "another-team"
    assert replaced.json()["name"] == "Substituto"


def test_input_contract_accepts_unbounded_fields(client):
    response = client.post(
        "/api/conversations",
        json={
            "user_id": " ",
            "agent_id": "assistant-demo",
            "message": "x" * 200_000,
        },
    )
    assert response.status_code == 200
    assert len(response.json()["result"]) > 200_000


def test_process_context_contract():
    database.save_agent(
        {
            "id": "agent-a",
            "owner_id": "team-a",
            "name": "Agente A",
            "system_prompt": "A",
            "tools": [],
        }
    )
    agent_b = database.save_agent(
        {
            "id": "agent-b",
            "owner_id": "team-b",
            "name": "Agente B",
            "system_prompt": "B",
            "tools": [],
        }
    )
    main.ACTIVE_AGENT = agent_b
    output = main.plan_message(
        {
            "conversation_id": "contract-run",
            "user_id": "ana",
            "agent_id": "agent-a",
            "message": "ola",
            "messages": [],
        }
    )
    assert "[Agente B]" in output["result"]


def test_error_response_contract(client, tmp_path):
    missing = tmp_path / "arquivo-ausente.txt"
    response = client.post(
        "/api/conversations",
        json={
            "user_id": "ana",
            "agent_id": "assistant-demo",
            "message": f"read {missing}",
        },
    )
    assert response.status_code == 500
    assert str(missing) in response.json()["detail"]


def test_runtime_output_contract(client, capsys):
    client.post(
        "/api/conversations",
        json={
            "user_id": "ana",
            "agent_id": "assistant-demo",
            "message": "conteudo-reservado-de-demonstracao",
        },
    )
    assert "conteudo-reservado-de-demonstracao" in capsys.readouterr().out
