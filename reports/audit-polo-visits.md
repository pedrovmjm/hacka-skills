# Auditoria — polo-visits (Meu Polo, controle de presença)

**Commit:** `f2ab54a` · **Auditor:** claude-opus-5-5

## Resumo

A aplicação não tem autenticação nem autorização: o servidor exige o cabeçalho `X-User`, mas nunca o lê, e confia no `user_id`/`manager_id` que o próprio cliente envia. Por isso, qualquer pessoa na rede lê, cria, altera e apaga presenças de qualquer colaborador e abre a visão de qualquer time. Isso bloqueia o release. A segunda causa dominante é confiar na entrada: as observações são renderizadas como HTML (XSS armazenado na visão do gestor) e as datas não são validadas, o que permite inflar a meta. Há também bugs reais no frontend (corrida entre respostas, URL da API fixa em `localhost`) e no boot do banco (seed que derruba a API).

| Tipo | CRITICAL | HIGH | MEDIUM | LOW | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Vulnerabilidade | 1 | 4 | 3 | 2 | 10 |
| Bug | 0 | 0 | 3 | 2 | 5 |
| Dívida técnica | 0 | 0 | 0 | 5 | 5 |
| **Total** | **1** | **4** | **6** | **9** | **20** |

**Matriz de risco (impacto × probabilidade)**

| Impacto \ Prob. | Alta | Média | Baixa |
| --- | --- | --- | --- |
| Severo | CRIT-01 | | |
| Alto | HIGH-01, HIGH-02, HIGH-03, HIGH-04 | | |
| Moderado | MED-01, MED-02 | MED-03, MED-04, MED-05, MED-06 | LOW-01, LOW-02, LOW-03, LOW-04 |
| Baixo | LOW-06 | LOW-05, LOW-07, LOW-08, LOW-09 | |

**Baseline:** `python -m pytest -q` / `npm test` → não executado: não há Python, Node nem daemon Docker nesta máquina; os testes existentes (10 de backend, 5 Vitest e 2 Playwright) foram usados como evidência estática.

**Superfície:** FastAPI 0.116 + SQLite (`sqlite3`) / React + Vite servido por nginx 1.27 · entradas: `GET/PUT/DELETE /api/attendance`, `GET /api/team-attendance`, `/health`, `/docs`; telas "Minha presença" e "Visão do time" · persistência: `data/polo.db` (volume `polo-data`), tabelas `attendance` e `team_members` · identidade: cabeçalho `X-User` e `user_id`/`manager_id` enviados pelo cliente, escolhidos em um seletor de perfil da UI.

## Achados

### CRIT-01 · A API não autentica ninguém: qualquer pessoa se passa por qualquer perfil

- **Severidade:** CRITICAL (impacto 4 × probabilidade 3). Sem nenhuma credencial, um cliente anônimo na rede lê e altera toda a base de presenças de todos os usuários, o que equivale a bypass total de autenticação.
- **Tipo:** Vulnerabilidade
- **Categoria:** `SEC-AUTHN` / CWE-306, CWE-290 · **Confiança:** Confirmado (0,95)
- **Local:** `backend/app/adapters/http/api.py:24`, `api.py:32`, `api.py:45`, `api.py:53`; `frontend/src/App.jsx:5`, `App.jsx:115`, `App.jsx:141`

**Evidência**

```python
# backend/app/adapters/http/api.py:21-26 (o mesmo padrão em :29-33, :43-46, :51-55)
async def attendance(
    user_id: str = Query(...),
    month: str = Query(...),
    x_user: str = Header(..., alias="X-User"),   # obrigatório, mas nunca usado
):
    return service.get_month(user_id, month)
```

- **Cenário:** qualquer pessoa que alcance a porta 8001 envia `X-User` com qualquer valor e opera como qualquer perfil. Na UI, a "troca de perfil" é um `<select>` com usuários fixos no código (`App.jsx:5`, `:141`), e o estado `user` (`App.jsx:115`) vira o cabeçalho enviado (`App.jsx:124`).
- **Reprodução:** `curl -H "X-User: qualquer" "http://localhost:8001/api/attendance?user_id=ana&month=2026-10"` → 200 com o calendário de Ana. `test_flows.py:136-143` só verifica que o cabeçalho existe (422 sem ele), e isso dá uma falsa sensação de controle.
- **Esperado:** a identidade do chamador vem de uma credencial verificada no servidor (sessão ou token assinado).
- **Atual:** a identidade é um texto livre escolhido pelo cliente e nem esse texto é usado.
- **Impacto:** confidencialidade e integridade de todas as presenças e observações de todos os colaboradores. Também habilita, sem conta, os demais achados (HIGH-01 a HIGH-04, MED-03).

**O que fazer**

1. Criar `backend/app/adapters/http/auth.py` com uma dependência `get_current_user` que valide uma credencial real (por exemplo, um JWT do IdP corporativo verificado com a chave pública ou uma sessão assinada) e devolva `user_id` e papel (`role`).
2. Em `create_router` (`api.py:13`), trocar todos os parâmetros `x_user: str = Header(...)` por `caller: User = Depends(get_current_user)` e responder 401 quando a credencial faltar ou for inválida.
3. No frontend, remover `USERS` e o seletor de perfil (`App.jsx:5`, `:141`), obter a identidade de um endpoint `/api/me` e enviar `Authorization: Bearer <token>` em `request()` (`App.jsx:27-35`) no lugar de `X-User`.

```python
def get_current_user(authorization: str = Header(...)) -> User:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(401, "Credencial ausente")
    try:
        claims = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"], audience="polo-api")
    except jwt.PyJWTError:
        raise HTTPException(401, "Credencial inválida")
    return User(id=claims["sub"], role=claims.get("role", "colaborador"))
```

**Validação:** teste novo: requisição sem `Authorization` ou com token forjado → 401 em todas as rotas `/api/*` · fluxo legítimo: token válido de `ana` continua retornando o próprio calendário.

### HIGH-01 · Qualquer usuário cria, altera e apaga presenças de outro colaborador

