---
name: audit
description: Audita uma base de código (segurança, arquitetura e qualidade) SEM alterar a implementação e produz um relatório em pt-BR com achados classificados por criticidade (CRITICAL, HIGH, MEDIUM, LOW, INFO), evidência, arquivo:linha, impacto, recomendação e estratégia de validação. Use quando o usuário pedir "auditoria", "audit", "revisão de segurança", "análise de vulnerabilidades", "relatório de achados" ou "avaliar riscos" de um projeto ou diretório.
allowed-tools: Read, Grep, Glob, Bash, Write
---

# Auditoria de código (`audit`)

Skill reutilizável e independente de projeto para auditar código e configuração, classificar
problemas por criticidade e entregar um relatório verificável e enxuto. Inspirada em:
- `trailofbits/skills`: *audit-context-building*, *insecure-defaults*, *fp-check*, *differential-review*;
- `anthropics/claude-code-security-review`: nota de confiança, exclusões fixas e cenário de exploração;
- OWASP Top 10 / ASVS / LLM Top 10, taxonomia CWE e CVSS v3.1.

## Quando usar

- Pedido explícito de auditoria, revisão de segurança, análise de riscos ou relatório de achados.
- Antes de uma refatoração, para gerar o escopo que será aprovado por um humano.
- Avaliação de um projeto legado ou desconhecido.

## Quando NÃO usar

- Para corrigir código. Esta skill **não edita implementação**. Correções são outra
  skill/etapa.
- Para revisar apenas um diff de PR pequeno (prefira uma revisão de código focada).

## Regras invioláveis

1. **Somente leitura sobre a implementação.** O único arquivo que você escreve é o relatório
   (e, opcionalmente, artefatos de evidência dentro da pasta de relatórios). Nunca use `Edit`
   ou `Write` em arquivos do projeto auditado. Não rode comandos que mutem o repositório
   (`git commit`, `git checkout --`, formatadores com `--fix`, migrações, `npm audit fix`).
2. **Sem evidência, sem achado.** Cada achado cita `arquivo:linha` reais, lidos por você, e
   uma evidência reproduzível (trecho de código, comando, requisição ou teste). Suposições vão
   para a seção "Observações", nunca para a lista de achados.
3. **Consolide por causa-raiz.** Um mesmo defeito que aparece em N lugares é **um** achado
   com N localizações. Duplicação artificial é penalizada.
4. **Severidade justificada.** Use a matriz em `references/severidade.md`. Toda severidade
   traz uma justificativa de uma ou duas frases (impacto × probabilidade × alcance).
5. **Não leia material de avaliação.** Ignore gabaritos, `answer-key`, `evaluation/` ou
   arquivos que contenham respostas esperadas da auditoria.
6. **Ambiente local apenas.** Reproduções só contra serviços locais/de teste. Nunca contra
   produção ou terceiros.

## Fluxo de trabalho

Siga as fases em ordem. Marque cada uma como concluída antes de avançar.

### Fase 0 — Escopo e baseline
- Defina o alvo (diretório) e o arquivo de saída. Padrão: `reports/audit-<projeto>.md` na raiz
  do repositório.
- Registre o commit atual (`git rev-parse --short HEAD`) e o estado (`git status --short`).
- Se houver testes, execute-os **sem alterar nada** e anote o resultado como baseline
  (comando, passou/falhou, contagem). Se a execução exigir instalar dependências e isso não
  for possível, registre o motivo.

### Fase 1 — Construção de contexto (antes de caçar bugs)
- Rode `scripts/inventario.py <alvo>` (opcional) para listar stack, arquivos, LOC e manifestos.
- Leia README, manifestos de dependência, Dockerfiles/compose, configuração e pontos de entrada.
- Mapeie: **entradas** (rotas HTTP, CLI, filas, ferramentas de agente, UI), **ativos**
  (dados, arquivos, segredos), **persistência**, **identidade/autorização** e
  **fronteiras de confiança** (onde dado não confiável entra e onde é consumido).
