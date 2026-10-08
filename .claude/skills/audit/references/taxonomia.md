# Taxonomia de achados

## Tipo

| Tipo | Definição | Pergunta-chave | Exemplo |
| --- | --- | --- | --- |
| **Vulnerabilidade** | Defeito que alguém pode explorar **de propósito** para fazer o que não deveria | "Um usuário mal-intencionado tira proveito disso?" | Mudar o `user_id` e ler dados de outro usuário |
| **Bug** | Defeito que faz o sistema **errar sozinho** no uso normal | "Um usuário comum recebe resultado errado ou perde dados?" | Resposta antiga sobrescreve a tela atual; banco reiniciado no boot |
| **Dívida técnica** | Não erra hoje, mas torna erros prováveis ou correções caras | "Qual bug ou vulnerabilidade concreta isso facilita?" | Regra de negócio duplicada no frontend e no backend |

Os tipos usam a **mesma escala de severidade**, e a severidade define a prioridade. O tipo
explica por que o achado importa e muda a leitura da probabilidade (`severidade.md`, seção 2).

## Categoria

Cada achado recebe **uma categoria principal** e, quando aplicável, um CWE e um item do OWASP
Top 10 (2021) ou do OWASP Top 10 para LLM (2025).

| Código | Categoria | CWE típicos | OWASP |
| --- | --- | --- | --- |
| `SEC-AUTHZ` | Autorização / controle de acesso (IDOR, privilégio, posse de recurso) | CWE-284, 285, 639, 862, 863 | A01 |
| `SEC-AUTHN` | Autenticação e identidade (identidade vinda do cliente, sessão) | CWE-287, 290, 306, 384 | A07 |
| `SEC-INJ` | Injeção (SQL, comando, template, path traversal) | CWE-22, 77, 78, 89, 94 | A03 |
| `SEC-XSS` | Cross-site scripting / renderização insegura | CWE-79, 80 | A03 |
| `SEC-FILE` | Acesso a arquivos e recursos locais | CWE-22, 73, 552 | A01 |
| `SEC-DATA` | Exposição de informação (erros, logs, PII, segredos) | CWE-200, 209, 532, 798 | A02 / A04 |
| `SEC-CONF` | Configuração insegura (CORS, debug, headers, defaults inseguros) | CWE-16, 942, 1188 | A05 |
| `SEC-DEP` | Dependências e cadeia de suprimentos | CWE-1104, 1395 | A06 |
| `SEC-LLM` | Riscos de agentes/LLM (ferramentas excessivas, prompt injection, HITL fraco) | CWE-77, 862 | LLM01, LLM06 (Excessive Agency) |
| `INT-WF` | Integridade de workflow e auditabilidade (aprovações, trilha, idempotência) | CWE-841, 778 | A08 / A09 |
| `INT-VAL` | Validação de entrada e regras de domínio | CWE-20, 1284, 1287 | A04 |
| `CONC` | Concorrência e persistência (race, transação, estado global) | CWE-362, 366, 667 | — |
| `ISO` | Isolamento de estado entre usuários/sessões/tenants | CWE-488, 668 | A01 |
| `ARQ` | Arquitetura e acoplamento (camadas, responsabilidade, testabilidade) | CWE-1047, 1061, 1120 | — |
| `FE` | Frontend (estado, efeitos, acessibilidade, build) | CWE-1021 | — |
| `MNT` | Manutenibilidade (duplicação, código morto, nomes, magic numbers) | CWE-561, 1041, 1106 | — |
| `TEST` | Testes (ausência de cobertura de fluxo crítico, testes que validam o bug) | CWE-1053 | — |

## Regras

- Categoria = **causa-raiz**, não sintoma. Uma identidade aceita do corpo da requisição que
  permite IDOR é `SEC-AUTHN` se a causa é a identidade não confiável. É `SEC-AUTHZ` se a
  identidade é confiável, mas a posse do recurso não é verificada.
- Se dois CWEs se aplicam, liste o mais específico primeiro.
- Achados `ARQ`/`MNT` precisam de **consequência concreta** (bug, risco ou custo mensurável).
  "Não segue Clean Architecture" sozinho não é achado.
