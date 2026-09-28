# Gabarito privado — baseline legado

Este arquivo pertence à avaliação do mantenedor. Não deve ser fornecido à skill durante a execução cega. As linhas abaixo correspondem ao baseline atualizado em 2026-09-28; se o legado for alterado antes da avaliação, atualize as referências.

## Cobertura

| Projeto | CRITICAL | HIGH | MEDIUM | LOW | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Plataforma de agentes | 1 | 4 | 4 | 2 | 11 |
| Controle de presença no polo | 0 | 3 | 5 | 3 | 11 |
| **Total** | **1** | **7** | **9** | **5** | **22** |

Categorias cobertas: autorização, acesso a arquivos, XSS, isolamento de estado, validação, integridade e auditabilidade, concorrência/persistência, exposição de informação, acoplamento arquitetural, configuração web, frontend e manutenção.

## Projeto 1 — Plataforma de agentes

### P1-01 — Leitura arbitraria de arquivos locais

- **Categoria / severidade:** seguranca, controle de acesso a recursos — **CRITICAL**.
- **Arquivo/linhas:** `langgraph-agent-platform/app/main.py:60-61` e `:78-80`.
- **Evidencia e reproducao:** `read_file` aceita qualquer `Path` e o comando `read` o executa imediatamente, sem diretorio permitido nem HITL. Envie `read /etc/hosts` no Linux/container ou um caminho absoluto legivel no Windows; o conteudo volta em `result`.
- **Esperado / atual:** esperado limitar a leitura a recursos explicitamente autorizados, validar o caminho e, conforme o recurso, exigir aprovacao; atualmente qualquer arquivo legivel pelo processo pode ser retornado ao chamador.
- **Impacto:** exposicao de configuracoes, codigo, bancos locais, tokens ou outros segredos disponiveis ao usuario do processo.
- **Correcao esperada:** remover a ferramenta generica ou usar uma raiz allowlist resolvida com `Path.resolve()`, rejeitar escapes/symlinks, autorizar o solicitante e aplicar HITL para recursos sensiveis.
- **Demonstracao:** `docker run --rm agent-platform-test python -m pytest -q tests/test_observed_behavior.py::test_file_tool_contract`.

### P1-02 — Aprovacao HITL nao pertence ao usuario nem ao solicitante

- **Categoria / severidade:** seguranca, autorizacao e integridade de workflow — **HIGH**.
- **Arquivo/linhas:** `langgraph-agent-platform/app/main.py:241-255`.
- **Evidencia e reproducao:** a rota localiza somente pelo `conversation_id`; `body.user_id` vira metadado `reviewer`, mas nunca e comparado com `item["user_id"]` nem com uma politica de aprovadores. Crie a acao como `ana` e aprove como `bruno`.
- **Esperado / atual:** esperado validar identidade autenticada, papel do aprovador, tenant e vinculo com execucao/acao pendente; atualmente qualquer pessoa que conheca o UUID pode aprovar ou recusar.
- **Impacto:** execucao nao autorizada de ferramentas e quebra da trilha de auditoria HITL.
- **Correcao esperada:** obter identidade de mecanismo confiavel, guardar solicitante/tenant/aprovadores no checkpoint, comparar todos os vinculos e registrar decisao atomica e auditavel.
- **Demonstracao:** `docker run --rm agent-platform-test python -m pytest -q tests/test_observed_behavior.py::test_access_contract_for_saved_runs`.

### P1-03 — Historico de conversa acessivel sem autorizacao

- **Categoria / severidade:** seguranca, controle de acesso/IDOR — **HIGH**.
- **Arquivo/linhas:** `langgraph-agent-platform/app/main.py:233-238`.
- **Evidencia e reproducao:** `GET /api/conversations/{id}` nao recebe nem verifica identidade. Depois de criar uma conversa de Ana, consulte o UUID sem credencial ou como outro usuario.
- **Esperado / atual:** esperado permitir somente participante ou administrador autorizado do mesmo tenant; atualmente o UUID e a unica barreira.
- **Impacto:** vazamento de mensagens, resultado de ferramentas, destinatarios e acoes pendentes.
- **Correcao esperada:** autenticacao real, consulta com escopo por proprietario/tenant e resposta minima; nao aceitar `user_id` autodeclarado como autenticacao.
- **Demonstracao:** o mesmo `test_access_contract_for_saved_runs` acima verifica a leitura direta do run de Ana.

