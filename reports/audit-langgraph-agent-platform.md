# Auditoria — langgraph-agent-platform

**Commit:** `f2ab54a` · **Auditor:** claude-opus-5-5

## Resumo

A API não tem autenticação nem verificação de posse: qualquer pessoa se passa por qualquer usuário, lê e assume conversas alheias, aprova ações de terceiros e reescreve agentes de outros times. O que bloqueia o release é a ferramenta `read_file`, habilitada no agente padrão e executada sem aprovação humana e sem restrição de caminho, o que entrega a leitura de qualquer arquivo do servidor a quem envia `read <caminho>`. A causa-raiz dominante é a confiança na identidade enviada no corpo e a falta de um ponto único que aplique política (dono, time, aprovação) antes de ler dados ou executar ferramentas. A suíte `tests/test_observed_behavior.py` fixa vários desses comportamentos como contrato e precisa ser reescrita junto com as correções.

| Tipo | CRITICAL | HIGH | MEDIUM | LOW | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Vulnerabilidade | 1 | 4 | 3 | 2 | 10 |
| Bug | 0 | 0 | 1 | 2 | 3 |
| Dívida técnica | 0 | 0 | 2 | 2 | 4 |
| **Total** | **1** | **4** | **6** | **6** | **17** |

**Matriz de risco (impacto × probabilidade)**

| Impacto \ Prob. | Alta | Média | Baixa |
| --- | --- | --- | --- |
| Severo | CRIT-01 | | |
| Alto | HIGH-01, HIGH-02 | HIGH-03, HIGH-04 | MED-05, MED-06 |
| Moderado | MED-01, MED-02 | MED-03, MED-04 | LOW-03, LOW-04, LOW-05, LOW-06 |
| Baixo | LOW-01 | LOW-02 | |

**Baseline:** `python -m pytest -q` → não executado: a máquina não tem Python, Node nem daemon Docker; os testes existentes foram usados como evidência estática.

**Superfície:** Python 3.12 + FastAPI + LangGraph 0.6 (modelo simulado) + SQLite (`agents.db` e `checkpoints.db`) · entradas: `GET /api/agents`, `PUT /api/agents/{id}`, `POST /api/conversations`, `GET /api/conversations/{id}`, `POST /api/approvals/{id}` e as ferramentas `lookup_policy`, `read_file`, `send_notification` acionadas por texto livre · persistência: duas conexões SQLite globais (tabelas `agents`/`conversations` e checkpoints do grafo) · identidade: `user_id` e `owner_id` enviados pelo cliente no corpo, sem autenticação.

## Achados

### CRIT-01 · Qualquer pessoa lê qualquer arquivo do servidor pela ferramenta de leitura do agente

- **Severidade:** CRITICAL (impacto 4 × probabilidade 3). Leitura arbitrária de arquivos (código, `/proc/self/environ`, bancos, segredos) por qualquer pessoa, sem autenticação e com uma única requisição; a ferramenta é acionada por texto livre, o que já está na probabilidade máxima.
- **Tipo:** Vulnerabilidade
- **Categoria:** `SEC-FILE` / CWE-22, CWE-73 · OWASP A01 / LLM06 · **Confiança:** Confirmado (0,95)
- **Local:** `app/main.py:60-61`, `app/main.py:78-80`, `app/database.py:53`

**Evidência**

```python
# app/main.py:60-61 e 78-80
def read_file(path):
    return Path(path).read_text(encoding="utf-8")
...
    if lowered.startswith("read ") and "read_file" in agent["tools"]:
        path = value.split(" ", 1)[1]
        return {"result": read_file(path), "pending_action": None}
```

- **Cenário:** cadeia `POST /api/conversations` → `run_conversation()` (`app/main.py:199-226`) → `graph.invoke` → `plan_message()` → `fake_model()` → `read_file(path)`. O agente semeado `assistant-demo` já vem com `read_file` habilitada (`app/database.py:53`), e quem não tiver um agente com a ferramenta pode criá-lo pelo `PUT /api/agents/{id}` (ver `HIGH-02`). O caminho vem inteiro do texto do usuário: não há `resolve()`, raiz permitida, verificação de symlink, limite de tamanho nem aprovação humana (só `send_notification` passa pelo HITL).
- **Reprodução:** `curl -s -X POST localhost:8000/api/conversations -H "Content-Type: application/json" -d '{"user_id":"x","agent_id":"assistant-demo","message":"read /etc/passwd"}'` → `result` traz o conteúdo do arquivo. O teste `tests/test_observed_behavior.py:29-41` (`test_file_tool_contract`) afirma exatamente esse comportamento com um caminho absoluto fora do projeto.
- **Esperado:** a ferramenta só lê arquivos de uma pasta permitida, com tamanho limitado, e uma ferramenta desse poder exige aprovação humana.
- **Atual:** lê qualquer caminho legível pelo processo (que roda como root na imagem, ver `LOW-04`) e grava o conteúdo no histórico, onde fica legível por terceiros (ver `HIGH-04`).
- **Impacto:** exposição de código-fonte, variáveis de ambiente, chaves e dos próprios bancos SQLite do servidor.

**O que fazer**