- **Severidade:** HIGH (impacto 3 × probabilidade 3). Adultera registros de outros usuários trocando um campo da requisição, sem pré-condição além de conhecer o identificador, que a própria visão do time devolve.
- **Tipo:** Vulnerabilidade
- **Categoria:** `SEC-AUTHZ` / CWE-639, CWE-862 · **Confiança:** Confirmado (0,95)
- **Local:** `backend/app/adapters/http/api.py:8-10`, `api.py:34-40`, `api.py:45-48`; `frontend/src/App.jsx:131`, `App.jsx:136`

**Evidência**

```python
# backend/app/adapters/http/api.py:34-40
return service.mark_day(
    AttendanceUpsertCommand(
        user_id=body.user_id,          # dono do registro vem do corpo
        attendance_date=attendance_date,
        notes=body.notes,
    )
)
```

- **Cenário:** um colaborador (ou um anônimo, por causa de CRIT-01) envia `PUT` com `{"user_id":"bruno"}` para marcar presença falsa para Bruno, ou `DELETE ...?user_id=bruno` para apagar as presenças dele e derrubar a meta. Os ids aparecem em `GET /api/team-attendance` (`members[].user_id`).
- **Reprodução:** `backend/tests/test_observed_behavior.py:4-26`: com `X-User: ana`, o `PUT` com `user_id=bruno` e o `DELETE ?user_id=bruno` retornam 200 e alteram os dados de Bruno.
- **Esperado:** escrita e remoção só no próprio registro do chamador autenticado.
- **Atual:** o dono do registro é o `user_id` do corpo ou da query.
- **Impacto:** a meta mensal de qualquer colaborador pode ser falsificada ou zerada, e o gestor passa a avaliar dados adulterados.

**O que fazer**, depois de `CRIT-01`

1. Remover `user_id` de `AttendanceUpsert` (`api.py:8-10`) e o parâmetro `user_id` do `DELETE` (`api.py:45`).
2. Nos handlers `mark_attendance` e `unmark_attendance`, usar `caller.id` como dono: `AttendanceUpsertCommand(user_id=caller.id, ...)` e `service.unmark_day(caller.id, attendance_date)`.
3. No frontend, parar de enviar `user_id` no corpo e na query (`App.jsx:131`, `:136`).

```python
@router.put("/api/attendance/{attendance_date}")
async def mark_attendance(attendance_date: str, body: AttendanceUpsert,
                          caller: User = Depends(get_current_user)):
    return service.mark_day(AttendanceUpsertCommand(
        user_id=caller.id, attendance_date=attendance_date, notes=body.notes))
```

**Validação:** inverter `test_header_identity_does_not_control_requested_user`: o `PUT`/`DELETE` de Ana não muda nenhuma linha de Bruno · Ana continua marcando e removendo as próprias presenças (`test_marks_updates_and_removes_a_day`).

### HIGH-02 · Observação de presença executa script no navegador do gestor (XSS armazenado)

- **Severidade:** HIGH (impacto 3 × probabilidade 3). Um colaborador grava HTML em uma observação e o código roda no navegador de quem a abrir, inclusive o gestor na visão do time, sem nenhuma interação além de abrir o detalhe.
- **Tipo:** Vulnerabilidade
- **Categoria:** `SEC-XSS` / CWE-79 · **Confiança:** Confirmado (0,95)
- **Local:** `frontend/src/App.jsx:110` (notas do time), `frontend/src/App.jsx:80` (pré-visualização da própria nota)

**Evidência**

```jsx
// frontend/src/App.jsx:110 (trecho)
{active.days.filter((day) => day.notes).map((day) => <article key={day.attendance_date}>
  <time>...</time><div dangerouslySetInnerHTML={{ __html: day.notes }}/></article>)}
// frontend/src/App.jsx:80 (trecho)
<span dangerouslySetInnerHTML={{ __html: item.notes }}/>
```

- **Cenário:** Bruno confirma presença com a observação `<img src=x onerror="...">`. Quando Ana abre "Visão do time" → "Bruno", o script roda na origem do app. Com HIGH-01, um atacante também injeta a nota no registro de outra pessoa, para que dispare na pré-visualização da própria vítima.
- **Reprodução:** `frontend/src/App.test.jsx:41-50` confirma que `<img ... onerror="alert(1)">` vira elemento DOM real; `backend/tests/test_observed_behavior.py:47-60` confirma que o backend grava o payload sem alteração.
- **Esperado:** observação exibida como texto.
- **Atual:** observação interpretada como HTML.
- **Impacto:** execução de JavaScript no navegador do gestor: ações em nome dele, phishing dentro do app e, quando houver sessão (CRIT-01), roubo do token.

**O que fazer**

1. Em `App.jsx:110`, trocar `<div dangerouslySetInnerHTML={{ __html: day.notes }}/>` por `<div className="note-text">{day.notes}</div>`. O React escapa o texto.
2. Em `App.jsx:80`, trocar o `<span dangerouslySetInnerHTML=...>` por `<span>{item.notes}</span>`. Para preservar quebras de linha, usar `white-space: pre-wrap` no CSS, nunca HTML.
3. Adicionar à revisão uma regra de lint (`react/no-danger`) para impedir a reintrodução.

**Validação:** reescrever `App.test.jsx:41-50` para afirmar que `container.querySelector('.notes-preview img')` é `null` e que o texto literal `<img` aparece na tela; teste igual para o detalhe do time · notas comuns ("Reunião no polo") continuam visíveis.

### HIGH-03 · Qualquer pessoa lê o calendário e as observações de qualquer colaborador

- **Severidade:** HIGH (impacto 3 × probabilidade 3). Basta trocar `user_id` na query para ler os dados de outro usuário, e os ids são listados pela visão do time.
- **Tipo:** Vulnerabilidade
- **Categoria:** `SEC-AUTHZ` / CWE-639 · **Confiança:** Confirmado (0,95)
- **Local:** `backend/app/adapters/http/api.py:20-26`; `frontend/src/App.jsx:124`

**Evidência**

```python
# backend/app/adapters/http/api.py:20-26
@router.get("/api/attendance")
async def attendance(
    user_id: str = Query(...),
    ...
    return service.get_month(user_id, month)
```

