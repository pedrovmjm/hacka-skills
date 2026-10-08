# Matriz de severidade

A severidade expressa **risco**: impacto × probabilidade de exploração × alcance.
Ela não depende de quão fácil é corrigir. A matriz se baseia no CVSS v3.1 e na
OWASP Risk Rating Methodology, simplificadas para auditoria de código.

## 1. Avalie o impacto (I)

| Nota | Impacto | Exemplos |
| --- | --- | --- |
| 4 — Severo | Controle do sistema ou de todos os dados | RCE, leitura/escrita arbitrária de arquivos, bypass total de autenticação, dump do banco, segredos expostos |
| 3 — Alto | Dados ou ações de **outros usuários** | IDOR, escalonamento de privilégio, XSS armazenado, aprovação/execução não autorizada, adulteração de registros |
| 2 — Moderado | Dano limitado ou indireto | Vazamento de stack trace/informação interna, condição de corrida com dado inconsistente, DoS localizado, validação ausente que corrompe dados do próprio usuário |
| 1 — Baixo | Higiene / defesa em profundidade | Header ausente, log ruidoso, código morto, nomes enganosos, dependência desatualizada sem exploit conhecido |

## 2. Avalie a probabilidade (P)

A probabilidade tem leitura diferente conforme o **tipo** do achado (ver `taxonomia.md`).

| Nota | Vulnerabilidade: chance de alguém **conseguir explorar** | Bug: chance de **acontecer sozinho** no uso normal |
| --- | --- | --- |
| 3 — Alta | Explorável remotamente, sem autenticação ou com qualquer usuário, sem interação da vítima, reprodução trivial | Acontece no fluxo principal, com uso comum (ex.: toda troca rápida de mês) |
| 2 — Média | Exige conta válida, conhecimento de um identificador, interação da vítima ou condição de tempo | Exige uma condição de dados ou de tempo plausível (ex.: virada de mês, tabela vazia) |
| 1 — Baixa | Exige acesso privilegiado, configuração rara, ou cadeia com outro defeito | Raro: falha de infraestrutura no meio da operação, ambiente incomum |

Para **Dívida técnica**, avalie a probabilidade de ela gerar um bug ou uma vulnerabilidade
concreta. Sem esse caminho, o item é INFO.

## 3. Combine

| I \ P | 3 — Alta | 2 — Média | 1 — Baixa |
| --- | --- | --- | --- |
| **4 — Severo** | **CRITICAL** | **CRITICAL** / HIGH* | HIGH |
| **3 — Alto** | **HIGH** | **HIGH** | MEDIUM |
| **2 — Moderado** | **MEDIUM** | **MEDIUM** | LOW |
| **1 — Baixo** | **LOW** | **LOW** | LOW / INFO |

\* Use CRITICAL quando a pré-condição for trivial (ex.: um UUID que aparece na própria resposta).
Use HIGH quando ela exigir algo realmente difícil de obter.

## 4. Ajustes (no máximo um nível para cima ou para baixo, sempre justificado)

- **+1** se o alcance atravessa uma fronteira que a nota de impacto **ainda não considerou**, por exemplo
  um defeito de aplicação que alcança o host ou outros tenants. **Não aplique** "afeta todos os
  usuários" a um IDOR/autorização: o impacto 3 já significa "dados de outros usuários".
  Contar o mesmo fator na nota e no ajuste infla a severidade.
- **+1** se é explorável por uma ferramenta de agente LLM movida por texto do usuário (prompt injection amplifica a probabilidade).
- **Regra de teto:** CRITICAL exige impacto 4 (controle do sistema, de arquivos/segredos ou do
  banco inteiro). Um impacto 3 com ajuste chega no máximo a HIGH.
- **−1** se existe mitigação parcial real em outra camada (verificada, não presumida).
- **−1** se o componente está claramente fora de uso, como código morto não alcançável. Avalie se o achado não deveria ser apenas INFO.

## 5. Definições operacionais

### CRITICAL
Comprometimento direto, explorável agora, com pouca ou nenhuma pré-condição.
Bloqueia release. Exemplos: path traversal/leitura arbitrária via endpoint público,
injeção de comando/SQL com controle total, credenciais administrativas hard-coded em uso,
desserialização insegura de entrada externa.

### HIGH
Viola controle de acesso, integridade ou confidencialidade de dados de terceiros, com
pré-condição baixa. Exemplos: IDOR em histórico/recursos, XSS armazenado, ação privilegiada
(aprovar/excluir) sem verificar quem pede, perda/sobrescrita silenciosa de dados de outros
usuários, estado global compartilhado entre usuários.

### MEDIUM
Impacto real, mas limitado ou condicionado. Inclui defeitos de arquitetura e qualidade
que **já produzem** ou **facilmente produzem** bugs. Exemplos: race condition em
leitura-modifica-escrita, validação de domínio ausente (datas, faixas, enums), exposição de
detalhes internos em erro, CORS permissivo com credenciais, acoplamento que impede testar uma regra
crítica, transação ausente em operação composta.

### LOW
Higiene, manutenção e defesa em profundidade sem caminho de exploração direto. Exemplos:
headers de segurança ausentes, `print` de depuração, código duplicado, magic numbers,
dependência sem pin, configuração de build frágil, acessibilidade básica.

### INFO
Observação sem risco: contexto, boa prática observada, sugestão. Não entra na contagem.

## 6. Justificativa (obrigatória)

Formato recomendado, em uma ou duas frases:

> **HIGH**: impacto 3 (lê histórico de outros usuários) × probabilidade 2 (exige conhecer o
> `conversation_id`, que é devolvido em respostas e logs). Sem mitigação em outra camada.

## 7. Erros comuns de classificação

- Inflar severidade porque o padrão é "famoso" (ex.: `eval` em código de teste não alcançável).
- Rebaixar porque "é só ambiente local". A auditoria avalia o código como se fosse implantado.
- Classificar a mesma causa-raiz duas vezes em níveis diferentes. Consolide e use o maior impacto.
- Confundir esforço de correção com severidade.