### P1-04 — Configuracao de agente pode ser tomada por qualquer chamador

- **Categoria / severidade:** seguranca, autorizacao administrativa — **HIGH**.
- **Arquivo/linhas:** `langgraph-agent-platform/app/main.py:192-196`; `app/database.py:67-84`.
- **Evidencia e reproducao:** `PUT /api/agents/assistant-demo` nao autentica nem compara `owner_id`; `INSERT OR REPLACE` substitui o registro. Envie outro owner, nome, prompt e conjunto de ferramentas.
- **Esperado / atual:** esperado apenas o proprietario/administrador alterar configuracao e ferramentas aprovadas; atualmente um chamador anonimo redefine todo o agente.
- **Impacto:** sequestro de comportamento, desabilitacao do fluxo ou habilitacao de ferramentas de maior alcance.
- **Correcao esperada:** autenticar, autorizar por tenant/owner, separar create/update, aplicar allowlist de ferramentas e controle otimista de versao.
- **Demonstracao:** `docker run --rm agent-platform-test python -m pytest -q tests/test_observed_behavior.py::test_agent_replacement_contract`.

### P1-05 — Contexto do agente e estado global de processo

- **Categoria / severidade:** arquitetura e isolamento de estado — **HIGH**.
- **Arquivo/linhas:** `langgraph-agent-platform/app/main.py:69`, `:99-101` e `:199-206`.
- **Evidencia e reproducao:** `plan_message` ignora `state["agent_id"]` e usa `ACTIVE_AGENT`, alterado por cada request. O teste monta estado para `agent-a`, deixa `agent-b` global e obtem resposta de B.
- **Esperado / atual:** esperado resolver/configurar o agente a partir do estado imutavel da propria execucao; atualmente o comportamento depende da ultima escrita global, com risco de contaminacao entre requisicoes concorrentes.
- **Impacto:** agente, prompt ou ferramentas errados em outra conversa; isolamento de tenant imprevisivel e testes dependentes de ordem.
- **Correcao esperada:** incluir snapshot/configuracao identificada no estado do grafo, resolver dependencias por execucao e eliminar mutabilidade global.
- **Demonstracao:** `docker run --rm agent-platform-test python -m pytest -q tests/test_observed_behavior.py::test_process_context_contract`.

### P1-06 — Entradas sem limites ou validacao semantica

- **Categoria / severidade:** seguranca/qualidade, validacao e disponibilidade — **MEDIUM**.
- **Arquivo/linhas:** `langgraph-agent-platform/app/main.py:28-45`.
- **Evidencia e reproducao:** modelos aceitam usuario em branco, IDs sem formato, prompt/mensagem arbitrariamente grandes e nomes de ferramentas desconhecidas. O teste envia usuario composto por espaco e mensagem de 200 mil caracteres, que e processada e persistida.
- **Esperado / atual:** esperado strings normalizadas, nao vazias, limites de tamanho, IDs tipados e enum/allowlist de ferramentas; atualmente apenas tipos basicos sao verificados.
- **Impacto:** consumo excessivo de memoria/disco, logs enormes, dados invalidos e configuracao incoerente.
- **Correcao esperada:** `Field(min_length, max_length, pattern)`, tipos especificos, validadores de dominio, limites HTTP e rejeicao de ferramentas desconhecidas.
- **Demonstracao:** `docker run --rm agent-platform-test python -m pytest -q tests/test_observed_behavior.py::test_input_contract_accepts_unbounded_fields`.

### P1-07 — SQLite global sincrono compartilhado por endpoints async

