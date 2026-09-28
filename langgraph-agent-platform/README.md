# Plataforma de agentes com LangGraph

API ficticia para configurar agentes e executar conversas com ferramentas. O modelo padrao e deterministico e local: nao ha custos, chaves ou chamadas a provedores de IA. Agentes, conversas e checkpoints sao persistidos em SQLite.

## Pre-requisitos

- Python 3.12+
- Opcional: Docker

## Instalacao nativa

No PowerShell:

```powershell
cd langgraph-agent-platform
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

No macOS/Linux, troque a ativacao por `source .venv/bin/activate`.

## Execucao

```bash
uvicorn app.main:app --reload --port 8000
```

Abra `http://localhost:8000/docs`. Por padrao, os dados ficam em `data/agents.db` e os checkpoints em `data/checkpoints.db`. Os caminhos podem ser alterados com `AGENT_DB_PATH` e `AGENT_CHECKPOINT_PATH`.

Com Docker:

```bash
docker build -t legacy-agent-platform .
docker run --rm -p 8000:8000 legacy-agent-platform
```

## Dados e comandos de demonstracao

O agente inicial tem ID `assistant-demo`, pertence ao time ficticio `team-demo` e oferece tres comandos reconhecidos pelo modelo simulado:

- texto livre: resposta ecoada pelo modelo local;
- `policy travel` ou `policy security`: consulta uma politica ficticia;
- `read <caminho>`: usa a ferramenta de leitura configurada;
- `send destinatario: mensagem`: cria uma acao de notificacao que fica aguardando decisao humana.

Usuarios como `ana` e `bruno` sao identificadores ficticios enviados no corpo das requisicoes.

## Endpoints

| Metodo | Caminho | Uso |
| --- | --- | --- |
| GET | `/health` | Verifica a API e o tipo de modelo. |
| GET | `/api/agents` | Lista agentes. |
| PUT | `/api/agents/{id}` | Cria ou atualiza configuracao. |
| POST | `/api/conversations` | Inicia ou continua uma conversa. |
| GET | `/api/conversations/{id}` | Recupera estado e historico. |
| POST | `/api/approvals/{id}` | Aprova ou recusa a acao pendente. |

Fluxo de conversa simples:

```bash
curl -s -X POST http://localhost:8000/api/conversations \
  -H "Content-Type: application/json" \
  -d '{"user_id":"ana","agent_id":"assistant-demo","message":"policy travel"}'
```

Fluxo HITL completo:

```bash
curl -s -X POST http://localhost:8000/api/conversations \
  -H "Content-Type: application/json" \
  -d '{"user_id":"ana","agent_id":"assistant-demo","message":"send equipe@example.test: reuniao as 10h"}'

# Copie o campo id da resposta anterior.
curl -s -X POST http://localhost:8000/api/approvals/CONVERSATION_ID \
  -H "Content-Type: application/json" \
  -d '{"user_id":"ana","approved":true}'

curl -s http://localhost:8000/api/conversations/CONVERSATION_ID
```

## Testes

```bash
python -m pytest -q
```

Os testes de fluxo cobrem catalogo, conversa, historico e interrupcao/aprovacao. A suite de caracterizacao registra outros contratos observaveis do legado para tornar a futura refatoracao comparavel.

Alternativa inteiramente em Docker:

```bash
docker build --target test -t agent-platform-test .
docker run --rm agent-platform-test
```