1. Em `app/database.py:53`, tirar `read_file` das ferramentas do agente semeado; ferramentas de arquivo devem ser opt-in.
2. Em `app/main.py:60-61`, reescrever `read_file` para aceitar só caminho relativo dentro de uma raiz configurável (`AGENT_FILES_ROOT`), resolvendo symlinks com `resolve()` e checando `is_relative_to`, exigindo arquivo regular e limitando o tamanho.
3. Marcar `read_file` como ferramenta que exige aprovação humana no registro central de ferramentas (ver `MED-06`), para que não execute direto em `fake_model()` (`app/main.py:78-80`).
4. Reescrever `test_file_tool_contract` para afirmar a recusa.

```python
FILES_ROOT = Path(os.getenv("AGENT_FILES_ROOT", "/app/files")).resolve()

def read_file(relative_path: str) -> str:
    target = (FILES_ROOT / relative_path).resolve()
    if not target.is_relative_to(FILES_ROOT) or not target.is_file():
        raise ToolDenied("Arquivo fora da área permitida.")
    if target.stat().st_size > 64_000:
        raise ToolDenied("Arquivo grande demais.")
    return target.read_text(encoding="utf-8")
```

**Validação:** teste com `read /etc/passwd`, `read ../app/main.py` e um symlink que aponte para fora da raiz → recusa sem conteúdo no `result` nem no histórico · arquivo dentro de `AGENT_FILES_ROOT` continua sendo lido após aprovação.

### HIGH-01 · A API não autentica ninguém: qualquer pessoa se passa por qualquer usuário informando o nome no corpo

- **Severidade:** HIGH (impacto 3 × probabilidade 3). Qualquer cliente age em nome de qualquer usuário em todas as rotas, sem conta e sem interação da vítima.
- **Tipo:** Vulnerabilidade
- **Categoria:** `SEC-AUTHN` / CWE-306, CWE-290 · OWASP A07 · **Confiança:** Confirmado (0,95)
- **Local:** `app/main.py:28-45`, `app/main.py:187-257`, `app/main.py:212`, `app/main.py:250`

**Evidência**

```python
# app/main.py:36-45
class ConversationInput(BaseModel):
    user_id: str
    ...
class ApprovalInput(BaseModel):
    user_id: str
    approved: bool
```

- **Cenário:** nenhuma rota declara dependência de autenticação (`app/main.py:182-257`); a identidade é o `user_id` do corpo, gravado como dono da conversa (`app/main.py:212` → `app/database.py:118`) e repassado como `reviewer` na aprovação (`app/main.py:250`). O README confirma: usuários "são identificadores ficticios enviados no corpo das requisicoes" (`README.md:47`).
- **Reprodução:** `curl -s -X POST localhost:8000/api/conversations -d '{"user_id":"ana","agent_id":"assistant-demo","message":"oi"}' -H "Content-Type: application/json"` sem credencial → 200 e conversa gravada como de `ana`. `tests/test_observed_behavior.py:60-70` mostra que até `user_id: " "` é aceito.
- **Esperado:** a identidade vem de uma credencial verificada no servidor; requisição sem credencial recebe 401.
- **Atual:** quem envia o corpo escolhe quem é.
- **Impacto:** toda a autorização posterior (dono da conversa, aprovador, time do agente) fica sem base; os achados `HIGH-02` a `MED-03` dependem desta correção para serem efetivos.

**O que fazer**

1. Criar em `app/main.py` (ou em `app/auth.py`) uma dependência `current_user` que valide um token (por exemplo, `HTTPBearer` com JWT assinado e com expiração) e devolva um `Principal(id, teams, roles)`.
2. Remover `user_id` de `ConversationInput` e `ApprovalInput` e usar `user.id` em `run_conversation()` (`app/main.py:212`) e `approve()` (`app/main.py:250`).
3. Aplicar a dependência a todas as rotas de `/api` (por exemplo, `APIRouter(dependencies=[Depends(current_user)])`); manter só `/health` público.

```python
bearer = HTTPBearer()

def current_user(cred: HTTPAuthorizationCredentials = Depends(bearer)) -> Principal:
    principal = verify_token(cred.credentials)  # assinatura + expiração
    if principal is None:
        raise HTTPException(status_code=401, detail="Credencial inválida")
    return principal

@app.post("/api/conversations")
async def run_conversation(body: ConversationInput, user: Principal = Depends(current_user)):
```

**Validação:** requisição sem token ou com token inválido em cada rota `/api` → 401 · com token de `ana`, a conversa gravada tem `user_id == "ana"` mesmo que o corpo tente outro valor; `/health` continua 200 sem token.

### HIGH-02 · Qualquer pessoa sobrescreve a configuração de qualquer agente e troca o time dono

- **Severidade:** HIGH (impacto 3 × probabilidade 3). Altera agentes de outros times, inclusive ferramentas e dono; os IDs são públicos em `GET /api/agents`.
- **Tipo:** Vulnerabilidade
- **Categoria:** `SEC-AUTHZ` / CWE-639, CWE-862 · OWASP A01 · **Confiança:** Confirmado (0,95)
- **Local:** `app/main.py:192-196`, `app/database.py:67-84`

**Evidência**