- **Categoria / severidade:** arquitetura, concorrencia e persistencia — **MEDIUM**.
- **Arquivo/linhas:** `langgraph-agent-platform/app/database.py:8-11`; `app/main.py:153-163`, `:187-257`.
- **Evidencia e reproducao:** ha uma conexao de dominio e outra de checkpoint globais com `check_same_thread=False`, sem lock/transaction boundary por request; endpoints `async` fazem I/O SQLite e `graph.invoke` sincronos no event loop.
- **Esperado / atual:** esperado conexao/sessao por unidade de trabalho, transacoes claras e I/O fora do event loop ou driver async; atualmente concorrencia pode bloquear o servidor, misturar transacoes ou produzir erros de lock/commit.
- **Impacto:** perda de throughput, falhas intermitentes e persistencia parcial entre checkpoint e tabela de conversas.
- **Correcao esperada:** repositorios injetados, pool/sessoes por request, transacao coordenada, locks quando necessarios e execucao async apropriada.
- **Demonstracao:** `rg -n "check_same_thread|connection\.execute|graph\.invoke|async def" langgraph-agent-platform/app` mostra singleton e chamadas bloqueantes; executar carga concorrente contra Uvicorn evidencia serializacao/contencao.

### P1-08 — Mensagens completas sao gravadas em stdout

- **Categoria / severidade:** seguranca operacional, logging — **MEDIUM**.
- **Arquivo/linhas:** `langgraph-agent-platform/app/main.py:220`.
- **Evidencia e reproducao:** a API imprime `user_id` e a mensagem integral para qualquer conversa.
- **Esperado / atual:** esperado log estruturado com IDs de correlacao e campos sensiveis omitidos/mascarados; atualmente todo o texto aparece nos logs do container.
- **Impacto:** dados fornecidos ao agente podem vazar para agregadores, operadores ou retencao de logs.
- **Correcao esperada:** remover payload, definir politica de redacao e logar apenas metadados necessarios com niveis apropriados.
- **Demonstracao:** `docker run --rm agent-platform-test python -m pytest -q tests/test_observed_behavior.py::test_runtime_output_contract`.

### P1-09 — Detalhes internos de excecao retornam ao cliente

- **Categoria / severidade:** seguranca, exposicao de informacao — **MEDIUM**.
- **Arquivo/linhas:** `langgraph-agent-platform/app/main.py:227-230` e `:256-257`.
- **Evidencia e reproducao:** excecoes inesperadas viram `HTTPException(detail=str(error))`. Ler um arquivo inexistente devolve o caminho interno do filesystem.
- **Esperado / atual:** esperado resposta publica generica e detalhes somente em log protegido; atualmente mensagens de biblioteca/SO chegam ao cliente.
- **Impacto:** revela caminhos, schema, estado e pistas uteis para outros ataques, alem de contrato instavel.
- **Correcao esperada:** handler central de erros, IDs de correlacao, excecoes de dominio mapeadas e redacao de detalhes.
- **Demonstracao:** `docker run --rm agent-platform-test python -m pytest -q tests/test_observed_behavior.py::test_error_response_contract`.

### P1-10 — Protocolo de ferramentas baseado em parsing fragil de texto

- **Categoria / severidade:** qualidade/manutencao — **LOW**.
- **Arquivo/linhas:** `langgraph-agent-platform/app/main.py:72-96`.
- **Evidencia e reproducao:** prefixos e regex ad hoc decidem ferramentas, argumentos e erros. `send destinatario sem dois-pontos` termina como resposta comum de sucesso, e qualquer evolucao exige editar o mesmo `if` central.
- **Esperado / atual:** esperado chamadas estruturadas com schema de argumentos, validacao e registro extensivel; atualmente o contrato depende de espacos, dois-pontos e ordem de `if`.
- **Impacto:** comportamento surpreendente, baixa extensibilidade e muitos casos de borda.
- **Correcao esperada:** comandos/tool calls tipados, validacao Pydantic por ferramenta e registry com interfaces claras.
- **Demonstracao:** `curl -X POST http://localhost:8000/api/conversations -H "Content-Type: application/json" -d '{"user_id":"ana","agent_id":"assistant-demo","message":"send destino sem separador"}'`.

### P1-11 — Duas fontes de ID no update com uma silenciosamente ignorada

- **Categoria / severidade:** qualidade, desenho de API — **LOW**.
- **Arquivo/linhas:** `langgraph-agent-platform/app/main.py:28-33` e `:192-196`.
- **Evidencia e reproducao:** `AgentInput` exige `id`, mas a rota sobrescreve esse valor pelo path. Enviar body `id="ignored"` para `/assistant-demo` retorna sucesso sem avisar a divergencia.
- **Esperado / atual:** esperado remover o ID do DTO de update ou rejeitar mismatch; atualmente o cliente nao sabe qual campo e autoritativo.
- **Impacto:** integracoes propensas a erro e documentacao OpenAPI enganosa.
- **Correcao esperada:** DTOs separados para create/update e regra explicita de identidade.
- **Demonstracao:** `test_agent_replacement_contract` envia `id="ignored"` e observa a substituicao de `assistant-demo`.

