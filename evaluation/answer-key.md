# Gabarito privado — baseline legado

Este arquivo pertence a avaliacao do mantenedor. Nao deve ser fornecido a skill durante a execucao cega. As linhas abaixo correspondem ao baseline criado em 2026-09-27; se o legado for alterado antes da avaliacao, atualize as referencias.

## Cobertura

| Projeto | CRITICAL | HIGH | MEDIUM | LOW | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Plataforma de agentes | 1 | 4 | 4 | 2 | 11 |
| Gestao de idas ao polo | 1 | 4 | 5 | 3 | 13 |
| **Total** | **2** | **8** | **9** | **5** | **24** |

Categorias cobertas: autorizacao, injecao, acesso a arquivos, XSS, isolamento de estado, validacao, integridade de regras, concorrencia/persistencia, exposicao de informacao, acoplamento arquitetural, configuracao web, frontend e manutencao.

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

## Projeto 2 — Gestao de idas ao polo

### P2-01 — Injecao SQL na pesquisa de visitas

- **Categoria / severidade:** seguranca, injecao — **CRITICAL**.
- **Arquivo/linhas:** `polo-visits/backend/app/main.py:51-57`.
- **Evidencia e reproducao:** `user_id` e `q` sao interpolados em SQL. Pesquisar por `inexistente%' OR 1=1 --` retorna registros de Ana e Bruno.
- **Esperado / atual:** esperado parametros bind para todos os valores e agrupamento logico explicito; atualmente entrada altera a estrutura da query.
- **Impacto:** leitura arbitraria do banco e possibilidade de ampliar impacto conforme driver/permissoes evoluam.
- **Correcao esperada:** query parametrizada/repository, escaping nunca como substituto, testes com metacaracteres e principio do menor privilegio.
- **Demonstracao:** `docker run --rm polo-api-test python -m pytest -q tests/test_observed_behavior.py::test_search_contract_with_sql_metacharacters`.

### P2-02 — Consultas e resumo aceitam identidade de outra pessoa

- **Categoria / severidade:** seguranca, autorizacao/IDOR — **HIGH**.
- **Arquivo/linhas:** `polo-visits/backend/app/main.py:45-63` e `:155-166`.
- **Evidencia e reproducao:** `X-User` e recebido, mas ignorado; `user_id` da query seleciona qualquer pessoa. Use header `ana` com `user_id=bruno` nas duas rotas.
- **Esperado / atual:** esperado derivar o usuario da identidade autenticada ou exigir papel administrativo; atualmente o chamador escolhe o dono consultado.
- **Impacto:** vazamento de agenda, historico, finalidade, notas e resumo de terceiros.
- **Correcao esperada:** autenticacao, autorizacao centralizada e consultas sempre escopadas ao principal/tenant.
- **Demonstracao:** `docker run --rm polo-api-test python -m pytest -q tests/test_observed_behavior.py::test_identity_contract_across_records`.

### P2-03 — Alteracao e cancelamento sem verificar proprietario

- **Categoria / severidade:** seguranca, autorizacao/IDOR — **HIGH**.
- **Arquivo/linhas:** `polo-visits/backend/app/main.py:103-152`.
- **Evidencia e reproducao:** PUT e DELETE buscam somente pelo ID; o header nao participa da query nem de uma regra. Ana altera e cancela o registro inicial de Bruno.
- **Esperado / atual:** esperado localizar por `id + owner/tenant` e autorizar a transicao; atualmente qualquer ID existente pode ser modificado.
- **Impacto:** adulteracao ou cancelamento de visitas alheias.
- **Correcao esperada:** policy/dependency de autorizacao, repositorio escopado, 404/403 coerente e testes negativos por usuario.
- **Demonstracao:** `test_identity_contract_across_records` executa PUT e DELETE no registro de Bruno com `X-User: ana`.

### P2-04 — Criacao permite personificar outro usuario

- **Categoria / severidade:** seguranca, integridade de identidade — **HIGH**.
- **Arquivo/linhas:** `polo-visits/backend/app/main.py:66-96`.
- **Evidencia e reproducao:** a linha 85 persiste `body.user_id`; `x_user` nao e comparado. Envie header Ana e body `user_id=bruno`.
- **Esperado / atual:** esperado dono derivado da identidade autenticada; atualmente o cliente escolhe para quem cria o agendamento.
- **Impacto:** spam, fraude de agenda e registros falsos em nome de terceiros.
- **Correcao esperada:** retirar `user_id` do payload comum, usar principal autenticado e reservar criacao delegada a papel explicito.
- **Demonstracao:** `docker run --rm polo-api-test python -m pytest -q tests/test_observed_behavior.py::test_payload_contract_keeps_supplied_values`.

### P2-05 — XSS armazenado nas observacoes