```python
# app/main.py:192-196
@app.put("/api/agents/{agent_id}")
async def put_agent(agent_id: str, body: AgentInput):
    data = body.model_dump()
    data["id"] = agent_id
    return database.save_agent(data)
```

- **Cenário:** `put_agent()` não lê o agente existente nem compara o time de quem chama com `owner_id`; `save_agent()` faz `INSERT OR REPLACE` (`app/database.py:70`) com o `owner_id` do corpo, então o atacante reescreve `system_prompt`, liga `read_file` (encadeando com `CRIT-01`) e transfere o agente para o próprio time.
- **Reprodução:** `curl -s -X PUT localhost:8000/api/agents/assistant-demo -H "Content-Type: application/json" -d '{"id":"x","owner_id":"another-team","name":"Substituto","system_prompt":"novo","tools":["read_file"]}'` → 200 com `owner_id: "another-team"`. `tests/test_observed_behavior.py:44-57` (`test_agent_replacement_contract`) afirma esse resultado.
- **Esperado:** só membros do time dono atualizam o agente; criar exige pertencer ao `owner_id` informado; atualizar não troca o dono.
- **Atual:** qualquer chamador cria, sobrescreve e se apropria de qualquer agente.
- **Impacto:** o time dono perde o controle do agente, que passa a responder e a usar ferramentas definidas por terceiros para todos os usuários dele.

**O que fazer**, depois de `HIGH-01`

1. Em `put_agent()`, carregar `database.get_agent(agent_id)`; se existir e `existing["owner_id"] not in user.teams`, responder 403.
2. Na criação, exigir `body.owner_id in user.teams`; na atualização, rejeitar (409) `owner_id` diferente do gravado.
3. Em `app/database.py:67-84`, separar `create_agent` (`INSERT`) de `update_agent` (`UPDATE ... WHERE id = ? AND owner_id = ?`), que também resolve `LOW-01`.

**Validação:** teste em que um usuário de `team-b` faz `PUT` em agente de `team-a` → 403 e agente inalterado · membro de `team-a` atualiza nome e ferramentas → 200 com `owner_id` preservado.

### HIGH-03 · Qualquer pessoa aprova ou recusa a ação pendente da conversa de outro usuário

- **Severidade:** HIGH (impacto 3 × probabilidade 2). Execução não autorizada de ferramenta em nome de outro usuário; exige conhecer o ID da conversa.
- **Tipo:** Vulnerabilidade
- **Categoria:** `SEC-LLM` / CWE-862, CWE-639 · OWASP LLM06 / A01 · **Confiança:** Confirmado (0,95)
- **Local:** `app/main.py:241-252`

**Evidência**

```python
# app/main.py:243-251
    item = database.get_conversation(conversation_id)
    ...
    if item["status"] != "pending_approval":
        raise HTTPException(status_code=409, detail="Conversation is not waiting for approval")
    try:
        output = graph.invoke(
            Command(resume={"approved": body.approved, "reviewer": body.user_id}),
```

- **Cenário:** o único controle do HITL é o status; não há comparação entre quem aprova e o dono da conversa ou um papel de revisor do time do agente. Um terceiro com o ID dispara `send_notification` que a dona ainda não decidiu, ou recusa ações legítimas.
- **Reprodução:** `tests/test_observed_behavior.py:16-26` (`test_access_contract_for_saved_runs`): `ana` cria a ação pendente, `bruno` aprova → 200 e `status: "completed"`.
- **Esperado:** só o dono da conversa (ou um revisor autorizado do time do agente, conforme a política) decide; os demais recebem 403/404.
- **Atual:** qualquer chamador decide qualquer ação pendente.
- **Impacto:** a salvaguarda humana deixa de proteger: notificações saem sem a decisão de quem pediu.

**O que fazer**, depois de `HIGH-01`

1. Em `approve()`, depois de carregar `item`, chamar `can_review(user, item)`: `user.id == item["user_id"]` ou `user` tem papel `reviewer` no time do agente (`database.get_agent(item["agent_id"])["owner_id"]`). Caso contrário, 404 para não revelar a existência.
2. Passar `user.id` (não o corpo) como `reviewer` no `Command(resume=...)`, que é a base de `MED-03`.
3. Reescrever `test_access_contract_for_saved_runs` para afirmar a recusa.

**Validação:** `bruno` aprova a conversa de `ana` → 404 e status continua `pending_approval` · `ana` aprova → 200 e `completed`.

### HIGH-04 · Qualquer pessoa lê, continua e toma para si a conversa de outro usuário pelo identificador

- **Severidade:** HIGH (impacto 3 × probabilidade 2). Lê histórico alheio (incluindo saídas de ferramentas) e reescreve o dono; exige conhecer ou escolher o ID, que o cliente pode definir livremente.
- **Tipo:** Vulnerabilidade
- **Categoria:** `SEC-AUTHZ` / CWE-639 · OWASP A01 · **Confiança:** Confirmado (0,9)
- **Local:** `app/main.py:233-238`, `app/main.py:207-209`, `app/main.py:225`, `app/database.py:106-129`

**Evidência**

