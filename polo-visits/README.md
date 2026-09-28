# Gestao de idas ao polo

Aplicacao ficticia para planejar e registrar visitas presenciais a um polo. Neste projeto, uma "ida ao polo" e um agendamento com visitante, data, horario, finalidade, observacoes, acompanhantes e status. A interface permite consultar, pesquisar, criar, alterar e cancelar visitas, alem de acompanhar um resumo.

Todos os nomes e registros sao demonstrativos.

## Estrutura e pre-requisitos

- `backend/`: Python 3.12+, FastAPI e SQLite.
- `frontend/`: Node.js 22+, React e Vite.
- Opcional: Docker e Docker Compose.

## Backend

O backend está organizado em arquitetura hexagonal. As dependências apontam para o
núcleo da aplicação, enquanto FastAPI e SQLite ficam nas bordas:

```text
backend/app/
├── domain/                    # Modelos, erros e porta de persistência
├── application/               # Casos de uso de visitas
├── adapters/
│   ├── http/                  # Adaptador de entrada FastAPI
│   └── persistence/           # Adaptador de saída SQLite
├── main.py                    # Composição das dependências
└── database.py                # Fachada de compatibilidade do legado
```

Fluxo de dependências:

```text
HTTP/FastAPI -> casos de uso -> porta do domínio <- SQLite
```

Essa organização é propositalmente apenas estrutural. Os comportamentos legados,
inclusive os inadequados usados na avaliação da futura skill, continuam preservados.

Instalacao no PowerShell:

```powershell
cd polo-visits\backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8001
```

No macOS/Linux, use `source .venv/bin/activate`. A documentacao interativa fica em `http://localhost:8001/docs`. O banco padrao e `backend/data/polo.db`; `POLO_DB_PATH` permite escolher outro arquivo.

Endpoints:

| Metodo | Caminho | Uso |
| --- | --- | --- |
| GET | `/health` | Estado da API. |
| GET | `/api/visits?user_id=ana&q=` | Lista e pesquisa visitas. |
| POST | `/api/visits` | Agenda uma ida. |
| PUT | `/api/visits/{id}` | Altera um agendamento. |
| DELETE | `/api/visits/{id}` | Cancela um agendamento. |
| GET | `/api/summary?user_id=ana` | Resume quantidades por status. |

As chamadas de demonstracao enviam `X-User: ana` ou `X-User: bruno`. Exemplo:

```bash
curl -s "http://localhost:8001/api/visits?user_id=ana" -H "X-User: ana"

curl -s -X POST http://localhost:8001/api/visits \
  -H "Content-Type: application/json" -H "X-User: ana" \
  -d '{"user_id":"ana","visitor_name":"Ana Demo","visit_date":"2026-10-15","start_time":"13:30","purpose":"Laboratorio presencial","notes":"Levar notebook","companions":0}'
```

Dados iniciais:

- Ana Demo: uma visita agendada em `2026-10-05` e uma concluida em `2026-09-12`.
- Bruno Demo: uma visita agendada em `2026-10-06`.

Testes do backend:

```bash
cd backend
python -m pytest -q
```

Alternativa inteiramente em Docker:

```bash
docker build --target test -t polo-api-test backend
docker run --rm polo-api-test
```

## Frontend

Com a API na porta 8001:

```bash
cd polo-visits/frontend
npm install
npm run dev
```

Abra `http://localhost:5173`. Use o seletor de perfil para navegar entre os dados ficticios, preencha o formulario para agendar, e use os botoes dos cards para alterar ou cancelar.

Testes e build:

```bash
npm test
npm run build
```

Alternativa de teste em Docker:

```bash
docker build --target test -t polo-web-test frontend
docker run --rm polo-web-test
```

E2E real do navegador contra os servicos do Compose:

```bash
# Na raiz do repositorio
docker compose up --build -d
docker build --target e2e -t polo-web-e2e polo-visits/frontend
docker run --rm --add-host=host.docker.internal:host-gateway polo-web-e2e
```

O harness reescreve apenas o host da API dentro do container do navegador; as requisicoes continuam chegando ao FastAPI real publicado na porta 8001.

## Docker Compose

A partir da raiz do repositorio:

```bash
docker compose up --build -d polo-api polo-web
```

Interface: `http://localhost:5173`; API: `http://localhost:8001/docs`.

## Fluxo manual de validacao

1. Abra a interface como Ana e confirme o resumo e as duas visitas iniciais.
2. Agende uma visita futura e confirme que ela aparece na lista e no resumo.
3. Abra a edicao, altere data ou finalidade e salve.
4. Cancele o agendamento e confirme o novo status no resumo.
5. Troque para Bruno e confirme a carga do outro conjunto ficticio.