- **Categoria / severidade:** seguranca web — **HIGH**.
- **Arquivo/linhas:** `polo-visits/backend/app/main.py:10-17`, `:77-95`; `polo-visits/frontend/src/App.jsx:209`.
- **Evidencia e reproducao:** backend aceita HTML sem regra e frontend injeta `notes` com `dangerouslySetInnerHTML`. O payload `<img src=x onerror=alert(1)>` e persistido e vira atributo executavel no DOM do navegador.
- **Esperado / atual:** esperado renderizar notas como texto ou sanitizar com politica rigorosa se HTML for requisito; atualmente conteudo armazenado entra diretamente no DOM.
- **Impacto:** execucao de script na origem do frontend, permitindo agir como o usuario e ler dados disponiveis a pagina.
- **Correcao esperada:** remover `dangerouslySetInnerHTML`, renderizar `{visit.notes}`, validar tamanho/conteudo no backend e adotar CSP como defesa adicional.
- **Demonstracao:** backend em `test_payload_contract_keeps_supplied_values`; frontend com `docker run --rm polo-web-test npm test -- --run src/App.test.jsx`.

### P2-06 — Datas, horarios, acompanhantes e status sem tipos/regras de dominio

- **Categoria / severidade:** seguranca/qualidade, validacao — **MEDIUM**.
- **Arquivo/linhas:** `polo-visits/backend/app/main.py:10-27`, `:68-75` e `:121-130`.
- **Evidencia e reproducao:** data/horario/status sao strings livres, acompanhantes aceita negativos, finalidade nem e checada no `if`; a API persiste `amanha-talvez`, `25:90`, `-4` e status arbitrario.
- **Esperado / atual:** esperado `date`, `time`, enum de status, limites de acompanhantes, strings nao vazias e regras de antecedencia; atualmente apenas presenca parcial e tipo inteiro sao verificados.
- **Impacto:** registros impossiveis, resumos com chaves inesperadas e regras facilmente contornadas.
- **Correcao esperada:** DTOs tipados/restritos, validadores de dominio compartilhados e transicoes de estado controladas no servidor.
- **Demonstracao:** `test_payload_contract_keeps_supplied_values` e `test_update_contract_for_capacity_and_status`.

### P2-07 — Regra de capacidade so existe na criacao

- **Categoria / severidade:** arquitetura/integridade de regra — **MEDIUM**.
- **Arquivo/linhas:** `polo-visits/backend/app/main.py:70-75` versus `:103-137`.
- **Evidencia e reproducao:** POST limita cinco visitas agendadas por data; PUT move uma sexta visita para a mesma data sem repetir a verificacao. O teste termina com seis registros.
- **Esperado / atual:** esperado uma politica unica aplicada atomicamente em criacao e reagendamento; atualmente a regra esta presa a um endpoint.
- **Impacto:** overbooking e comportamento inconsistente conforme o caminho usado.
- **Correcao esperada:** service/use case transacional reutilizado por create/update e constraint/estrategia contra corrida concorrente.
- **Demonstracao:** `docker run --rm polo-api-test python -m pytest -q tests/test_observed_behavior.py::test_update_contract_for_capacity_and_status`.

### P2-08 — Rotas concentram regra, SQL e transacao sobre conexao global

- **Categoria / severidade:** arquitetura e concorrencia — **MEDIUM**.
- **Arquivo/linhas:** `polo-visits/backend/app/main.py:45-166`; `app/database.py:7-10`.
- **Evidencia e reproducao:** cada endpoint monta/roda SQL, valida regra, faz commit e formata retorno; todos usam o singleton SQLite com `check_same_thread=False` em funcoes async, sem unidade de trabalho.
- **Esperado / atual:** esperado separar handler HTTP, casos de uso/regras e repositorio/transacoes; atualmente testes, concorrencia e mudanca de persistencia ficam acoplados ao modulo de rotas.
- **Impacto:** duplicacao/omissao de regras (como capacidade), bloqueio do event loop, commits parciais e alto custo de manutencao.
- **Correcao esperada:** camadas leves orientadas ao dominio, dependencias injetadas, sessao por request e transacoes nos casos de uso.
- **Demonstracao:** `rg -n "database\.connection|commit\(|SELECT |INSERT |UPDATE " polo-visits/backend/app/main.py` lista o acesso a dados em todos os handlers.

### P2-09 — CORS permite qualquer origem com credenciais

- **Categoria / severidade:** seguranca de configuracao web — **MEDIUM**.
- **Arquivo/linhas:** `polo-visits/backend/app/main.py:30-37`.
- **Evidencia e reproducao:** wildcard de origens/metodos/headers com credenciais faz o preflight refletir `https://untrusted.example` e autorizar DELETE/X-User.
- **Esperado / atual:** esperado allowlist de origens conhecidas, metodos/headers minimos e politica coerente de credenciais; atualmente qualquer site recebe permissao CORS.
- **Impacto:** amplia ataques cross-origin quando autenticacao por cookie/token for adicionada e permite leitura pelo navegador de origem nao confiavel.
- **Correcao esperada:** configuracao por ambiente com allowlist estrita e testes de preflight negativo.
- **Demonstracao:** `docker run --rm polo-api-test python -m pytest -q tests/test_observed_behavior.py::test_browser_preflight_contract`.