```python
# app/main.py:207-209 e 233-235
        conversation_id = body.conversation_id or str(uuid.uuid4())
        previous = database.get_conversation(conversation_id)
        messages = previous["messages"] if previous else []
...
async def get_conversation(conversation_id: str):
    item = database.get_conversation(conversation_id)
```

- **Cenário:** `GET /api/conversations/{id}` devolve qualquer conversa sem comparar dono. No `POST /api/conversations`, um `conversation_id` alheio carrega o histórico da vítima, devolve-o na resposta e grava por `INSERT OR REPLACE` (`app/database.py:111`) com o `user_id` do atacante, que vira dono. O `thread_id` do checkpoint é o mesmo ID (`app/main.py:223`), então a execução do grafo também é compartilhada.
- **Reprodução:** `ana` cria uma conversa com `"conversation_id":"conv-1"`; `bruno` faz `POST /api/conversations` com `{"user_id":"bruno","agent_id":"assistant-demo","message":"oi","conversation_id":"conv-1"}` → resposta traz as mensagens de `ana` e `GET /api/conversations/conv-1` passa a mostrar `user_id: "bruno"`. `tests/test_observed_behavior.py:18-24` mostra o `GET` sem nenhuma identidade devolvendo a conversa de `ana`.
- **Esperado:** só o dono lê ou continua a conversa; IDs são gerados pelo servidor.
- **Atual:** qualquer chamador lê, acrescenta mensagens e troca o dono.
- **Impacto:** vazamento de conversas e de conteúdo lido por ferramentas, e perda do histórico para a dona legítima.

**O que fazer**, depois de `HIGH-01`

1. Criar `load_owned_conversation(conversation_id, user)` em `app/main.py` que devolve 404 quando o item não existe ou `item["user_id"] != user.id`; usar em `get_conversation()` e em `run_conversation()` quando `body.conversation_id` vier preenchido.
2. Não aceitar `conversation_id` inexistente vindo do cliente: novas conversas recebem sempre `uuid4()` do servidor.
3. Em `save_conversation()`, preservar `user_id` gravado (usar `UPDATE ... WHERE id = ? AND user_id = ?` na continuação).

```python
def load_owned_conversation(conversation_id: str, user: Principal) -> dict:
    item = database.get_conversation(conversation_id)
    if not item or item["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return item
```

**Validação:** `bruno` faz `GET` e `POST` com o ID de `ana` → 404 e conversa inalterada · `ana` continua a própria conversa e o histórico cresce normalmente.

### MED-01 · Erros internos são devolvidos ao cliente com caminhos e mensagens do servidor

- **Severidade:** MEDIUM (impacto 2 × probabilidade 3). Vazamento de detalhes internos em qualquer falha, provocável por qualquer chamador.
- **Tipo:** Vulnerabilidade
- **Categoria:** `SEC-DATA` / CWE-209 · OWASP A04 · **Confiança:** Confirmado (0,95)
- **Local:** `app/main.py:229-230`, `app/main.py:256-257`

**Evidência**

```python
# app/main.py:229-230 (igual em 256-257)
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
```

- **Cenário:** `read <caminho inexistente>` devolve `[Errno 2] No such file or directory: '<caminho>'`; a diferença entre `FileNotFoundError`, `PermissionError` e `IsADirectoryError` serve de oráculo da estrutura de arquivos, e erros do SQLite/LangGraph expõem detalhes internos.
- **Reprodução:** `tests/test_observed_behavior.py:105-116` (`test_error_response_contract`) afirma status 500 com o caminho no `detail`.
- **Esperado:** mensagem genérica com ID de correlação e 4xx para erro de entrada
- **Atual:** 500 com `str(error)` para tudo.
- **Impacto:** facilita reconhecimento do servidor e classifica erro do cliente como falha do servidor.

**O que fazer**

1. Trocar os dois `except Exception` por `logger.exception(...)` e `HTTPException(500, detail={"error": "internal_error", "id": <uuid>})`.
2. Criar exceções de domínio (`ToolDenied`, `ToolInputError`) lançadas pelas ferramentas e mapeá-las para 400/403 com mensagem controlada.
3. Reescrever `test_error_response_contract` para afirmar que o caminho não aparece.

**Validação:** `read <arquivo ausente>` → 4xx sem o caminho no corpo, com o detalhe registrado no log do servidor · fluxos normais seguem 200.

### MED-02 · Agentes de um time são listados e usados por pessoas de outros times

- **Severidade:** MEDIUM (impacto 2 × probabilidade 3). Expõe `system_prompt` e ferramentas de todos os times e permite executar agentes alheios; o dano é moderado porque as ferramentas não carregam dados próprios do time.
- **Tipo:** Vulnerabilidade
- **Categoria:** `SEC-AUTHZ` / CWE-862, CWE-200 · OWASP A01 · **Confiança:** Confirmado (0,9)
- **Local:** `app/main.py:187-189`, `app/main.py:203-206`, `app/database.py:96-103`

**Evidência**

```python
# app/main.py:187-189 e 203
async def agents():
    return database.list_agents()
...
        agent = database.get_agent(body.agent_id)
```