## Projeto 2 — Controle de presença no polo

### P2-01 — Controle pessoal permite ler, alterar e remover dados de outra pessoa

- **Categoria / severidade:** segurança, Broken Access Control/IDOR — **HIGH**.
- **Arquivo/linhas:** `polo-visits/backend/app/adapters/http/api.py:20-50`; `app/application/attendance_service.py:28-39`.
- **Evidência e reprodução:** `X-User` é obrigatório, mas ignorado. Com `X-User: ana`, use `user_id=bruno` no GET, PUT ou DELETE para consultar, sobrescrever ou apagar marcações de Bruno.
- **Esperado / atual:** esperado derivar o proprietário de uma identidade autenticada; atualmente o cliente escolhe o usuário-alvo.
- **Impacto:** vazamento e adulteração de dados pessoais de presença.
- **Correção esperada:** autenticação real, autorização no caso de uso e repositório escopado ao principal/tenant.
- **Demonstração:** `tests/test_observed_behavior.py::test_header_identity_does_not_control_requested_user`.

### P2-02 — Visão gerencial exposta sem papel ou vínculo com a equipe

- **Categoria / severidade:** segurança, autorização funcional — **HIGH**.
- **Arquivo/linhas:** `polo-visits/backend/app/adapters/http/api.py:52-58`; `app/application/attendance_service.py:41-66`.
- **Evidência e reprodução:** envie `X-User: outsider` com `manager_id=ana`; a resposta contém Bruno, Carla, Diego, totais e dias individuais.
- **Esperado / atual:** esperado validar identidade, papel de gestor e escopo organizacional; atualmente `manager_id` é autodeclarado.
- **Impacto:** exposição em massa de dados da equipe e inferência de rotina presencial.
- **Correção esperada:** política de autorização centralizada, identidade confiável e minimização do retorno.
- **Demonstração:** `tests/test_observed_behavior.py::test_manager_view_is_exposed_to_a_different_x_user`.

### P2-03 — XSS armazenado nas observações

- **Categoria / severidade:** segurança web — **HIGH**.
- **Arquivo/linhas:** `polo-visits/backend/app/adapters/http/api.py:8-12`; `polo-visits/frontend/src/App.jsx:81` e `:111`.
- **Evidência e reprodução:** o backend persiste HTML livre e o frontend usa `dangerouslySetInnerHTML` tanto no editor pessoal quanto no detalhe do gestor. Uma nota como `<img src=x onerror=alert(1)>` vira elemento executável.
- **Esperado / atual:** esperado renderizar notas como texto ou sanitizar com política rigorosa; atualmente entrada persistida é inserida diretamente no DOM.
- **Impacto:** execução de script na origem da aplicação para o próprio usuário e para gestores que consultem a equipe.
- **Correção esperada:** remover os sinks HTML, validar limites no backend e adicionar CSP como defesa adicional.
- **Demonstração:** `src/App.test.jsx`, teste “caracteriza a injeção deliberada de HTML”.

### P2-04 — Correções de presença destroem o histórico sem trilha de auditoria

- **Categoria / severidade:** integridade e auditabilidade — **MEDIUM**.
- **Arquivo/linhas:** `polo-visits/backend/app/adapters/persistence/sqlite.py:41-73`.
- **Evidência e reprodução:** o upsert sobrescreve status/notas do mesmo dia e o DELETE remove definitivamente o registro; não há evento, versão, autor ou motivo da correção.
- **Esperado / atual:** esperado preservar histórico de alterações relevante para relatórios gerenciais; atualmente um registro pode ser reescrito ou apagado sem vestígio.
- **Impacto:** relatórios não auditáveis, dificuldade de investigar erros e possibilidade de manipulação retroativa.
- **Correção esperada:** histórico append-only ou tabela de auditoria com ator, data, valor anterior, novo valor e motivo; restringir alterações fora da janela permitida.
- **Demonstração:** marque, altere e remova a mesma data e consulte diretamente o banco: apenas o último estado — ou nenhum — permanece.