- Registre o mapa em **uma linha** na "Superfície" do relatório. O mapa detalhado é
  material de trabalho e não entra no relatório.

### Fase 2 — Caça sistemática
Percorra os checklists, do mais crítico ao menos crítico:
1. `references/checklist-seguranca.md` (OWASP/CWE, incluindo riscos de agentes LLM).
2. `references/checklist-arquitetura-qualidade.md` (acoplamento, concorrência, validação,
   testes, manutenção, frontend).
3. `references/padroes-por-stack.md` (padrões de busca `grep` por linguagem/framework).

Para cada fonte de entrada não confiável, siga o dado até o *sink* (arquivo, SQL, HTML,
shell, ferramenta, resposta HTTP). Para cada operação sensível, pergunte: **quem pode chamar,
sobre qual recurso, e isso é verificado no servidor?**

### Fase 3 — Verificação (gate anti falso-positivo)
Para cada candidato, aplique `references/verificacao-falsos-positivos.md`:
- O caminho é alcançável a partir de uma entrada real?
- Há mitigação em outra camada (middleware, proxy, validação de schema, framework)?
- Consegue reproduzir (teste, `curl`, leitura de fluxo completo)? Se sim, registre o passo a passo.
- Aplique as **exclusões fixas** (DoS, rate limiting, validação sem impacto etc.).
- Resultado: **Confirmado** (≥ 0,9), **Provável** (0,8–0,9), **Hipótese** (0,7–0,8, vai para
  "Observações") ou **Descartado** (< 0,7, não entra).

### Fase 4 — Classificação
- Atribua severidade com `references/severidade.md` e categoria com
  `references/taxonomia.md` (categoria + CWE quando aplicável).
- Classifique o **tipo** (`references/taxonomia.md`): **Vulnerabilidade** (alguém pode explorar
  de propósito), **Bug** (o sistema erra sozinho no uso normal) ou **Dívida técnica** (não
  erra hoje, mas torna erros prováveis ou correções caras). Um defeito pode ser os dois
  primeiros: use o tipo do maior risco e cite o outro na justificativa.
- Consolide achados com a mesma causa-raiz. Consolidar exige **a mesma correção**. Defeitos
  com correções diferentes, como falta de autorização e falta de trilha de auditoria, são achados separados.
- **Gate de cobertura:** antes de escrever, liste (nas suas notas, não no relatório) todos os
  candidatos levantados na Fase 2 e o destino de cada um: achado, observação ou descartado
  com a regra. Nenhum candidato confirmado pode ficar sem destino. Percorra de novo as
  seções do checklist de segurança (A–I) e de arquitetura (A–H) e confirme que cada uma foi
  considerada.
- Ordene: severidade (CRITICAL → LOW), depois confiança, depois alcance.
- IDs pela severidade, para que o leitor saiba a gravidade só pelo ID: `CRIT-01`, `HIGH-01`,
  `MED-01`, `LOW-01`, com numeração reiniciada a cada nível. INFO não recebe ID.
- O título diz **o problema e onde ele está** em linguagem simples
  (ex.: "Qualquer usuário lê o histórico de conversa de outro"), sem jargão nem nome de variável.

### Fase 5 — Relatório
- Preencha `templates/relatorio-auditoria.md`; cada achado segue `templates/achado.md`.
- **Cobertura vem antes de concisão.** Não existe limite de linhas para o relatório inteiro,
  e **nunca omita, funda ou rebaixe um achado para economizar espaço**. A concisão é por achado:
  - CRITICAL/HIGH: formato completo, até ~35 linhas.
  - MEDIUM: formato completo, até ~25 linhas.
  - LOW: **formato compacto** de `templates/achado.md`, até ~12 linhas.
  - Diga cada fato **uma vez**. Não repita a justificativa no impacto nem o impacto no
    esperado × atual, e não crie tabela-resumo dos achados (os títulos já cumprem esse papel).
  - Trecho de evidência com no máximo 8 linhas. Se houver vários locais, cite os demais em
    "Local" sem colar código.
  - Achados que dependem de outro citam a dependência em meia frase ("corrigir após `HIGH-01`").
    Não repita a explicação.