- **Cenário:** `list_agents()` faz `SELECT * FROM agents` sem filtro (`app/database.py:97`); `run_conversation()` só verifica se o agente existe, sem comparar `owner_id` com o time de quem chama.
- **Reprodução:** `curl -s localhost:8000/api/agents` → todos os agentes, com `owner_id` e `system_prompt`; `POST /api/conversations` com `agent_id` de outro time → 200.
- **Esperado:** listagem e execução restritas aos times do usuário
- **Atual:** tudo visível e executável por todos.
- **Impacto:** configuração de outros times exposta e agentes consumidos por quem não pertence ao time.

**O que fazer**, depois de `HIGH-01`

1. Mudar `list_agents()` para `list_agents(team_ids)` com `WHERE owner_id IN (...)` e passar `user.teams` em `agents()`.
2. Em `run_conversation()`, responder 404 quando `agent["owner_id"] not in user.teams`.

**Validação:** usuário de `team-b` lista e não vê agentes de `team-a`; ao usá-los recebe 404 · membro de `team-demo` usa `assistant-demo` normalmente.

### MED-03 · A aprovação não registra quem aprovou nem quando

- **Severidade:** MEDIUM (impacto 2 × probabilidade 2). Sem trilha de auditoria, uma aprovação indevida (como em `HIGH-03`) não pode ser atribuída; afeta toda decisão de HITL.
- **Tipo:** Vulnerabilidade
- **Categoria:** `INT-WF` / CWE-778 · OWASP A09 · **Confiança:** Confirmado (0,9)
- **Local:** `app/main.py:250`, `app/main.py:134-143`, `app/database.py:29-39`

**Evidência**

```python
# app/main.py:134-137
    if decision.get("approved"):
        action = state["pending_action"]
        output = TOOLBOX[action["tool"]](action["recipient"], action["text"])
        messages.append({"role": "tool", "content": output})
```

- **Cenário:** o `reviewer` vai no `Command(resume=...)` (`app/main.py:250`), mas `wait_for_approval()` nunca o lê; a tabela `conversations` não tem coluna de revisor nem de data da decisão, e `save_conversation()` sobrescreve a linha (`app/database.py:111`).
- **Reprodução:** aprovar pelo fluxo de `tests/test_flows.py:36-58` e consultar a conversa → nenhum campo indica quem aprovou.
- **Esperado:** cada decisão grava revisor, decisão, ação e horário de forma imutável
- **Atual:** só resta `status` e a mensagem "Acao recusada."/saída da ferramenta.
- **Impacto:** impossível investigar ou contestar uma execução de ferramenta.

**O que fazer**, depois de `HIGH-01` e `HIGH-03`

1. Criar tabela `approvals(id, conversation_id, reviewer_id, approved, action_json, decided_at)` em `initialize_database()` com inserção somente (sem `REPLACE`).
2. Em `wait_for_approval()`, incluir `decision["reviewer"]` na mensagem `tool` e devolver um campo `decision`; em `approve()`, inserir a linha em `approvals` com `user.id` autenticado.

**Validação:** após aprovar ou recusar, existe exatamente uma linha em `approvals` com o revisor autenticado · aprovação repetida continua 409 e não cria segunda linha.

### MED-04 · Continuar uma conversa com outro agente troca o agente gravado e leva o histórico junto

- **Severidade:** MEDIUM (impacto 2 × probabilidade 2). Corrompe o registro da conversa e entrega o histórico a outro agente; ocorre quando o cliente envia um `agent_id` diferente na continuação.
- **Tipo:** Bug
- **Categoria:** `INT-VAL` / CWE-20 · **Confiança:** Confirmado (0,9)
- **Local:** `app/main.py:203-215`, `app/main.py:225`

**Evidência**

```python
# app/main.py:208-213
        previous = database.get_conversation(conversation_id)
        messages = previous["messages"] if previous else []
        state = {
            "conversation_id": conversation_id,
            "user_id": body.user_id,
            "agent_id": body.agent_id,
```

- **Cenário:** a continuação ignora `previous["agent_id"]` e usa o `agent_id` do corpo; `save_conversation()` grava o novo agente sobre o antigo, e o histórico (que pode conter conteúdo lido por ferramentas) passa a pertencer a outro agente, possivelmente de outro time.
- **Reprodução:** criar conversa com `assistant-demo`, depois `POST` com o mesmo `conversation_id` e `agent_id: "policy-agent"` → 200 e `GET` mostra `agent_id: "policy-agent"` com as mensagens anteriores.
- **Esperado:** uma conversa fica presa ao agente que a iniciou
- **Atual:** o agente muda silenciosamente.
- **Impacto:** histórico misturado entre agentes e configuração aplicada à conversa errada.

**O que fazer**

1. Em `run_conversation()`, quando `previous` existir e `previous["agent_id"] != body.agent_id`, responder 409.
2. Tornar `agent_id` opcional em `ConversationInput` para continuação e usar `previous["agent_id"]` quando ausente.

**Validação:** continuação com outro `agent_id` → 409 e conversa inalterada · continuação sem `agent_id` ou com o mesmo segue 200 (`tests/test_flows.py:8-33`).

### MED-05 · O agente da execução vem de uma variável global compartilhada, e não da conversa