### P2-05 — Data, mês, status, usuário e notas não têm invariantes de domínio

- **Categoria / severidade:** segurança/qualidade, validação — **MEDIUM**.
- **Arquivo/linhas:** `polo-visits/backend/app/adapters/http/api.py:8-12`; `app/domain/models.py:8-13`; `app/application/attendance_service.py:33-35`.
- **Evidência e reprodução:** a API aceita `amanha-talvez`, `talvez-presente`, usuário inexistente e notas sem limite.
- **Esperado / atual:** esperado data ISO válida, mês coerente, enum de status, usuário conhecido e limites de texto; atualmente todos são strings livres.
- **Impacto:** registros impossíveis, contagens inconsistentes e crescimento descontrolado do banco.
- **Correção esperada:** value objects/tipos de domínio, validação Pydantic e constraints equivalentes no SQLite.
- **Demonstração:** `tests/test_observed_behavior.py::test_payload_keeps_unvalidated_status_date_and_notes`.

### P2-06 — CORS permite qualquer origem com credenciais

- **Categoria / severidade:** segurança de configuração web — **MEDIUM**.
- **Arquivo/linhas:** `polo-visits/backend/app/main.py:9-16`.
- **Evidência e reprodução:** origens, métodos e headers usam wildcard com credenciais; o preflight reflete `https://untrusted.example`.
- **Esperado / atual:** esperado allowlist por ambiente e somente métodos/headers necessários; atualmente qualquer site pode chamar e ler a API pelo navegador.
- **Impacto:** amplia os efeitos da ausência de autenticação e de futuras credenciais baseadas em navegador.
- **Correção esperada:** allowlist estrita e teste negativo de preflight.
- **Demonstração:** `tests/test_observed_behavior.py::test_browser_preflight_contract_remains_permissive`.

### P2-07 — SQLite global síncrono é compartilhado por endpoints assíncronos

- **Categoria / severidade:** arquitetura, concorrência e persistência — **MEDIUM**.
- **Arquivo/linhas:** `polo-visits/backend/app/adapters/persistence/sqlite.py:10-13`; `app/main.py:18-20`.
- **Evidência e reprodução:** uma conexão com `check_same_thread=False` é compartilhada por toda a aplicação; execute/commit/leitura não possuem unidade de trabalho nem lock.
- **Esperado / atual:** esperado conexão por request/unidade de trabalho e limites transacionais claros; atualmente requisições concorrentes compartilham estado e bloqueiam o event loop.
- **Impacto:** contenção, respostas intercaladas, falhas de lock e baixa escalabilidade.
- **Correção esperada:** sessões injetadas por request, transações no caso de uso e I/O assíncrono ou executado fora do event loop.
- **Demonstração:** carga concorrente de PUTs para a mesma pessoa/data e inspeção de erros, respostas e valor final.

### P2-08 — Hexágono estrutural mantém domínio anêmico e formato do SQLite nas portas

- **Categoria / severidade:** arquitetura e manutenção — **MEDIUM**.
- **Arquivo/linhas:** `polo-visits/backend/app/domain/ports.py:1-17`; `app/domain/models.py:8-13`; `app/application/attendance_service.py:7-25`.
- **Evidência e reprodução:** `AttendanceRecord` é `dict[str, Any]`; o serviço conhece chaves do registro e altera dicionários devolvidos pelo adaptador; as invariantes não existem no domínio.
- **Esperado / atual:** esperado que portas troquem entidades/DTOs tipados e que regras pertençam ao núcleo; atualmente uma mudança de schema atravessa adaptador, serviço e HTTP.
- **Impacto:** falhas tardias por `KeyError`, adaptadores incompatíveis e falsa sensação de isolamento arquitetural.
- **Correção esperada:** entidades e value objects, DTOs explícitos e mapeamento nas bordas.
- **Demonstração:** um repositório substituto pode devolver qualquer dicionário sem violar o protocolo declarado.

### P2-09 — URL da API está fixada em localhost