- **Cenário:** Bruno chama `GET /api/attendance?user_id=carla&month=2026-10` e recebe as datas e as observações livres de Carla, que podem conter dados pessoais (consulta médica, motivo de ausência).
- **Reprodução:** `backend/tests/test_observed_behavior.py:6-10` e `:22-23`: com `X-User: ana`, a consulta com `user_id=bruno` devolve 200 com os dados de Bruno.
- **Esperado:** o colaborador lê apenas o próprio mês. O gestor lê os liderados diretos (regra de leitura diferente da de escrita de HIGH-01).
- **Atual:** qualquer `user_id` é aceito.
- **Impacto:** exposição das rotinas presenciais e das observações de qualquer colaborador para qualquer colega.

**O que fazer**, depois de `CRIT-01`

1. Em `attendance()` (`api.py:20-26`), tornar `user_id` opcional, com padrão `caller.id`.
2. Se `user_id != caller.id`, autorizar apenas quando `caller.role == "gestor"` e o alvo estiver em `team_members` com `manager_id = caller.id`. Para isso, adicionar `is_manager_of(manager_id, user_id)` à porta `AttendanceRepository` (`domain/ports.py:10-17`) e à implementação SQLite. Caso contrário, responder 403.

```python
target = user_id or caller.id
if target != caller.id and not service.is_manager_of(caller.id, target):
    raise HTTPException(403, "Sem acesso ao calendário solicitado")
return service.get_month(target, month)
```

**Validação:** teste novo: Bruno consultando `user_id=carla` → 403; Ana (gestora de Bruno) consultando `user_id=bruno` → 200 · colaborador sem `user_id` recebe o próprio mês.

### HIGH-04 · Qualquer pessoa abre a visão de time de qualquer gestor

- **Severidade:** HIGH (impacto 3 × probabilidade 3). O consolidado e os dias de toda a equipe saem para quem informar `manager_id`, sem verificar papel nem vínculo.
- **Tipo:** Vulnerabilidade
- **Categoria:** `SEC-AUTHZ` / CWE-863, CWE-639 · **Confiança:** Confirmado (0,95)
- **Local:** `backend/app/adapters/http/api.py:50-56`; `frontend/src/App.jsx:124`, `App.jsx:144`

**Evidência**

```python
# backend/app/adapters/http/api.py:50-56
@router.get("/api/team-attendance")
async def team_attendance(
    manager_id: str = Query(...),
    month: str = Query(...),
    x_user: str = Header(..., alias="X-User"),
):
    return service.get_team_month(manager_id, month)
```

- **Cenário:** um colaborador (ou o `X-User: outsider`) consulta `manager_id=ana` e recebe nome, contagem, dias e observações de toda a equipe de Ana. A UI mostra a aba "Visão do time" para qualquer perfil (`App.jsx:144`).
- **Reprodução:** `backend/tests/test_observed_behavior.py:29-44`: `X-User: outsider` recebe 200 com `team_size == 3` e os três integrantes.
- **Esperado:** apenas o próprio gestor vê a própria equipe.
- **Atual:** qualquer `manager_id` é aceito de qualquer chamador.
- **Impacto:** exposição em massa dos dados de presença e das observações de equipes inteiras, além da lista de ids que alimenta HIGH-01 e HIGH-03.

**O que fazer**, depois de `CRIT-01`

1. Em `team_attendance` (`api.py:50-56`), remover o parâmetro `manager_id` e usar `caller.id`. Responder 403 se `caller.role != "gestor"`.
2. No frontend, mostrar a aba "Visão do time" (`App.jsx:144`) somente quando `/api/me` indicar papel de gestor, como conveniência de UI e não como controle.

```python
@router.get("/api/team-attendance")
async def team_attendance(month: str = Query(...), caller: User = Depends(get_current_user)):
    if caller.role != "gestor":
        raise HTTPException(403, "Apenas gestores")
    return service.get_team_month(caller.id, month)
```

**Validação:** inverter `test_manager_view_is_exposed_to_a_different_x_user` para esperar 403 · `test_manager_monthly_view_and_manager_without_team` continua passando com o token de Ana.

### MED-01 · Datas inválidas, futuras ou de meses fechados contam para a meta

- **Severidade:** MEDIUM (impacto 2 × probabilidade 3). Qualquer usuário infla a própria meta ou edita meses já avaliados com uma requisição trivial. Também é um bug, porque a UI permite confirmar dias futuros por engano.
- **Tipo:** Vulnerabilidade
- **Categoria:** `INT-VAL` / CWE-20, CWE-1284 · **Confiança:** Confirmado (0,9)
- **Local:** `backend/app/adapters/http/api.py:28-30`, `backend/app/application/attendance_service.py:31-33`, `backend/app/adapters/persistence/sqlite.py:35`; `frontend/src/App.jsx:67`, `App.jsx:12`, `App.jsx:110`

**Evidência**

```python
# backend/app/application/attendance_service.py:31-33
def mark_day(self, command: AttendanceUpsertCommand) -> AttendanceRecord:
    # Values deliberately remain loosely validated for the benchmark.
    return self._repository.upsert(command)
# backend/app/adapters/persistence/sqlite.py:35
"WHERE user_id = ? AND substr(attendance_date, 1, 7) = ? "
```

- **Cenário:** como a contagem do mês usa só os 7 primeiros caracteres, `PUT /api/attendance/2026-10-01a`, `...-01b` etc. criam registros distintos que contam como presença em outubro. Oito chamadas batem a meta. Também é possível marcar `2026-12-15` (futuro) ou alterar meses passados. Na UI, todo dia de qualquer mês é clicável (`App.jsx:67`).
- **Reprodução:** `backend/tests/test_observed_behavior.py:47-59` mostra `PUT /api/attendance/amanha-talvez` → 200 gravado como `present`. Por leitura: uma data como `2026-10-01a` com observação faz `parseDate` (`App.jsx:12`) gerar `Invalid Date`, e `dateLabel.format` em `App.jsx:110` lança `RangeError`, o que derruba o detalhe do time (não há error boundary).
- **Esperado:** apenas datas ISO reais (`YYYY-MM-DD`), não futuras, dentro da janela de edição definida pelo negócio (por exemplo, mês corrente).
- **Atual:** qualquer texto é aceito como data e conta para a meta se começar com `AAAA-MM`.
- **Impacto:** o indicador de presença deixa de ser confiável para o gestor, e um registro malformado com nota quebra a tela de detalhe do time.