- **Severidade:** MEDIUM (impacto 3 × probabilidade 1). Se ocorrer, a conversa de um usuário roda com o agente e as ferramentas de outro time; hoje só não acontece porque os handlers `async` sem `await` serializam as requisições.
- **Tipo:** Dívida técnica
- **Categoria:** `ISO` / CWE-488, CWE-362 · **Confiança:** Confirmado (0,9)
- **Local:** `app/main.py:69`, `app/main.py:99-101`, `app/main.py:201`, `app/main.py:206`

**Evidência**

```python
# app/main.py:99-101 e 206
def plan_message(state):
    agent = ACTIVE_AGENT
    decision = fake_model(state["message"], agent)
...
        ACTIVE_AGENT = agent
```

- **Cenário:** `plan_message()` ignora `state["agent_id"]` e usa o último agente gravado no global do processo. Basta trocar o handler para `def` (thread pool), usar `graph.ainvoke` ou introduzir um `await` entre `app/main.py:206` e `app/main.py:221` para que duas requisições concorrentes troquem de agente.
- **Reprodução:** `tests/test_observed_behavior.py:73-102` (`test_process_context_contract`): estado com `agent_id: "agent-a"` e global apontando para `agent-b` → resposta `[Agente B]`.
- **Esperado:** o nó do grafo usa o agente da própria conversa
- **Atual:** usa o estado global do processo.
- **Impacto:** risco latente de execução com permissões de ferramenta erradas, e o nó não pode ser testado isoladamente.

**O que fazer**

1. Remover `ACTIVE_AGENT` (`app/main.py:69`, `201`, `206`) e, em `plan_message()`, carregar `database.get_agent(state["agent_id"])`, falhando se não existir.
2. Reescrever `test_process_context_contract` para afirmar que o agente do estado é usado.

**Validação:** o teste acima passa a conter `[Agente A]` · fluxos de `tests/test_flows.py` seguem iguais.

### MED-06 · Ferramentas executam por caminhos diferentes, sem um ponto único que aplique permissão e aprovação

- **Severidade:** MEDIUM (impacto 3 × probabilidade 1). A falta de ponto único é o que deixou `read_file` fora do HITL (`CRIT-01`) e deixa a aprovação executar ferramenta já removida do agente.
- **Tipo:** Dívida técnica
- **Categoria:** `ARQ` / CWE-1061 · OWASP LLM06 · **Confiança:** Confirmado (0,9)
- **Local:** `app/main.py:64-68`, `app/main.py:72-96`, `app/main.py:134-136`

**Evidência**

```python
# app/main.py:77, 80 e 136
        return {"result": lookup_policy(topic), "pending_action": None}
        return {"result": read_file(path), "pending_action": None}
        output = TOOLBOX[action["tool"]](action["recipient"], action["text"])
```

- **Cenário:** `fake_model()` chama `lookup_policy` e `read_file` diretamente, enquanto só `send_notification` passa por `TOOLBOX` no nó de aprovação, com assinatura fixa `(recipient, text)`. A permissão (`"x" in agent["tools"]`) é checada só no planejamento; se o dono remover `send_notification` do agente enquanto há ação pendente, a aprovação ainda executa.
- **Reprodução:** criar ação pendente, fazer `PUT /api/agents/assistant-demo` com `tools: ["lookup_policy"]` e aprovar → 200 com "Notificacao enviada".
- **Esperado:** toda execução passa por um executor que confere permissão atual, argumentos e necessidade de aprovação
- **Atual:** cada ferramenta tem um caminho próprio.
- **Impacto:** cada ferramenta nova repete o problema de `CRIT-01`; qualquer segunda ferramenta com aprovação quebra em `app/main.py:136`.

**O que fazer**

1. Trocar `TOOLBOX` por um registro `ToolSpec(func, args_model, requires_approval)` e fazer `fake_model()` devolver apenas `{"tool": nome, "args": {...}}`.
2. Criar `execute_tool(agent_id, name, args)` que recarrega o agente, confere `name in agent["tools"]`, valida `args` e chama `func(**args)`; usar no nó `plan` (sem aprovação) e em `wait_for_approval()`.
3. Fazer `route_after_plan()` enviar ao nó `approval` toda ferramenta com `requires_approval=True` (incluindo `read_file`).

**Validação:** teste em que a ferramenta é removida do agente antes da aprovação → recusa · `policy travel` continua sem aprovação e `send ...` continua pedindo aprovação.

### LOW-01 · Atualizar um agente apaga a data de criação e muda a ordem do catálogo

- **Severidade:** LOW (impacto 1 × probabilidade 3). Toda atualização perde o `created_at` original e reordena a listagem.
- **Tipo / Categoria:** Bug · `CONC` / sem CWE específico · **Confiança:** Confirmado (0,9)
- **Local:** `app/database.py:70-80`, `app/database.py:97`
- **Evidência:** `INSERT OR REPLACE INTO agents (..., created_at) VALUES (..., now())` e a listagem usa `ORDER BY created_at`.
- **Esperado / Atual / Impacto:** `created_at` imutável e `updated_at` separado · data de criação reescrita a cada `PUT` · catálogo muda de ordem e `tests/test_flows.py:4` (que espera `assistant-demo` primeiro) quebra se o agente semeado for editado.
- **O que fazer:** em `save_agent()`, usar `INSERT ... ON CONFLICT(id) DO UPDATE SET name=excluded.name, system_prompt=excluded.system_prompt, tools_json=excluded.tools_json` sem tocar em `created_at`, e adicionar coluna `updated_at`.
- **Validação:** atualizar `assistant-demo` e conferir `created_at` igual ao anterior e ordem da lista preservada.

