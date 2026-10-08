# Padrões de busca por stack

Use com a ferramenta `Grep` (ripgrep). Um resultado é **candidato**, não achado. Sempre leia o
contexto e passe pelo gate de `verificacao-falsos-positivos.md`.

## Python / FastAPI
| Risco | Padrão (regex) |
| --- | --- |
| Rotas e entradas | `@(app\|router)\.(get\|post\|put\|patch\|delete)` |
| Identidade vinda do cliente | `user_id\|role\|is_admin\|reviewer` em modelos Pydantic de request |
| SQL dinâmico | `execute\(f["']\|execute\(.*\.format\(\|execute\(.*%` |
| Comando/código | `subprocess\|os\.system\|shell=True\|eval\(\|exec\(\|pickle\.loads\|yaml\.load\(` |
| Arquivos | `open\(\|Path\(\|read_text\|read_bytes\|send_file\|FileResponse` |
| Erro exposto | `detail=str\(\|str\(e\)\|traceback\|repr\(e\)` |
| CORS | `CORSMiddleware\|allow_origins\|allow_credentials` |
| Estado global | variáveis em nível de módulo mutadas em handlers (`global `, `dict\(\)` / `\{\}` no topo) |
| SQLite | `check_same_thread\|sqlite3\.connect\|commit\(\)\|isolation_level` |
| Tempo | `datetime\.now\(\)\|date\.today\(\)\|utcnow` |

## LangGraph / agentes
| Risco | Padrão |
| --- | --- |
| Ferramentas | `@tool\|ToolNode\|tools=\|bind_tools\|def .*_tool` |
| HITL | `interrupt\|Command\(resume\|approve\|reject\|pending` |
| Checkpoint/thread | `thread_id\|checkpointer\|MemorySaver\|SqliteSaver\|get_state` |
| Configuração global | `AGENT_CONFIG\|config\[\|settings\.` mutados em rotas |

## JavaScript / React / Vite
| Risco | Padrão |
| --- | --- |
| XSS | `dangerouslySetInnerHTML\|innerHTML\|outerHTML\|document\.write\|href=\{` |
| Código dinâmico | `eval\(\|new Function\|setTimeout\(["']` |
| Armazenamento | `localStorage\|sessionStorage` (identidade/papel no cliente) |
| API | `fetch\(\|axios\|VITE_\|http://localhost` |
| Efeitos | `useEffect\(` (dependências, cancelamento, corrida) |
| Papel na UI | `role\|isManager\|admin` usados para decidir acesso apenas no cliente |

## Docker / configuração
| Risco | Padrão |
| --- | --- |
| Root | ausência de `USER` no Dockerfile |
| Dev em produção | `--reload\|npm run dev\|vite --host\|DEBUG=1` |
| Segredos | `SECRET\|TOKEN\|PASSWORD\|API_KEY` em arquivos versionados |
| Pin | `requirements*.txt` sem `==`; `package.json` com `^`/`*` sem lockfile |

## Comandos úteis (somente leitura)
```bash
git rev-parse --short HEAD && git status --short
python -m pytest -q            # baseline (não use --fix ou plugins que reescrevem)
npm test -- --run              # vitest em modo não interativo
```