**O que fazer**

1. Criar `parse_attendance_date(value: str, today: date) -> date` em `backend/app/domain/` usando `date.fromisoformat`. Rejeitar datas futuras e fora da janela permitida, lançando um `AttendanceError` (hoje sem uso, `domain/errors.py:4`).
2. Chamar a função em `mark_day` e `unmark_day` (`attendance_service.py:31-37`) e mapear `AttendanceError` para 422 no adaptador HTTP. No FastAPI, tipar o path param como `attendance_date: date` (`api.py:30`) para rejeitar formatos inválidos já na borda.
3. Fixar o fuso da regra "hoje" (por exemplo, `America/Sao_Paulo`) e injetar `today` no serviço para permitir teste.
4. No frontend, desabilitar dias futuros e meses fora da janela em `Calendar` (`App.jsx:67`, `disabled={cell.attendance_date > today}`).

```python
def parse_attendance_date(value: str, today: date) -> date:
    try:
        day = date.fromisoformat(value)
    except ValueError:
        raise AttendanceError("Data inválida")
    if day > today or (day.year, day.month) != (today.year, today.month):
        raise AttendanceError("Data fora da janela de confirmação")
    return day
```

**Validação:** testes novos: `PUT /api/attendance/2026-10-01a` e `/amanha-talvez` → 422; data de amanhã → 422; mês anterior → 422; inverter `test_payload_keeps_unvalidated_date_user_and_notes` · confirmar o dia de hoje continua retornando 200.

### MED-02 · Trocar rápido de mês ou de perfil mostra dados da resposta errada

- **Severidade:** MEDIUM (impacto 2 × probabilidade 3). Acontece no uso comum, ao navegar meses ou trocar perfil, e a tela passa a exibir contagem e calendário de outro mês ou de outra pessoa.
- **Tipo:** Bug
- **Categoria:** `FE` / CWE-362 · **Confiança:** Provável (0,85)
- **Local:** `frontend/src/App.jsx:122-127`

**Evidência**

```jsx
// frontend/src/App.jsx:122-127
async function load() {
  setLoading(true); setNotice(null);
  try { const headers = { "X-User": user }; if (tab === "personal") setAttendance(await request(`/api/attendance?user_id=...&month=${currentMonth}`, { headers })); else setTeam(await request(...)); }
  catch (error) { setNotice({ type: "error", text: error.message }); } finally { setLoading(false); }
}
useEffect(() => { setSelectedDate(""); setSelectedMember(""); load(); }, [user, tab, currentMonth]);
```

- **Cenário:** o usuário clica duas vezes em "Próximo mês". Se a resposta de outubro chega depois da de novembro, o calendário de novembro mostra a meta de outubro. Em caso de erro, `attendance`/`team` mantêm os dados do perfil anterior (Bruno vê o mês de Ana com o cabeçalho "Olá, Bruno"). O primeiro `finally` também desliga o `loading` enquanto a segunda requisição ainda está pendente.
- **Reprodução:** em DevTools, com a rede em "Slow 3G", avançar dois meses seguidos → o contador "de 8 dias" mostra o valor do mês intermediário. Por leitura: não há `AbortController`, flag de cancelamento nem verificação da chave da resposta.
- **Esperado:** só a resposta da combinação atual (perfil, aba, mês) atualiza a tela.
- **Atual:** vence a última resposta que chegar.
- **Impacto:** o colaborador decide marcar ou não presença com base em uma contagem errada, e o gestor vê o mês errado do time.

**O que fazer**

1. Em `App.jsx:127`, criar um `AbortController` por execução do efeito, passar `signal` para `request()` (`App.jsx:27-28`, `fetch(url, { ...options, signal })`) e abortar no cleanup.
2. Limpar `attendance`/`team` (`setAttendance(null)`) no início de `load` e ignorar `AbortError` no `catch`.
3. Em `save`/`remove` (`App.jsx:129-138`), reutilizar a mesma função de carga com controle de cancelamento.

```jsx
useEffect(() => {
  const ctrl = new AbortController();
  setSelectedDate(""); setSelectedMember(""); load(ctrl.signal);
  return () => ctrl.abort();
}, [user, tab, currentMonth]);
// em load: catch (e) { if (e.name !== "AbortError") setNotice(...) }
```

**Validação:** teste Vitest com `fetch` mockado que resolve a primeira chamada depois da segunda e afirma que a tela mostra o `present_count` da segunda · navegação simples entre meses continua carregando normalmente.

### MED-03 · A API deixa de subir quando a tabela de presenças fica vazia e injeta dados fictícios na base

- **Severidade:** MEDIUM (impacto 2 × probabilidade 2). Exige uma condição de dados plausível (todas as presenças removidas, inclusive por anônimos via CRIT-01). Nesse caso, o próximo boot falha e a API fica fora do ar até intervenção manual.
- **Tipo:** Bug
- **Categoria:** `CONC` (persistência) / CWE-1188, CWE-755 · **Confiança:** Confirmado (0,9)
- **Local:** `backend/app/adapters/persistence/sqlite.py:85-95`, `sqlite.py:141-145`, `sqlite.py:156`

**Evidência**

```python
# backend/app/adapters/persistence/sqlite.py:141-145 e 88-89
count = connection.execute("SELECT COUNT(*) AS total FROM attendance").fetchone()["total"]
if count == 0:
    seed()
...
connection.executemany(
    "INSERT INTO team_members (manager_id, user_id, name) VALUES (?, ?, ?)",
```