### LOW-02 · O identificador do agente enviado no corpo é ignorado sem aviso

- **Severidade:** LOW (impacto 1 × probabilidade 2). Um cliente que envia `id` diferente da URL acha que criou um agente novo e sobrescreve outro.
- **Tipo / Categoria:** Bug · `INT-VAL` / CWE-20 · **Confiança:** Confirmado (0,9)
- **Local:** `app/main.py:29`, `app/main.py:195`
- **Evidência:** `data["id"] = agent_id` substitui o `id` obrigatório do corpo; `tests/test_observed_behavior.py:48` envia `"id": "ignored"` e o agente `assistant-demo` é que muda.
- **Esperado / Atual / Impacto:** divergência entre corpo e URL rejeitada · descartada em silêncio · sobrescrita acidental de agente.
- **O que fazer:** remover `id` de `AgentInput` (a URL é a fonte), ou responder 422 em `put_agent()` quando `body.id != agent_id`.
- **Validação:** `PUT /api/agents/a` com `"id":"b"` → 422; com corpo sem `id` → 200.

### LOW-03 · O conteúdo de toda mensagem de usuário é impresso na saída do servidor

- **Severidade:** LOW (impacto 2 × probabilidade 1). Mensagens com dados pessoais ou tokens vão para os logs; exige acesso aos logs.
- **Tipo / Categoria:** Vulnerabilidade · `SEC-DATA` / CWE-532 · **Confiança:** Confirmado (0,95)
- **Local:** `app/main.py:220`
- **Evidência:** `print("agent-run", body.user_id, body.message)`; `tests/test_observed_behavior.py:119-128` afirma que o conteúdo aparece no stdout.
- **Esperado / Atual / Impacto:** log estruturado só com metadados · texto integral em `print` · PII e segredos retidos em logs, contra a própria política de `app/main.py:51`.
- **O que fazer:** trocar por `logger.info("agent-run", extra={"conversation_id": ..., "agent_id": ..., "message_len": len(body.message)})` e reescrever o teste para afirmar a ausência do conteúdo.
- **Validação:** `capsys` não contém o texto da mensagem; contém o `conversation_id`.

### LOW-04 · O contêiner de produção roda como root

- **Severidade:** LOW (impacto 2 × probabilidade 1). Defesa em profundidade; como root, `CRIT-01` lê qualquer arquivo do contêiner.
- **Tipo / Categoria:** Vulnerabilidade · `SEC-CONF` / CWE-250 · **Confiança:** Confirmado (0,95)
- **Local:** `Dockerfile:13-17`
- **Evidência:** o estágio `runtime` não tem instrução `USER`; `uvicorn` herda o usuário root da imagem base.
- **Esperado / Atual / Impacto:** processo sem privilégio dono só de `/app/data` · root · amplia o alcance de qualquer leitura ou escrita indevida.
- **O que fazer:** no estágio `runtime`, `RUN useradd --system --uid 10001 app && chown -R app /app/data` seguido de `USER app`.
- **Validação:** `docker run ... id -u` → `10001`; a API sobe e grava em `/app/data`.

### LOW-05 · Bancos usam caminho relativo ao diretório de onde o servidor é iniciado

- **Severidade:** LOW (impacto 2 × probabilidade 1). Iniciar o servidor de outra pasta cria bancos vazios e os dados parecem perdidos.
- **Tipo / Categoria:** Dívida técnica · `ARQ` / CWE-1120 · **Confiança:** Confirmado (0,9)
- **Local:** `app/database.py:8`, `app/main.py:153`
- **Evidência:** `Path(os.getenv("AGENT_DB_PATH", "data/agents.db"))` e `Path(os.getenv("AGENT_CHECKPOINT_PATH", "data/checkpoints.db"))` resolvem contra o CWD.
- **Esperado / Atual / Impacto:** caminho padrão fixo em relação ao projeto · depende de onde `uvicorn` é executado · dados divididos entre pastas e conversas pendentes "somem" (checkpoint em outro arquivo).
- **O que fazer:** centralizar em um `settings.py` com padrão `Path(__file__).resolve().parent.parent / "data"` e validar na inicialização que o diretório existe e é gravável.
- **Validação:** iniciar a partir da raiz do repositório e da pasta do projeto e conferir que ambos usam o mesmo arquivo.

### LOW-06 · Conexões SQLite globais são abertas na importação e compartilhadas entre threads sem trava