- **"O que fazer"** é a parte mais importante para quem vai corrigir. Escreva passos
  numerados e acionáveis (o que mudar, em qual arquivo/função e por qual mecanismo) e, quando
  ajudar, um esboço de código de até 10 linhas. Evite recomendações genéricas como "validar a
  entrada" ou "adicionar autorização" sem dizer como.
- INFO, hipóteses e descartados vão juntos em "Observações", uma linha cada e sem limite de itens.
  Todo descartado cita a regra que o descartou (exclusão fixa, mitigação ou confiança < 0,7).
- **Pare aqui**: não inicie correções.

## Níveis de criticidade (resumo)

| Nível | Significado curto | Prazo sugerido |
| --- | --- | --- |
| **CRITICAL** | Comprometimento direto e explorável sem pré-condições relevantes (RCE, leitura/escrita arbitrária de arquivos, bypass total de autenticação, vazamento massivo). | Bloqueia release; corrigir imediatamente. |
| **HIGH** | Quebra de controle de acesso, integridade ou confidencialidade com pré-condição baixa (IDOR, XSS armazenado, aprovação sem autorização, perda de dados). | Corrigir antes do próximo release. |
| **MEDIUM** | Impacto limitado ou exige pré-condições; defeitos de arquitetura que geram bugs reais (race condition, validação ausente, vazamento de erro interno, acoplamento que impede testar). | Planejar na sprint corrente/seguinte. |
| **LOW** | Defesa em profundidade, higiene, manutenção (headers ausentes, código morto, nomes enganosos, configuração frágil). | Backlog. |
| **INFO** | Observação sem risco direto; boa prática ou contexto. Não conta no placar. | Opcional. |

Detalhes, critérios de desempate e exemplos: `references/severidade.md`.

## Arquivos da skill

| Arquivo | Uso |
| --- | --- |
| `references/severidade.md` | Matriz impacto × probabilidade, critérios por nível, ajustes e exemplos. |
| `references/taxonomia.md` | Categorias de achados e mapeamento CWE/OWASP. |
| `references/checklist-seguranca.md` | Checklist de segurança (web, API, arquivos, LLM/agentes). |
| `references/checklist-arquitetura-qualidade.md` | Checklist de arquitetura, concorrência, testes e manutenção. |
| `references/padroes-por-stack.md` | Padrões de busca por stack (Python/FastAPI, JS/React, SQL, Docker). |
| `references/verificacao-falsos-positivos.md` | Gate de verificação e níveis de confiança. |
| `templates/relatorio-auditoria.md` | Esqueleto do relatório final. |
| `templates/achado.md` | Formato obrigatório de cada achado. |
| `scripts/inventario.py` | Inventário somente-leitura (stack, LOC, manifestos, rotas). |

## Critério de pronto

- [ ] Nenhum arquivo do projeto auditado foi modificado (`git status` igual ao início).
- [ ] Todo achado tem ID, título, severidade + justificativa, categoria/CWE, `arquivo:linha`,
      tipo, evidência/reprodução, esperado × atual, impacto, "O que fazer" com passos concretos e validação.
- [ ] Nenhum achado duplicado por causa-raiz e nenhuma informação repetida entre seções.
- [ ] Gate de cobertura cumprido: nenhum candidato confirmado foi omitido, fundido ou rebaixado por espaço.
- [ ] Achados dentro do orçamento de linhas do seu nível; LOW no formato compacto.
- [ ] Linhas citadas conferem com o código atual.
- [ ] Relatório salvo no caminho combinado e resumo apresentado ao usuário.