### P2-10 — Componente React concentra a aplicacao inteira

- **Categoria / severidade:** arquitetura frontend — **MEDIUM**.
- **Arquivo/linhas:** `polo-visits/frontend/src/App.jsx:14-223`.
- **Evidencia e reproducao:** `App` controla identidade, busca, resumo, formulario, validacao, POST/PUT/DELETE, edicao, confirmacao e toda a renderizacao em um unico componente de mais de 200 linhas.
- **Esperado / atual:** esperado separar cliente HTTP/hooks, formulario, resumo e lista/cards com limites testaveis; atualmente qualquer mudanca de fluxo toca o mesmo estado e componente.
- **Impacto:** testes complexos, re-renderizacao ampla, duplicacao futura e maior risco de regressao.
- **Correcao esperada:** extrair API client, hooks/use cases e componentes focados, mantendo estado no menor ancestral necessario.
- **Demonstracao:** `rg -n "function |fetch\(|return \(" polo-visits/frontend/src/App.jsx` e `npm test` mostram que os fluxos so podem ser montados pelo componente inteiro.

### P2-11 — URL da API fixada em localhost

- **Categoria / severidade:** qualidade/configuracao — **LOW**.
- **Arquivo/linhas:** `polo-visits/frontend/src/App.jsx:3`.
- **Evidencia e reproducao:** o bundle sempre chama `http://localhost:8001`; ao servir de outra maquina/origem, `localhost` aponta para o computador do visitante.
- **Esperado / atual:** esperado URL relativa/proxy ou variavel `VITE_API_URL` por ambiente; atualmente deployment fora da topologia local quebra.
- **Impacto:** artefato nao portavel e configuracao de CORS desnecessariamente acoplada.
- **Correcao esperada:** configuracao validada no build/runtime, default relativo e documentacao de ambientes.
- **Demonstracao:** `rg -n "localhost:8001" polo-visits/frontend/src polo-visits/frontend/dist` apos `npm run build`.

### P2-12 — Cards usam indice como chave React

- **Categoria / severidade:** qualidade frontend — **LOW**.
- **Arquivo/linhas:** `polo-visits/frontend/src/App.jsx:199-200`.
- **Evidencia e reproducao:** a lista ordenada/filtrada usa `key={index}` embora cada visita tenha `id`; busca, criacao ou cancelamento muda indices e permite reutilizacao do DOM para outro registro.
- **Esperado / atual:** esperado `key={visit.id}` estavel; atualmente identidade visual depende da posicao.
- **Impacto:** estado local/foco de componentes futuros pode migrar para o card errado e gerar bugs sutis.
- **Correcao esperada:** usar ID persistente e testar reordenacao/remocao.
- **Demonstracao:** evidencia estatica na linha 200; renderizar lista, inserir item no inicio e inspecionar reutilizacao de nos no React DevTools.

### P2-13 — Dependencias frontend nao sao reproduziveis

- **Categoria / severidade:** qualidade da cadeia de build — **LOW**.
- **Arquivo/linhas:** `polo-visits/frontend/package.json:12-23`.
- **Evidencia e reproducao:** quase todas as dependencias usam `latest` e nao ha lockfile versionado; uma instalacao futura pode trazer majors incompatíveis e alterar o resultado sem mudanca do repositorio.
- **Esperado / atual:** esperado faixas controladas e lockfile versionado; atualmente o baseline depende do momento do `npm install`.
- **Impacto:** builds/testes nao deterministas e risco de supply-chain/compatibilidade maior.
- **Correcao esperada:** fixar versoes/faixas revisadas, manter `package-lock.json` e usar `npm ci` em CI/Docker.
- **Demonstracao:** `rg -n 'latest' polo-visits/frontend/package.json`; remover lock/node_modules e instalar em datas diferentes pode resolver versoes distintas.

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

### Gestao de idas ao polo

- [ ] Interface carrega e mostra dados ficticios do perfil selecionado.
- [ ] Lista e pesquisa de visitas funcionam para o usuario autorizado.
- [ ] Resumo reflete agendadas, concluidas, canceladas e total.
- [ ] Criacao valida e agenda uma visita futura.
- [ ] Edicao valida altera data, horario, finalidade, notas e acompanhantes permitidos.
- [ ] Cancelamento valido muda o status e o resumo.
- [ ] Regra de capacidade continua aplicada a criacao e reagendamento.
- [ ] Troca entre Ana e Bruno nao mistura dados nem autoriza operacoes cruzadas.
- [ ] Notas sao exibidas como conteudo inerte.
- [ ] Backend, frontend, testes e build iniciam com os comandos documentados.

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
```

No baseline, os testes de `test_observed_behavior.py` e o segundo teste de `App.test.jsx` caracterizam comportamentos inseguros atuais. Depois da correcao, eles devem ser substituidos ou invertidos para esperar rejeicao/neutralizacao, sem simplesmente serem apagados.