- **Severidade:** LOW (impacto 2 × probabilidade 1). Hoje as requisições são serializadas; com handlers `def` ou mais threads, transações de requisições diferentes se misturam (um `commit` grava a escrita parcial de outra).
- **Tipo / Categoria:** Dívida técnica · `CONC` / CWE-362 · **Confiança:** Provável (0,8)
- **Local:** `app/database.py:9-11`, `app/database.py:145`, `app/main.py:154-156`
- **Evidência:** `sqlite3.connect(DB_PATH, check_same_thread=False)` em nível de módulo e `initialize_database()` na importação; `tests/conftest.py:5-7` precisa definir variáveis de ambiente antes do `import` para isolar os testes.
- **Esperado / Atual / Impacto:** conexão criada no startup e obtida por requisição · uma conexão por processo, criada no `import` · concorrência futura corrompe transações e testes não conseguem injetar outro banco.
- **O que fazer:** abrir as conexões e o `SqliteSaver` no `lifespan` do FastAPI e expor `get_db()` como dependência (uma conexão por requisição), removendo `initialize_database()` do nível de módulo.
- **Validação:** teste que sobe o app com banco temporário injetado sem mexer em `os.environ`; requisições concorrentes não perdem gravações.

## Observações (INFO, hipóteses e descartados)

- **Hipótese:** aprovações simultâneas da mesma conversa em mais de um worker podem executar a ferramenta duas vezes, porque a checagem de status (`app/main.py:246`) não é atômica com a retomada do checkpoint (`app/main.py:249`); falta confirmar o comportamento do LangGraph em retomadas concorrentes.
- **Hipótese:** enviar nova mensagem para uma conversa em `pending_approval` (`app/main.py:207-224`) provavelmente descarta a ação pendente sem registro de recusa; depende da semântica do LangGraph para nova entrada sobre thread interrompida, não executada.
- **Hipótese:** histórico e status vivem em duas fontes (`conversations.messages_json` e checkpoint) sem transação comum; uma falha entre `app/main.py:249` e `app/main.py:254` deixa o banco em `pending_approval` com o checkpoint concluído. Falta reproduzir a falha.
- **Hipótese:** continuações simultâneas da mesma conversa em workers diferentes perdem mensagens (leitura em `app/main.py:208`, escrita em `app/main.py:225`); com um worker as requisições são serializadas.
- **INFO:** `system_prompt` é gravado e listado, mas o modelo simulado nunca o usa (`app/main.py:72-96`).
- **INFO:** a string em `app/database.py:147` está no fim do módulo e não funciona como docstring (código morto, sem caminho para bug).
- **INFO:** `tests/test_observed_behavior.py` fixa como contrato os comportamentos de `CRIT-01`, `HIGH-02`, `HIGH-03`, `MED-01`, `MED-05` e `LOW-03`; deve ser reescrito junto com as correções para não virar risco de regressão.
- **INFO:** não há testes negativos de autorização nem de recusa de ferramenta; os fluxos críticos só têm o caminho feliz (`tests/test_flows.py`).
- **INFO:** `reset_database()` (`app/database.py:60-64`) apaga tudo e está no módulo de produção; hoje só os testes o chamam, sem rota exposta.
- **INFO:** a imagem não declara `VOLUME` e o README usa `docker run --rm` (`README.md:35`), então os dados somem a cada execução do contêiner.
- **INFO:** dependências diretas estão fixadas com `==` (`requirements.txt:1-5`), mas não há lockfile para as transitivas.
- **INFO:** `status` é texto livre sem `CHECK` e `conversations.agent_id` não tem chave estrangeira (`app/database.py:29-39`); sem bug observado hoje.
- **INFO:** `app/main.py` concentra ferramentas, modelo, grafo e rotas; as consequências concretas estão em `MED-05` e `MED-06`.
- **INFO:** consultas SQL são parametrizadas e datas usam UTC (`app/database.py:14-15`), boas práticas observadas.
- **Descartado:** campos sem limite de tamanho (`message` de 200 mil caracteres, `tests/test_observed_behavior.py:60-70`) (exclusão fixa: DoS/esgotamento de recursos; o `user_id` em branco é consequência de `HIGH-01`).
- **Descartado:** handlers `async` com I/O bloqueante (`graph.invoke`, SQLite, `read_text` de arquivos grandes) travam o event loop (exclusão fixa: DoS).
- **Descartado:** injeção de SQL (mitigação: todas as consultas em `app/database.py` usam parâmetros `?`).
- **Descartado:** destinatário livre em `send_notification` (mitigação: passa por aprovação humana e a função só devolve texto, `app/main.py:56-57`).
- **Descartado:** nomes de ferramenta desconhecidos aceitos em `AgentInput.tools` (validação sem efeito: `fake_model()` ignora nomes fora dos três prefixos).
- **Descartado:** prompt injection indireta por saída de ferramenta no histórico (inalcançável: o modelo simulado não lê o histórico; confiança < 0,7).
- **Descartado:** divergência entre a ação exibida (banco) e a executada (checkpoint) na aprovação (confiança < 0,7: ambas vêm da mesma saída de `plan_message()` e não há caminho que altere uma sem a outra).
- **Descartado:** `uvicorn --reload` no README (`README.md:26`) (sem defeito no artefato implantado: o `Dockerfile:17` não usa `--reload`).
- **Descartado:** CORS, headers de segurança e XSS (boa prática genérica sem defeito concreto: API só JSON, sem frontend e sem `CORSMiddleware`).
- **Descartado:** `policy` com espaço duplo não encontra a política (validação sem impacto de segurança ou de regra de negócio).