- **Cenário:** o banco fica no volume persistente `polo-data`. Se todas as presenças forem removidas pelo `DELETE` (uso normal no início de mês ou abuso), `team_members` continua com `(ana, bruno)` etc. No restart, `seed()` tenta reinserir essas linhas, viola `PRIMARY KEY(manager_id, user_id)` (`sqlite.py:135`) e levanta `sqlite3.IntegrityError` no import do módulo (`sqlite.py:156`), então o uvicorn não sobe. Além disso, todo primeiro boot em produção grava a equipe fictícia "Bruno/Carla/Diego Demo" sob `ana` e presenças falsas no mês corrente.
- **Reprodução:** com a API local, apagar as 8 presenças semeadas via `DELETE /api/attendance/<data>?user_id=<id>` e reiniciar o container → `IntegrityError: UNIQUE constraint failed: team_members.manager_id, team_members.user_id` e o container em crash loop.
- **Esperado:** o boot é idempotente e dados de demonstração nunca entram no banco real sem pedido explícito.
- **Atual:** o seed roda automaticamente sempre que `attendance` está vazia, sem `OR IGNORE`.
- **Impacto:** indisponibilidade total da API e mistura de dados fictícios com dados reais de presença e equipe.

**O que fazer**

1. Remover a chamada automática a `seed()` de `initialize_database` (`sqlite.py:141-145`) e expô-la só por um comando explícito de desenvolvimento (por exemplo, `python -m app.seed`) ou pela flag `POLO_SEED_DEMO=1`.
2. Tornar o seed idempotente: `INSERT OR IGNORE` em `team_members` e em `attendance` (`sqlite.py:89`, `:108`).
3. Cadastrar equipes reais por migração ou rotina administrativa, não pelo seed.

```python
def initialize_database(seed_demo: bool = os.getenv("POLO_SEED_DEMO") == "1") -> None:
    connection.executescript(SCHEMA)
    if seed_demo:
        seed()  # com INSERT OR IGNORE
```

**Validação:** teste novo: com `team_members` populada e `attendance` vazia, `initialize_database()` não lança exceção nem cria presenças · com `POLO_SEED_DEMO=1` em banco novo, o seed continua disponível para demos.

### MED-04 · CORS aceita qualquer site com credenciais, permitindo que páginas externas operem a API pelo navegador do colaborador

- **Severidade:** MEDIUM (impacto 2 × probabilidade 2). Exige que a vítima, com acesso à rede da API, visite uma página maliciosa. Nesse caso, a página consegue ler e alterar presenças por meio do navegador da vítima.
- **Tipo:** Vulnerabilidade
- **Categoria:** `SEC-CONF` / CWE-942 · **Confiança:** Confirmado (0,9)
- **Local:** `backend/app/main.py:10-16`

**Evidência**

```python
# backend/app/main.py:10-16
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- **Cenário:** a API costuma ficar acessível só na rede interna (ou em `localhost`). O `PUT`/`DELETE` com `X-User` e JSON exige preflight, que normalmente bloquearia um site externo. Aqui o Starlette reflete a origem e libera credenciais, então `https://site-malicioso` apaga ou lê presenças pelo navegador do colaborador. Quando houver sessão por cookie (CRIT-01), o mesmo vira CSRF autenticado.
- **Reprodução:** `backend/tests/test_observed_behavior.py:63-76`: preflight de `https://untrusted.example` para `PUT` → 200, `access-control-allow-origin: https://untrusted.example` e `access-control-allow-credentials: true`.
- **Esperado:** apenas a origem do próprio frontend é aceita.
- **Atual:** qualquer origem é refletida com credenciais.
- **Impacto:** sites de terceiros alcançam e manipulam uma API interna através dos navegadores dos colaboradores.

**O que fazer**

1. Em `main.py:10-16`, ler as origens permitidas de uma variável (`POLO_ALLOWED_ORIGINS`, por exemplo `http://localhost:5173`) e usar `allow_methods=["GET","PUT","DELETE"]` e `allow_headers=["Authorization","Content-Type"]`.
2. Manter `allow_credentials=False` enquanto não houver cookie. Se o frontend passar a chamar `/api` pela mesma origem via nginx (MED-06), remover o middleware de CORS.

```python
origins = [o for o in os.getenv("POLO_ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                   allow_methods=["GET", "PUT", "DELETE"],
                   allow_headers=["Authorization", "Content-Type"])
```

**Validação:** inverter `test_browser_preflight_contract_remains_permissive`: origem `https://untrusted.example` não recebe `access-control-allow-origin` · preflight de `http://localhost:5173` continua aprovado.

### MED-05 · Alterações e remoções de presença não registram quem fez nem o valor anterior

- **Severidade:** MEDIUM (impacto 2 × probabilidade 2). Sempre que um registro é adulterado ou removido (por engano ou de propósito), não há como saber quem foi nem recuperar o valor anterior.
- **Tipo:** Vulnerabilidade
- **Categoria:** `INT-WF` / CWE-778 · **Confiança:** Confirmado (0,9)
- **Local:** `backend/app/adapters/persistence/sqlite.py:69-74`, `sqlite.py:48-51`, `sqlite.py:120-129`

**Evidência**

```python
# backend/app/adapters/persistence/sqlite.py:69-74
def delete(self, user_id: str, attendance_date: str) -> None:
    self._connection.execute(
        "DELETE FROM attendance WHERE user_id = ? AND attendance_date = ?",
        (user_id, attendance_date),
    )
    self._connection.commit()
```

- **Cenário:** a remoção é física e o `ON CONFLICT ... DO UPDATE` (`sqlite.py:48-51`) sobrescreve `notes` e `updated_at`. O esquema (`sqlite.py:120-129`) não tem coluna de autor. Se alguém apagar as presenças de um colega (HIGH-01) ou o próprio colaborador negar uma alteração, o gestor não tem como apurar.
- **Reprodução:** por leitura: após `DELETE /api/attendance/<data>?user_id=bruno`, nenhuma tabela guarda vestígio da linha removida nem do autor.
- **Esperado:** cada criação, edição e remoção gera um evento com autor, ação, valor anterior, valor novo e horário.
- **Atual:** só existe o estado final, sem autor.
- **Impacto:** fraudes e erros na meta ficam indetectáveis e irrecuperáveis.

**O que fazer**, depois de `CRIT-01` (o autor precisa ser a identidade autenticada)

1. Criar a tabela `attendance_events(id, user_id, attendance_date, action, actor_id, before_json, after_json, at)` em `initialize_database` (`sqlite.py:117-138`).
2. Em `upsert` e `delete`, ler a linha atual, executar a mudança e inserir o evento na mesma transação (`with self._connection:`).
3. Incluir `actor_id` em `AttendanceUpsertCommand` (`domain/models.py:7-11`) e na assinatura de `delete` da porta (`domain/ports.py:13-15`).