- **Categoria / severidade:** qualidade/configuração — **LOW**.
- **Arquivo/linhas:** `polo-visits/frontend/src/App.jsx:3`.
- **Evidência e reprodução:** o bundle sempre usa `http://localhost:8001`; ao acessar por outra máquina, localhost aponta para o computador do visitante.
- **Impacto:** artefato não portável e topologia de deployment acoplada ao código.
- **Correção esperada:** URL relativa/reverse proxy ou `VITE_API_URL` validada por ambiente.
- **Demonstração:** abrir a interface por hostname remoto e observar as requisições.

### P2-10 — Dependências frontend e builds não são reproduzíveis

- **Categoria / severidade:** qualidade da cadeia de build — **LOW**.
- **Arquivo/linhas:** `polo-visits/frontend/package.json:13-23`; `frontend/Dockerfile:1-8`.
- **Evidência e reprodução:** quase todas as dependências usam `latest`, não há lockfile versionado e o Docker executa `npm install`.
- **Impacto:** instalações futuras podem resolver versões incompatíveis sem mudança no repositório.
- **Correção esperada:** versões/faixas controladas, lockfile versionado e `npm ci`.
- **Demonstração:** o build atual resolveu Vite 8.3.1 e Vitest 5.0.2 dinamicamente.

### P2-11 — Bootstrap do banco depende apenas da contagem de presenças

- **Categoria / severidade:** persistência e manutenção — **LOW**.
- **Arquivo/linhas:** `polo-visits/backend/app/adapters/persistence/sqlite.py:120-147`.
- **Evidência e reprodução:** o seed inteiro só roda quando `attendance` está vazio. Se houver presença e `team_members` estiver vazio/incompleto, a inicialização não restaura a equipe.
- **Impacto:** visão gerencial vazia ou inconsistente após migração/restauração parcial.
- **Correção esperada:** migrações idempotentes e seed independente por conjunto de dados.
- **Demonstração:** mantenha uma presença, apague `team_members`, reinicie e consulte a visão do time.

## Checklist de fluxos que a refatoracao deve preservar

### Plataforma de agentes

- [ ] `GET /health` informa API ativa e modelo simulado.
- [ ] Agente inicial pode ser listado e configuracoes validas podem ser administradas por usuario autorizado.
- [ ] Conversa de texto livre retorna resposta deterministica sem servico externo.
- [ ] Consulta de politica funciona.
- [ ] Continuacao conserva o historico correto da mesma conversa, usuario e agente.
- [ ] Acao de notificacao interrompe como `pending_approval`.
- [ ] Aprovador autorizado pode aprovar e retomar; recusa tambem encerra corretamente.
- [ ] Estado e decisao sobrevivem a reinicio usando persistencia local.
- [ ] Conversas, ferramentas e aprovacoes permanecem isoladas entre usuarios/agentes.

### Controle de presença no polo

- [ ] Interface carrega o calendário e os dados fictícios do perfil selecionado.
- [ ] Meta mensal de 8 dias, realizado, restante e percentual são consistentes.
- [ ] Pessoa autorizada pode marcar presença ou ausência e corrigir uma data.
- [ ] Troca entre Ana e Bruno não mistura nem autoriza operações cruzadas.
- [ ] Aba gerencial exige papel e vínculo real com a equipe.
- [ ] Total, média e progresso de Bruno, Carla e Diego são consistentes.
- [ ] Notas são exibidas como conteúdo inerte no nível pessoal e gerencial.
- [ ] Correções preservam uma trilha de auditoria suficiente.
- [ ] Calendário, API e persistência usam o mesmo contrato de data.
- [ ] Backend, frontend, testes, build e E2E real passam com os comandos documentados.

## Comandos de baseline

```bash
docker build --target test -t agent-platform-test langgraph-agent-platform
docker run --rm agent-platform-test

docker build --target test -t polo-api-test polo-visits/backend
docker run --rm polo-api-test

docker build --target test -t polo-web-test polo-visits/frontend
docker run --rm polo-web-test

docker compose up --build -d
docker compose ps

docker build --target e2e -t polo-web-e2e polo-visits/frontend
docker run --rm --add-host=host.docker.internal:host-gateway polo-web-e2e
```

No baseline, `test_observed_behavior.py` caracteriza autorização, validação e CORS inseguros. Em `App.test.jsx`, o teste de HTML persistido caracteriza o XSS. Depois da correção, esses testes devem ser substituídos ou invertidos para esperar rejeição ou neutralização, sem simplesmente serem apagados.