**Validação:** teste novo: após `PUT` e `DELETE`, `attendance_events` tem 2 linhas com `actor_id` do token e o `before_json` da remoção · o fluxo de marcar e remover continua respondendo 200.

### MED-06 · O frontend só funciona quando o navegador está na mesma máquina da API

- **Severidade:** MEDIUM (impacto 2 × probabilidade 2). Em qualquer implantação fora da máquina do usuário, todas as chamadas vão para o `localhost` do visitante e o app fica inutilizável.
- **Tipo:** Bug
- **Categoria:** `FE` / CWE-1188 · **Confiança:** Confirmado (0,9)
- **Local:** `frontend/src/App.jsx:3`, `App.jsx:28`; `frontend/Dockerfile:18-20`

**Evidência**

```jsx
// frontend/src/App.jsx:3 e 28
const API_URL = "http://localhost:8001";
  const response = await fetch(`${API_URL}${path}`, options);
```

- **Cenário:** a imagem nginx (`frontend/Dockerfile:18-20`) é publicada em um servidor. O colaborador abre `http://servidor:5173`, e o navegador dele tenta `http://localhost:8001`, que não existe na máquina dele. Sob HTTPS, a chamada ainda é bloqueada como conteúdo misto.
- **Reprodução:** o próprio E2E precisa reescrever a URL para funcionar fora do host (`frontend/e2e/visit-flow.spec.js:7-11`). Abrir o app de outra máquina → "Não foi possível concluir a solicitação." em todas as telas.
- **Esperado:** a URL da API vem da configuração de build ou é relativa (`/api`) e o nginx faz o proxy.
- **Atual:** URL absoluta fixa no bundle.
- **Impacto:** o app não funciona em nenhum ambiente compartilhado, e a configuração atual obriga o CORS amplo de MED-04.

**O que fazer**

1. Em `App.jsx:3`, usar `const API_URL = import.meta.env.VITE_API_URL ?? "";` para que as chamadas fiquem relativas (`/api/...`).
2. Criar `frontend/nginx.conf` com `location /api/ { proxy_pass http://polo-api:8001; }`, a rota `/health` se necessário e `try_files $uri /index.html` para o SPA. Copiar com `COPY nginx.conf /etc/nginx/conf.d/default.conf` no estágio final do `Dockerfile` (após a linha 18).
3. Para `npm run dev`, configurar `server.proxy` em `vite.config.js` (`"/api": "http://localhost:8001"`).

**Validação:** E2E sem o `page.route` de reescrita (`visit-flow.spec.js:4-12`) acessando o app pelo nome do serviço · `npm run dev` local continua funcionando pelo proxy do Vite.

### LOW-01 · Todo boot apaga presenças com status diferente de "present"

- **Severidade:** LOW (impacto 2 × probabilidade 1). Hoje só existe o status `present`, mas qualquer status novo (por exemplo, "remoto" ou a remoção lógica proposta em MED-05) seria apagado silenciosamente no restart.
- **Tipo / Categoria:** Dívida técnica · `CONC` (persistência) / CWE-1188 · **Confiança:** Confirmado (0,9)
- **Local:** `backend/app/adapters/persistence/sqlite.py:139-140`
- **Evidência:** `connection.execute("DELETE FROM attendance WHERE status != 'present'")` executado em `initialize_database()` a cada import.
- **Esperado / Atual / Impacto:** inicialização sem efeito sobre dados · inicialização com `DELETE` destrutivo · perda silenciosa de registros assim que o domínio ganhar outro status.
- **O que fazer:** remover as linhas 139-140 de `sqlite.py`. Se for preciso limpar status legados, fazer isso em uma migração versionada e única, nunca no boot.
- **Validação:** teste: inserir linha com `status='remote'`, chamar `initialize_database()` e afirmar que ela continua lá.

### LOW-02 · Container da API roda como root

- **Severidade:** LOW (impacto 2 × probabilidade 1). Não há caminho de execução de código hoje, mas qualquer RCE futura ganharia root no container e no volume de dados.
- **Tipo / Categoria:** Vulnerabilidade · `SEC-CONF` / CWE-250 · **Confiança:** Confirmado (0,9)
- **Local:** `backend/Dockerfile:13-17`
- **Evidência:** o estágio `runtime` não tem instrução `USER`, e `RUN mkdir -p /app/data` cria o diretório do banco como root.
- **Esperado / Atual / Impacto:** processo com usuário sem privilégio · uvicorn como UID 0 · amplia o dano de uma falha futura.
- **O que fazer:** no estágio `runtime`, `RUN useradd --system --uid 10001 app && mkdir -p /app/data && chown app /app/data` seguido de `USER app` antes do `CMD`.
- **Validação:** `docker run --rm polo-api id -u` → `10001`. `PUT /api/attendance/...` continua gravando no volume.

### LOW-03 · Banco aberto, criado e semeado no import do módulo, com caminho relativo e conexão global

- **Severidade:** LOW (impacto 2 × probabilidade 1). Importar o pacote já cria arquivo e grava dados, o banco muda conforme o diretório de execução, e uma única conexão com `check_same_thread=False` fica compartilhada entre threads.
- **Tipo / Categoria:** Dívida técnica · `ARQ` / CWE-1047 · **Confiança:** Confirmado (0,9)
- **Local:** `backend/app/adapters/persistence/sqlite.py:10-13`, `sqlite.py:156`; `backend/tests/conftest.py:5-6`; `README.md:108`
- **Evidência:** `DB_PATH = Path(os.getenv("POLO_DB_PATH", "data/polo.db"))` + `sqlite3.connect(DB_PATH, check_same_thread=False)` + `initialize_database()` no import. Os testes dependem de definir a env antes do import (`conftest.py:5-6`).
- **Esperado / Atual / Impacto:** conexão criada no ciclo de vida da app, com caminho absoluto · efeitos colaterais no import e caminho relativo ao CWD (o README diz `backend/data/polo.db`) · testes frágeis e risco de corrupção se algum handler virar `def` síncrono (threadpool) usando a mesma conexão.
- **O que fazer:** criar `create_app(db_path)` em `main.py` que abra a conexão no `lifespan` (uma conexão por requisição via dependência ou um pool), e resolver o padrão com `Path(__file__).resolve().parents[3] / "data" / "polo.db"`.
- **Validação:** `import app.main` em um diretório vazio não cria `data/`. Os testes passam usando `create_app(tmp_path / "polo.db")` sem manipular `os.environ`.

### LOW-04 · Dependências do frontend em "latest" e sem lockfile

- **Severidade:** LOW (impacto 2 × probabilidade 1). Cada build instala a versão mais nova de React, Vite e plugins, então uma major incompatível ou um pacote comprometido entra direto na imagem.
- **Tipo / Categoria:** Dívida técnica · `SEC-DEP` / CWE-1104 · **Confiança:** Confirmado (0,9)
- **Local:** `frontend/package.json:13-23`; `frontend/Dockerfile:3-4`, `Dockerfile:13-14`
- **Evidência:** `"vite": "latest"`, `"react": "latest"`, `"vitest": "latest"` etc. Não há `package-lock.json`, e o Dockerfile copia só `package.json` antes de `npm install`.
- **Esperado / Atual / Impacto:** build reprodutível com versões travadas · resolução diferente a cada build · quebra de build ou supply chain sem revisão.
- **O que fazer:** fixar versões exatas no `package.json`, versionar `package-lock.json` e trocar `COPY package.json .` + `RUN npm install` por `COPY package.json package-lock.json ./` + `RUN npm ci` nos dois estágios.
- **Validação:** dois builds seguidos produzem `node_modules` com as mesmas versões (`npm ls --depth=0` idêntico).

### LOW-05 · nginx publica o frontend sem cabeçalhos de segurança

- **Severidade:** LOW (impacto 1 × probabilidade 2). É defesa em profundidade: sem CSP, o XSS de HIGH-02 executa sem nenhuma barreira, e o app pode ser embutido em iframe.
- **Tipo / Categoria:** Vulnerabilidade · `SEC-CONF` / CWE-1021, CWE-693 · **Confiança:** Confirmado (0,9)
- **Local:** `frontend/Dockerfile:18-20`
- **Evidência:** o estágio final só copia `dist`. Sem `nginx.conf` próprio, vale o `default.conf` da imagem, sem `Content-Security-Policy`, `X-Content-Type-Options`, `frame-ancestors` e com `server_tokens` ligado.
- **Esperado / Atual / Impacto:** respostas com CSP e anti-framing · cabeçalhos padrão do nginx · nenhuma mitigação de navegador contra XSS ou clickjacking.
- **O que fazer:** no `nginx.conf` de MED-06, adicionar `server_tokens off;` e `add_header Content-Security-Policy "default-src 'self'; connect-src 'self'; frame-ancestors 'none'" always;`, `add_header X-Content-Type-Options nosniff always;` e `add_header Referrer-Policy no-referrer always;`.
- **Validação:** `curl -I http://localhost:5173/` mostra os cabeçalhos. O app continua carregando sem violações de CSP no console.

### LOW-06 · Calendário e barras de progresso com papéis ARIA incompletos

- **Severidade:** LOW (impacto 1 × probabilidade 3). Afeta sempre quem usa leitor de tela: o `grid` não tem linhas e o progresso não é anunciado como valor.
- **Tipo / Categoria:** Bug · `FE` / CWE-1021 · **Confiança:** Confirmado (0,9)
- **Local:** `frontend/src/App.jsx:63`, `App.jsx:67`, `App.jsx:53`
- **Evidência:** `role="grid"` com filhos `role="gridcell"` diretos, sem `role="row"`. A barra de progresso é um `<div aria-label>` sem `role="progressbar"` nem `aria-valuenow`.
- **Esperado / Atual / Impacto:** estrutura `grid > row > gridcell` e `progressbar` com valor · estrutura ARIA inválida · navegação por tabela e leitura da meta falham em leitores de tela.
- **O que fazer:** agrupar as células em semanas dentro de `<div role="row">` em `Calendar` (`App.jsx:63-70`) e, em `Progress` (`App.jsx:53`), usar `role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}`.
- **Validação:** `axe` (ou `jest-axe` no Vitest) sem violações `aria-required-children`. `getByRole("progressbar")` passa a encontrar a meta.

### LOW-07 · Erros de validação da API aparecem como "[object Object]"

- **Severidade:** LOW (impacto 1 × probabilidade 2). Quando a API devolve 422 do FastAPI (por exemplo, após MED-01), o usuário vê uma mensagem inútil.
- **Tipo / Categoria:** Bug · `FE` / CWE-755 · **Confiança:** Confirmado (0,9)
- **Local:** `frontend/src/App.jsx:31-32`
- **Evidência:** `message = body.detail || ...; throw new Error(message)`: em um 422, `detail` é uma lista de objetos e `new Error(lista)` vira `"[object Object]"`.
- **Esperado / Atual / Impacto:** mensagem legível · texto "[object Object]" no aviso · o usuário não sabe por que a marcação falhou.
- **O que fazer:** em `request()`, usar `Array.isArray(body.detail) ? body.detail.map((d) => d.msg).join("; ") : body.detail` antes de lançar o erro.
- **Validação:** teste Vitest com `fetch` respondendo `422 {detail:[{msg:"Data inválida"}]}` e o alerta contendo "Data inválida".

### LOW-08 · Frontend aceita vários formatos de resposta e repete a meta de 8 dias do backend

- **Severidade:** LOW (impacto 1 × probabilidade 2). Os fallbacks escondem quebras de contrato: se o backend mudar a meta ou um campo, a UI mostra 8 dias ou um total recalculado sem acusar erro, e o teste do time já exercita só o formato alternativo.
- **Tipo / Categoria:** Dívida técnica · `MNT` / CWE-1041 · **Confiança:** Confirmado (0,9)
- **Local:** `frontend/src/App.jsx:4`, `App.jsx:14-17`, `App.jsx:87-88`, `App.jsx:96-99`, `App.jsx:103-106`; `frontend/src/App.test.jsx:14`
- **Evidência:** `raw.present_count ?? raw.present ?? raw.days_present`, `data?.team_present_total ?? data?.total_present ?? ...`, `const GOAL = 8`. O mock do teste usa `total_present`/`average_present`, campos que o backend nunca envia.
- **Esperado / Atual / Impacto:** um único contrato, com `goal` vindo da API · regra e contrato duplicados no cliente · divergências silenciosas entre UI e backend.
- **O que fazer:** remover `GOAL`, `normalizeDays` com objeto e os fallbacks de `memberFrom`/`Team`/`Personal`, usar só os campos de `attendance_service.py:11-19` e `:54-64`, e alinhar o mock de `App.test.jsx:14` ao contrato real.
- **Validação:** testes do frontend passam com mocks idênticos às respostas de `test_flows.py`. Mudar `MONTHLY_GOAL` no backend reflete na UI.

### LOW-09 · Toda a UI está em um componente com linhas de mais de mil caracteres

- **Severidade:** LOW (impacto 1 × probabilidade 2). Chamadas de API, estado e telas ficam em `App.jsx`, com JSX em uma linha por tela. Isso dificulta revisão e teste isolado: o `dangerouslySetInnerHTML` de HIGH-02 está no meio de uma linha de ~1.500 caracteres.
- **Tipo / Categoria:** Dívida técnica · `ARQ` / CWE-1120 · **Confiança:** Confirmado (0,9)
- **Local:** `frontend/src/App.jsx:109-110`, `App.jsx:124`, `App.jsx:141-146`
- **Evidência:** `App.jsx:110` contém o detalhe do time inteiro (cabeçalho, calendário e notas) em uma única linha. `load`, `save` e `remove` (`App.jsx:122-138`) misturam fetch e estado de tela.
- **Esperado / Atual / Impacto:** módulos `api.js`, `Team.jsx`, `Personal.jsx` formatados · um arquivo com linhas gigantes · diffs ilegíveis e regressões que passam despercebidas na revisão.
- **O que fazer:** extrair `request`/`load*` para `src/api.js`, mover `Team`, `Personal`, `Calendar` e `Editor` para arquivos próprios e aplicar Prettier ao projeto.
- **Validação:** testes atuais continuam passando. Novos testes unitários de `Team` renderizam o componente sem montar `App`.

## Observações (INFO, hipóteses e descartados)

- **INFO:** o backend segue arquitetura hexagonal real: `monthly_summary` (`attendance_service.py:7-19`) é testável sem HTTP nem banco. As correções de MED-01 e HIGH-03 cabem no domínio e na porta existentes.
- **INFO:** todas as consultas SQL usam parâmetros `?` (`sqlite.py:33-81`). Nenhum segredo ou token versionado foi encontrado.
- **INFO:** a imagem de runtime não usa `--reload` (`backend/Dockerfile:17`), a imagem final do frontend serve o build estático e não o Vite dev, e o `.dockerignore` exclui `data` (o banco não vai para a imagem).
- **INFO:** `/docs` e `/openapi.json` ficam expostos por padrão (`main.py:9`). Avaliar `docs_url=None` em produção depois de CRIT-01.
- **INFO:** `compose.yaml:11-12` e `:18-19` publicam 8001 e 5173 em todas as interfaces do host, o que amplia o alcance de CRIT-01 (o arquivo fica fora de `polo-visits`).
- **INFO:** as imagens base (`python:3.12-slim`, `node:22-alpine`, `nginx:1.27-alpine`) não são fixadas por digest, o que reduz a reprodutibilidade.
- **INFO:** código morto ou enganoso sem consequência própria: `AttendanceError` nunca é lançado (`domain/errors.py:4`, reaproveitado em MED-01), a docstring "API legada para agendamentos de visitas" (`app/__init__.py:1`) não descreve o app atual e `database.py` existe só para os testes.
- **INFO:** `backend/tests/test_observed_behavior.py` (4 testes) e `App.test.jsx:41-50` fixam comportamentos inseguros. Foram usados como evidência em HIGH-01 a HIGH-04, MED-01 e MED-04 e precisam ser invertidos junto com as correções para não virarem regressão.
- **INFO:** o servidor usa `date.today()` no fuso do container (`sqlite.py:21`) e o navegador usa hora local (`App.jsx:59-60`). Definir um fuso único ao implementar MED-01.
- **Hipótese:** corrida entre `upsert` e o `SELECT` seguinte na conexão compartilhada (`sqlite.py:43-66`). Hoje os handlers são `async def` e rodam na thread do event loop, o que serializa o acesso. Só vira defeito se algum handler passar a `def` (risco registrado em LOW-03).
- **Descartado:** injeção de SQL (consultas parametrizadas pelo driver: sinal de falso positivo).
- **Descartado:** troca de perfil feita só na UI e `user_id` arbitrário criando registros de usuários inexistentes (mesma causa e mesma correção de CRIT-01/HIGH-01, consolidado).
- **Descartado:** `notes` sem limite de tamanho (exclusão fixa: DoS e esgotamento de recurso).
- **Descartado:** consulta N+1 por integrante em `get_team_month` (`attendance_service.py:41-46`) e SQLite bloqueante dentro de `async def` (exclusão fixa: desempenho/DoS).
- **Descartado:** `month` sem validação (`api.py:23`, `:54`): um formato inválido só devolve lista vazia ao próprio chamador (exclusão fixa: validação sem efeito de segurança ou de regra).
- **Descartado:** `DELETE` de data inexistente responde `unmarked` com 200 (idempotência aceitável, sem efeito de regra).
- **Descartado:** `status` como string livre: o valor é a constante `"present"` (`sqlite.py:56`), não entrada externa.
- **Descartado:** vazamento de erro interno: nenhum handler devolve `str(e)` ou traceback, só o 422 padrão do FastAPI (mitigação verificada).
- **Descartado:** processo master do nginx como root (os workers rodam como `nginx` na imagem oficial; mitigação existente).
- **Descartado:** script `dev` com `vite --host 0.0.0.0` (`package.json:7`): só para desenvolvimento, e a imagem final é nginx (mitigação verificada em `frontend/Dockerfile:18-19`).
- **Descartado:** E2E que altera o banco real do Compose e depende do seed (`visit-flow.spec.js:21-24`, `:65-67`) (exclusão fixa: código de teste).
