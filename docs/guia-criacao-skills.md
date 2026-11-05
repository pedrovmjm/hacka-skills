# Guia de criação de Agent Skills

Como decidir se uma skill vale a pena, como estruturá-la, como escrevê-la e como testá-la, com uma seleção de templates e repositórios de referência.


**Sumário**

1. [Em 5 minutos](#1-em-5-minutos)
2. [O que é uma skill e quando usar](#2-o-que-é-uma-skill-e-quando-usar)
3. [Como pensar antes de escrever](#3-como-pensar-antes-de-escrever)
4. [Estrutura de uma skill](#4-estrutura-de-uma-skill)
5. [Passo a passo](#5-passo-a-passo)
6. [Como escrever a `description`](#6-como-escrever-a-description)
7. [Boas práticas para as instruções](#7-boas-práticas-para-as-instruções)
8. [Scripts](#8-scripts)
9. [Como testar](#9-como-testar)
10. [Segurança](#10-segurança)
11. [Skills que trabalham em sequência](#11-skills-que-trabalham-em-sequência)
12. [Antipadrões](#12-antipadrões)
13. [Checklist antes de publicar](#13-checklist-antes-de-publicar)
14. [Template para copiar](#14-template-para-copiar)
15. [Materiais e repositórios](#15-materiais-e-repositórios)

---

## 1. Em 5 minutos

- Uma skill é uma **pasta com um `SKILL.md`**. O arquivo traz metadados (`name`, `description`) e instruções em Markdown. Scripts, referências e templates são opcionais.
- O agente lê primeiro só o `name` e a `description` de cada skill. O corpo só é carregado quando a skill é ativada, e os demais arquivos só quando necessário.
- Por isso, **a `description` decide se a skill será usada**, e o `SKILL.md` deve conter apenas o essencial.
- Escreva **só o que o agente não saberia sozinho**: convenções, procedimentos, armadilhas e formatos de saída.
- **Comece por uma tarefa real**, não por uma folha em branco. Faça a tarefa com o agente, observe o que precisou corrigir e transforme isso na skill.
- **Teste com e sem a skill.** Se o resultado for igual, ela não está agregando valor.
- **Trate skills de terceiros como código de terceiros**: leia antes de instalar.

---

## 2. O que é uma skill e quando usar

Agent Skills é um [padrão aberto](https://agentskills.io/specification) adotado por ferramentas como Claude Code, OpenAI Codex e GitHub Copilot. Uma skill ensina um **procedimento reutilizável** que o agente carrega sob demanda.

### Qual mecanismo escolher

| Você precisa de... | Use | Exemplo |
| --- | --- | --- |
| Regras que valem em toda conversa | Instruções do projeto (`AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`) | "Use pytest", "commits em inglês" |
| Um procedimento usado só em certas tarefas | **Skill** | Auditar um projeto, gerar um relatório padronizado |
| Uma operação que precisa dar sempre o mesmo resultado | Script (que pode estar dentro de uma skill) | Validar um arquivo, gerar um inventário |
| Acesso a um sistema ou dado externo | Servidor MCP | Consultar um banco, abrir um ticket |
| Contexto isolado ou um papel dedicado | Subagente ou agente customizado | Coordenar várias etapas de um fluxo |

Esses mecanismos se combinam: uma skill pode chamar um script, usar uma ferramenta MCP ou rodar em um subagente.

### Vale criar uma skill quando

- você repete as mesmas instruções em várias conversas;
- o agente erra sempre da mesma forma sem esse contexto;
- a tarefa exige um processo ou formato de saída consistente;
- o conhecimento é específico da equipe, do domínio ou do projeto.

### Não vale criar quando

- o agente já resolve bem sem ajuda (compare com e sem a skill antes de investir);
- é uma tarefa pontual que não vai se repetir;
- a regra deve valer sempre, caso em que o lugar dela é nas instruções do projeto.

---

## 3. Como pensar antes de escrever

Responda a estas perguntas antes de abrir o editor. Elas definem quase toda a estrutura.

| Pergunta | O que ela define |
| --- | --- |
| Qual tarefa, exatamente, a skill resolve? | Escopo e nome |
| O que um usuário digitaria ao precisar dela? | Gatilhos da `description` |
| Quando ela **não** deve ser usada? | Limites da `description` e seção "Quando não usar" |
| O que o agente erra sem ela? | O conteúdo que realmente importa |
| O que entra e o que sai? | Entradas, formato de saída e template |
| Qual parte não pode variar? | O que vira script ou regra rígida |
| Como saber se deu certo? | Critério de pronto e testes |
| Quais ações são arriscadas? | Regras invioláveis e pontos de aprovação humana |

### Defina um escopo coerente

Pense em uma skill como em uma função: ela deve fazer [uma unidade coerente de trabalho](https://agentskills.io/skill-creation/best-practices#design-coherent-units).

- **Estreita demais:** várias skills precisam ser carregadas para uma única tarefa, com custo extra e risco de instruções conflitantes.
- **Ampla demais:** fica difícil ativá-la na hora certa.

Um bom teste **(sugestão do guia)**: se a `description` precisa de "e também..." para cobrir tarefas sem relação entre si, provavelmente são duas skills.

### Parta de conhecimento real

Pedir a um LLM uma skill sem dar contexto produz [instruções genéricas](https://agentskills.io/skill-creation/best-practices#start-from-real-expertise), como "trate os erros adequadamente". Use material concreto:

- uma tarefa real feita com o agente, incluindo as correções que você precisou fazer;
- runbooks, guias de estilo e documentação interna;
- especificações de API, schemas e configurações;
- comentários de code review e histórico de incidentes e correções.

---

## 4. Estrutura de uma skill

### Organização da pasta

```text
nome-da-skill/
├── SKILL.md       # Obrigatório: metadados e instruções
├── scripts/       # Opcional: código executável
├── references/    # Opcional: documentação carregada sob demanda
└── assets/        # Opcional: templates, schemas e outros recursos
```

Só o `SKILL.md` é obrigatório, e o padrão [aceita outras pastas](https://agentskills.io/specification#optional-directories). Comece com o arquivo único e crie as outras conforme a necessidade.

### Os três níveis de carregamento

Esse modelo, chamado de [progressive disclosure](https://agentskills.io/specification#progressive-disclosure), é a principal ideia a considerar na estrutura:

| Nível | Conteúdo | Quando é carregado | Tamanho indicado |
| --- | --- | --- | --- |
| 1. Metadados | `name` e `description` | No início, para todas as skills | ~100 tokens |
| 2. Instruções | Corpo do `SKILL.md` | Quando a skill é ativada | < 5.000 tokens e < 500 linhas |
| 3. Recursos | `scripts/`, `references/`, `assets/` | Só quando necessário | Arquivos pequenos e focados |

### Onde colocar cada conteúdo

| Conteúdo | Lugar | Motivo |
| --- | --- | --- |
| Quando usar a skill | `description` | É o que o agente lê antes de ativá-la |
| Fluxo principal e regras invioláveis | `SKILL.md` | Valem em toda execução |
| Armadilhas que o agente não reconheceria sozinho | `SKILL.md` | Precisam ser lidas antes de o problema acontecer |
| Detalhes usados só em alguns casos | `references/` | Não ocupam contexto sem necessidade |
| Formato de saída longo | `assets/` | Carregado só na hora de gerar a saída |
| Operações que precisam ser determinísticas | `scripts/` | O agente executa o script sem ter de ler o código |

### Campos do frontmatter

Definidos na [especificação](https://agentskills.io/specification#frontmatter):

| Campo | Obrigatório | Regras |
| --- | --- | --- |
| `name` | Sim | Até 64 caracteres, com letras minúsculas, números e hífens. Sem hífen no início, no fim ou duplicado. **Igual ao nome da pasta.** |
| `description` | Sim | Até 1.024 caracteres. Diz o que a skill faz e quando usá-la. |
| `license` | Não | Nome da licença ou arquivo incluído na skill. |
| `compatibility` | Não | Até 500 caracteres. Use só se houver requisitos de ambiente. |
| `metadata` | Não | Mapa de chaves e valores em texto, como `author` e `version`. |
| `allowed-tools` | Não | Ferramentas pré-aprovadas, separadas por espaços. Campo experimental; o suporte varia. |

**Pontos de atenção**

- No ecossistema da Anthropic, [`name` não pode conter](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#skill-structure) as palavras `anthropic` ou `claude`, e `name` e `description` não podem ter tags XML.
- O Claude Code [tem campos próprios](https://code.claude.com/docs/en/skills), como `disable-model-invocation`, `context` e `paths`. Fora dele (uploads no claude.ai e Skills API), só os seis campos padrão são aceitos, e chaves extras **causam erro de validação**.
- O Claude Code trunca em 1.536 caracteres o texto combinado de `description` e `when_to_use` na listagem. Coloque o caso de uso principal no começo.
- No Claude Code, `allowed-tools` **pré-aprova ferramentas, mas não restringe as demais**. Para remover uma ferramenta, use `disallowed-tools`.

### Onde cada ferramenta procura skills

| Ferramenta | No projeto | Pessoal | Fonte |
| --- | --- | --- | --- |
| Claude Code | `.claude/skills/` | `~/.claude/skills/` | [Docs](https://code.claude.com/docs/en/skills) |
| OpenAI Codex | `.agents/skills/` (da pasta atual até a raiz do repositório) | `~/.agents/skills/` | [Docs](https://learn.chatgpt.com/docs/build-skills) |
| GitHub Copilot | `.github/skills/`, `.claude/skills/` ou `.agents/skills/` | `~/.copilot/skills/` ou `~/.agents/skills/` | [Docs](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills) |

Nenhuma pasta aparece nas três listas. Para atender Claude Code e Copilot, use `.claude/skills/`; para Codex e Copilot, use `.agents/skills/`. Para os três, mantenha uma cópia ou um link simbólico nas duas pastas **(sugestão do guia)**.

---

## 5. Passo a passo

### 1. Faça a tarefa sem skill

[Execute uma tarefa real com o agente](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#develop-skills-iteratively-with-claude) e anote o que precisou explicar, o que precisou corrigir, os comandos que funcionaram e o formato de saída desejado. Essas anotações são a matéria-prima da skill.

### 2. Defina os cenários de teste

Antes de escrever muita documentação, [crie ao menos três cenários](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#build-evaluations-first) baseados nas falhas observadas. Assim, a skill resolve problemas reais, e não problemas imaginados.

### 3. Crie a pasta e o frontmatter

Escolha um nome específico. Use um único padrão de nomes em toda a coleção, como `processing-pdfs` ou `pdf-processing`. Evite nomes como `helper`, `utils` e `tools`.

Você pode partir do [template deste guia](#14-template-para-copiar), do [template da Anthropic](https://github.com/anthropics/skills/tree/main/template) ou rodar `npx skills init <nome>` com a [CLI `skills`](https://github.com/vercel-labs/skills).

### 4. Escreva a `description`

Veja a [seção 6](#6-como-escrever-a-description). Uma boa versão inicial já ajuda; o ajuste fino vem com os testes.

### 5. Escreva o mínimo de instruções

Inclua só o necessário para passar nos cenários. Uma ordem que costuma funcionar **(sugestão do guia)**:

1. quando usar e quando não usar;
2. regras invioláveis;
3. fluxo em passos numerados;
4. armadilhas conhecidas;
5. formato de saída;
6. mapa dos arquivos da skill;
7. critério de pronto.

### 6. Separe o que cresceu demais

Mova detalhes para `references/` e operações repetitivas para `scripts/`. Diga [quando carregar cada arquivo](https://agentskills.io/skill-creation/best-practices#structure-large-skills-with-progressive-disclosure):

```markdown
<!-- Vago -->
Veja references/ para mais detalhes.

<!-- Melhor -->
Se a API retornar um status diferente de 200, leia `references/erros-api.md`.
```

### 7. Valide o formato

```bash
skills-ref validate ./nome-da-skill
```

O [`skills-ref`](https://github.com/agentskills/agentskills/tree/main/skills-ref) é a biblioteca de referência do padrão e precisa ser instalado a partir do repositório. Segundo o próprio README, ela é apenas demonstrativa e não se destina a produção.

### 8. Teste em uma sessão nova

Use uma sessão limpa para garantir que o agente siga apenas o que está na skill. Observe se ela foi ativada, quais arquivos foram lidos, onde houve desperdício de esforço e o que saiu errado. Veja a [seção 9](#9-como-testar).

### 9. Ajuste a partir do que observou

[Leia o histórico de execução, não só o resultado final](https://agentskills.io/skill-creation/best-practices#refine-with-real-execution). Quando precisar corrigir o agente, registre a correção nas armadilhas da skill. Corte também o que não fez diferença.

### 10. Publique e mantenha

Versione a skill no Git e defina um responsável. Revise-a quando as ferramentas ou os processos mudarem, e colete o retorno de quem a usa.

---

## 6. Como escrever a `description`

A `description` é a parte mais importante da skill. Se for vaga, a skill não é ativada; se for ampla demais, é ativada na hora errada.

Uma fórmula simples:

```text
[O que faz, com verbos concretos]. Use quando [situações e intenções do usuário], mesmo que [variação em que o usuário não cita o assunto diretamente].
```

| Evite | Prefira |
| --- | --- |
| `Ajuda com documentos.` | `Extrai texto e tabelas de PDFs, preenche formulários e combina arquivos. Use ao trabalhar com PDFs ou quando o usuário mencionar formulários ou extração de documentos.` |
| `Processa dados.` | `Analisa arquivos CSV e planilhas: calcula estatísticas, limpa dados e gera gráficos. Use quando o usuário quiser explorar ou visualizar dados tabulares, mesmo sem citar "CSV".` |
| `Eu posso escrever suas notas de versão.` | `Gera notas de versão a partir do histórico do Git, sem alterar o código. Use quando o usuário pedir changelog, release notes ou um resumo do que mudou entre versões.` |

**Recomendações**

- **Foque na intenção do usuário**, não na mecânica interna.
- **Inclua as palavras que as pessoas realmente usam**, inclusive termos em inglês e no idioma da equipe **(sugestão do guia)**.
- **Declare os limites** quando houver risco de confusão com outra skill, como "não corrige o código".
- **Evite primeira e segunda pessoa.** A [Anthropic recomenda a terceira pessoa](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#writing-effective-descriptions), pois o texto é inserido no prompt de sistema.

> **As fontes divergem em um detalhe.** A Anthropic pede terceira pessoa ("Processa arquivos..."), enquanto o [agentskills.io](https://agentskills.io/skill-creation/optimizing-descriptions#writing-effective-descriptions) prefere a forma imperativa ("Use esta skill quando..."). A fórmula acima atende às duas: descreve em terceira pessoa o que a skill faz e depois diz "Use quando...".

**Tarefas simples podem não ativar a skill.** Agentes tendem a [consultar skills em tarefas que vão além do que resolvem sozinhos](https://agentskills.io/skill-creation/optimizing-descriptions#how-skill-triggering-works). Um pedido como "leia este PDF" pode não ativar uma skill de PDF, mesmo com uma boa `description`. Isso não significa necessariamente que ela esteja errada.

---

## 7. Boas práticas para as instruções

### Economize contexto

Para cada trecho, pergunte: [o agente erraria sem esta instrução?](https://agentskills.io/skill-creation/best-practices#add-what-the-agent-lacks-omit-what-it-knows) Se a resposta for não, corte.

```markdown
<!-- Prolixo: o agente já sabe o que é um PDF -->
PDF é um formato de arquivo comum que contém texto e imagens. Existem
várias bibliotecas para processá-lo, e pdfplumber é uma boa opção...

<!-- Direto -->
Use pdfplumber para extrair texto. Em PDFs escaneados, use pdf2image com pytesseract.
```

### Ajuste o nível de controle ao risco

| Situação | Nível de controle | Exemplo |
| --- | --- | --- |
| Várias abordagens são válidas | Alta liberdade: objetivos e critérios | Revisão de código |
| Existe um padrão preferido, com alguma variação | Média liberdade: template ou script com parâmetros | Geração de relatório |
| Operação frágil ou com sequência obrigatória | Baixa liberdade: comando exato | Migração de banco |

A Anthropic usa uma [analogia](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#set-appropriate-degrees-of-freedom): em uma ponte estreita, dê instruções exatas; em um campo aberto, indique a direção. A mesma skill pode combinar os dois níveis.

### Ofereça um padrão, não um menu

```markdown
<!-- Menu -->
Você pode usar pypdf, pdfplumber, PyMuPDF ou pdf2image...

<!-- Padrão com exceção -->
Use pdfplumber. Em PDFs escaneados, use pdf2image com pytesseract.
```

### Ensine o método, não uma resposta específica

Uma skill deve [servir para uma classe de problemas](https://agentskills.io/skill-creation/best-practices#favor-procedures-over-declarations). "Leia o schema e faça o join pela chave `_id`" é reutilizável; "faça o join de `orders` com `customers` e filtre `EMEA`" só serve para aquele caso.

### Explique o motivo

[Instruções com justificativa](https://agentskills.io/skill-creation/evaluating-skills#iterating-on-the-skill) tendem a funcionar melhor do que ordens soltas, pois ajudam o agente a decidir em situações não previstas. Guarde a linguagem imperativa para o que é realmente inegociável, e justifique também nesses casos.

```markdown
Não reescreva o histórico do Git: outras pessoas podem já ter baseado
trabalho nesses commits.
```

### Liste as armadilhas

Muitas vezes, a [seção de maior valor](https://agentskills.io/skill-creation/best-practices#gotchas-sections) é a de armadilhas: fatos do ambiente que contrariam o que seria razoável supor.

```markdown
## Armadilhas

- A tabela `users` usa exclusão lógica. Inclua `WHERE deleted_at IS NULL`,
  ou contas desativadas aparecerão nos resultados.
- `/health` retorna 200 mesmo com o banco fora do ar. Use `/ready`.
```

### Use padrões que aumentam a confiabilidade

| Padrão | Quando usar | Como funciona |
| --- | --- | --- |
| [Template de saída](https://agentskills.io/skill-creation/best-practices#templates-for-output-format) | O formato importa | Mostre a estrutura em vez de descrevê-la em prosa |
| [Exemplos de entrada e saída](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#examples-pattern) | A qualidade depende de estilo ou nível de detalhe | Inclua alguns pares concretos |
| [Checklist](https://agentskills.io/skill-creation/best-practices#checklists-for-multi-step-workflows) | Muitos passos ou dependências entre eles | O agente acompanha o progresso e não pula etapas |
| [Ciclo de validação](https://agentskills.io/skill-creation/best-practices#validation-loops) | Há como verificar o resultado | Fazer → validar → corrigir → repetir |
| [Planejar, validar, executar](https://agentskills.io/skill-creation/best-practices#plan-validate-execute) | Operações em lote ou destrutivas | Gere um plano estruturado e valide-o antes de executar |

### Cuide da organização e do texto

- Mantenha as referências [a um nível de distância do `SKILL.md`](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#avoid-deeply-nested-references). Em cadeias longas, o agente pode ler os arquivos só em parte.
- Coloque um sumário no início de referências com mais de 100 linhas.
- Use nomes descritivos: `regras-validacao.md`, não `doc2.md`.
- Use sempre `/` nos caminhos, mesmo no Windows.
- Use sempre o mesmo termo para o mesmo conceito.
- Evite informações que envelhecem, como "antes de agosto, use a API antiga".

---

## 8. Scripts

[Scripts são indicados](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#provide-utility-scripts) quando a operação precisa ser determinística ou quando o agente reescreve a mesma lógica a cada execução. Eles são mais confiáveis do que código gerado na hora e economizam contexto, já que, ao executar um script, só a saída ocupa espaço. Para o resto, [prefira instruções](https://learn.chatgpt.com/docs/build-skills).

- **Deixe claro o que fazer com o arquivo:** "execute `analisar.py`" ou "leia `analisar.py` para entender o algoritmo".
- **Trate os erros no script**, em vez de deixar o agente descobrir o que aconteceu.
- **Escreva mensagens úteis:** "Campo `data` não encontrado. Campos disponíveis: `nome`, `total`".
- **Declare as dependências** e não presuma que estejam instaladas.
- **Justifique os valores fixos:** um comentário deve explicar por que o timeout é 30 segundos.
- **Considere o ambiente:** [na API da Anthropic, as skills não têm acesso à rede nem instalam pacotes em tempo de execução](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#package-dependencies).
- **Teste os scripts** separadamente, como qualquer outro código **(sugestão do guia)**.

---

## 9. Como testar

Há duas perguntas diferentes, e cada uma exige um teste.

### A skill é ativada na hora certa?

[Roteiro do agentskills.io](https://agentskills.io/skill-creation/optimizing-descriptions):

1. Crie cerca de **20 pedidos realistas**: de 8 a 10 que devem ativar a skill e de 8 a 10 que não devem.
2. Nos negativos, use **quase acertos**, pedidos com palavras parecidas, mas outra necessidade. "Qual é a previsão do tempo?" não testa nada.
3. Rode cada pedido cerca de **3 vezes**, pois o comportamento do modelo varia. Uma taxa de ativação de 0,5 é um bom ponto de corte inicial.
4. Separe os pedidos em **treino (~60%) e validação (~40%)**. Ajuste a `description` só com as falhas do treino e escolha a versão com melhor resultado na validação.
5. Generalize os ajustes: copiar palavras de um pedido que falhou é sobreajuste. Em geral, cinco iterações bastam.

```json
[
  { "query": "meu gestor pediu um resumo do que mudou na versão 2.4 para enviar aos clientes", "should_trigger": true },
  { "query": "escreve a mensagem de commit para o diff que está em stage", "should_trigger": false }
]
```

### O resultado melhora?

[Roteiro do agentskills.io](https://agentskills.io/skill-creation/evaluating-skills):

1. Comece com **2 ou 3 casos**, cada um com pedido realista, resultado esperado e arquivos de entrada. Inclua ao menos um caso de borda.
2. Rode cada caso **com e sem a skill**, em sessões limpas. Ao melhorar uma skill, compare com a versão anterior.
3. Depois da primeira rodada, escreva **verificações objetivas** e exija evidência para cada aprovação.
4. Compare qualidade, tempo e tokens. Uma skill pode dobrar o custo sem melhorar quase nada.
5. Peça a revisão de uma pessoa, pois verificações só cobrem o que você pensou em verificar.
6. Remova verificações que sempre passam nos dois cenários, já que não medem o valor da skill.

```json
{
  "skill_name": "release-notes",
  "evals": [
    {
      "id": 1,
      "prompt": "Gere as notas da versão 2.4 a partir do histórico entre as tags v2.3 e v2.4",
      "expected_output": "Notas de versão agrupadas por tipo de mudança, sem alterar o código.",
      "files": ["evals/files/repo-exemplo/"],
      "assertions": [
        "git status não mostra alterações fora de CHANGELOG.md",
        "Todo item cita um commit que existe no intervalo",
        "Mudanças incompatíveis aparecem em uma seção própria"
      ]
    }
  ]
}
```

| Verificação fraca | Verificação boa |
| --- | --- |
| "As notas estão boas" | "Todo item cita um commit que existe no intervalo" |
| "O texto contém exatamente 'Total: X'" | "As notas informam o total de mudanças" |

Teste também [com os modelos que você pretende usar](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#test-with-all-models-you-plan-to-use): o que funciona em um modelo mais capaz pode precisar de mais detalhes em um mais simples.

> **Atalho:** a skill [`skill-creator`](https://github.com/anthropics/skills/tree/main/skills/skill-creator) da Anthropic automatiza grande parte desse processo: executa os testes, avalia as verificações, agrega resultados e ajuda a otimizar a `description`.

---

## 10. Segurança

Uma skill pode direcionar as ações do agente e incluir código executável. A Anthropic [recomenda instalar apenas skills de fontes confiáveis](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills), já que uma skill maliciosa pode introduzir vulnerabilidades ou induzir o agente a vazar dados.

**Ao adotar uma skill de terceiros**

- [ ] Li todos os arquivos, inclusive scripts e recursos.
- [ ] Verifiquei dependências e conexões de rede externas.
- [ ] Procurei instruções que tentem acessar segredos ou enviar dados para fora.
- [ ] Verifiquei a licença.
- [ ] Fixei um commit ou uma versão, em vez de acompanhar sempre a versão mais recente **(sugestão do guia)**.

**Ao criar uma skill** **(sugestões do guia)**

- Não inclua segredos nem dados pessoais; use variáveis de ambiente.
- Pré-aprove o mínimo de ferramentas possível.
- Exija confirmação humana para ações destrutivas ou irreversíveis.
- Oriente o agente a tratar arquivos analisados e páginas web como dados, não como instruções.
- Garanta restrições importantes com mecanismos da ferramenta (permissões, `disallowed-tools`) e não só com texto na skill.

---

## 11. Skills que trabalham em sequência

As recomendações abaixo são **sugestões do guia** para fluxos com várias skills, como `análise → revisão humana → execução`.

- **Uma responsabilidade por skill.** Cada uma deve poder ser executada e testada sozinha.
- **Passe o trabalho por arquivos.** A saída de uma é a entrada da outra, e isso sobrevive ao fim da sessão. Ex.: `saida/analise-<projeto>.md`.
- **Defina um contrato.** Use templates para que a etapa seguinte saiba o que encontrar, e preserve IDs para manter a rastreabilidade.
- **Valide a entrada.** Se o arquivo esperado não existir, a skill deve parar e explicar o que falta, em vez de improvisar.
- **Crie um ponto de aprovação explícito.** A skill anterior deve parar, e a seguinte deve exigir um registro de aprovação.
- **Reduza a ativação automática de etapas arriscadas.** No Claude Code e no VS Code, [`disable-model-invocation: true`](https://code.claude.com/docs/en/skills) faz a skill ser iniciada só manualmente. No Codex, o equivalente é `policy.allow_implicit_invocation: false` em [`agents/openai.yaml`](https://learn.chatgpt.com/docs/build-skills).
- **Deixe a coordenação para um agente.** A sequência pode ficar em um agente coordenador, e as skills continuam independentes. No Claude Code, uma skill com `context: fork` roda em um subagente que não vê o histórico da conversa, então as instruções precisam ser autossuficientes.

---

## 12. Antipadrões

| Antipadrão | Problema | O que fazer |
| --- | --- | --- |
| `description` vaga | A skill não é ativada | Diga o que faz e quando usar |
| Explicar o óbvio | Gasta contexto sem ganho | Mantenha só o que o agente não sabe |
| Skill gerada sem contexto real | Vira um manual genérico | Parta de uma tarefa ou de material real |
| Cobrir todos os casos possíveis | O agente se perde em instruções irrelevantes | Passos curtos e um exemplo que funcione |
| `SKILL.md` gigante | Todo o conteúdo é carregado sempre | Mova detalhes para `references/` |
| Referências em cadeia | Leitura parcial | Um nível a partir do `SKILL.md` |
| "Veja references/" sem dizer quando | O arquivo é ignorado ou lido à toa | Diga em que situação ler |
| Muitas opções equivalentes | O agente hesita ou tenta várias | Um padrão e uma exceção |
| Skill presa a um caso específico | Não pode ser reutilizada | Ensine o método |
| Testar só o caminho feliz, na mesma sessão | Falsa confiança | Sessão limpa, casos de borda e comparação sem a skill |
| Instalar muitas skills "por garantia" | [Dispersa a atenção e gasta tokens](https://github.com/microsoft/skills) | Instale só o que o projeto usa |
| Copiar skill de terceiros sem ler | Risco de segurança | Leia tudo antes de adotar |

---

## 13. Checklist antes de publicar

**Formato**

- [ ] `name` válido e igual ao nome da pasta.
- [ ] `description` diz o que a skill faz e quando usá-la, em até 1.024 caracteres.
- [ ] Campos fora do padrão só aparecem se a ferramenta de destino os aceitar.
- [ ] `skills-ref validate` executado.

**Conteúdo**

- [ ] `SKILL.md` com menos de 500 linhas.
- [ ] Nada que o agente já saiba.
- [ ] Escopo coerente e limites claros.
- [ ] Passos claros, com um padrão definido quando há mais de uma opção.
- [ ] Armadilhas documentadas.
- [ ] Referências a um nível de distância, indicando quando carregar cada uma.
- [ ] Terminologia consistente e sem informação datada.

**Scripts**

- [ ] Dependências declaradas.
- [ ] Erros tratados, com mensagens úteis.
- [ ] Valores fixos justificados.
- [ ] Caminhos com `/`.

**Testes**

- [ ] Ativação testada, inclusive com quase acertos.
- [ ] Ao menos 3 cenários, comparados com e sem a skill.
- [ ] Testada em sessão limpa e com os modelos previstos.
- [ ] Testada por outra pessoa, se for compartilhada.

**Segurança**

- [ ] Sem segredos ou dados pessoais.
- [ ] Ferramentas pré-aprovadas no mínimo necessário.
- [ ] Ações destrutivas exigem confirmação.
- [ ] Licença definida, se for distribuída.

---

## 14. Template para copiar

Salve como `nome-da-skill/SKILL.md` e **apague as seções que não fizerem diferença**. Este template é um ponto de partida, não um formato obrigatório.

````markdown
---
name: nome-da-skill
description: [O que faz, com verbos concretos]. Use quando [situações e intenções do usuário], mesmo que [variação em que o usuário não cita o assunto diretamente]. Não usar para [limite, se houver confusão com outra skill].
---

# Nome da skill

[Uma ou duas frases sobre o objetivo e o resultado esperado.]

## Quando usar

- [Situação concreta]

## Quando não usar

- [Situação parecida que pertence a outra skill ou etapa]

## Regras invioláveis

1. [Regra] porque [motivo].

## Fluxo de trabalho

Copie este checklist e acompanhe o progresso:

```text
- [ ] 1. Preparar
- [ ] 2. Executar
- [ ] 3. Validar
- [ ] 4. Entregar
```

### 1. Preparar

- [O que ler ou verificar. O que fazer se faltar algo.]

### 2. Executar

- [Padrão a seguir e exceção, se houver.]
- Se [condição], leia `references/arquivo.md`.

### 3. Validar

1. Execute `python scripts/validar.py <saida>`.
2. Se falhar, corrija o problema e rode novamente.
3. Só avance quando a validação passar.

### 4. Entregar

Preencha `assets/template-saida.md` e salve em `[caminho]`.

## Armadilhas

- [Fato do ambiente que contraria o que seria razoável supor, e o que fazer.]

## Exemplo

**Entrada:** [pedido realista]

**Saída:** [trecho do resultado esperado]

## Arquivos da skill

| Arquivo | Quando usar |
| --- | --- |
| `references/arquivo.md` | [Situação] |
| `scripts/validar.py` | Executar na etapa 3 |
| `assets/template-saida.md` | Preencher na etapa 4 |

## Critério de pronto

- [ ] [Condição verificável]
````

---

## 15. Materiais e repositórios

### Por onde começar

Uma trilha curta, nesta ordem **(sugestão do guia)**:

1. [Especificação do padrão](https://agentskills.io/specification): o formato.
2. [Best practices do agentskills.io](https://agentskills.io/skill-creation/best-practices): como pensar a skill.
3. [`anthropics/skills/template`](https://github.com/anthropics/skills/tree/main/template): o ponto de partida mínimo.
4. [`skill-creator`](https://github.com/anthropics/skills/tree/main/skills/skill-creator): um exemplo completo que também ajuda a criar e testar skills.
5. [Avaliação de resultados](https://agentskills.io/skill-creation/evaluating-skills) e [de ativação](https://agentskills.io/skill-creation/optimizing-descriptions): como medir se funciona.

### Documentação oficial

| Fonte | Material | Conteúdo |
| --- | --- | --- |
| Padrão aberto | [Agent Skills](https://agentskills.io/home) | Visão geral, [especificação](https://agentskills.io/specification), [início rápido](https://agentskills.io/skill-creation/quickstart) e [uso de scripts](https://agentskills.io/skill-creation/using-scripts) |
| Anthropic | [Visão geral](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) | Conceitos e arquitetura |
| Anthropic | [Boas práticas de autoria](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | O guia mais completo; leitura recomendada |
| Anthropic | [Skills no Claude Code](https://code.claude.com/docs/en/skills) | Locais, campos, argumentos e subagentes |
| Anthropic | [Artigo de engenharia](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) | Motivação, princípios de design e segurança |
| OpenAI | [Build skills](https://learn.chatgpt.com/docs/build-skills) | Skills no Codex |
| OpenAI | [Build plugins](https://developers.openai.com/codex/plugins/build) | Distribuição, inclusive plugins só com skills |
| GitHub | [About agent skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills) | Skills no Copilot |
| Microsoft | [VS Code](https://code.visualstudio.com/docs/agent-customization/agent-skills) | Skills no VS Code e comparação com instruções |
| Microsoft | [Visual Studio](https://learn.microsoft.com/en-us/visualstudio/ide/copilot-agent-skills) | Skills no Visual Studio |
| Microsoft | [Agent Framework](https://learn.microsoft.com/en-us/agent-framework/agents/skills) | Skills em agentes criados com o framework |

### Repositórios oficiais e de fabricantes

As estrelas são aproximadas. Elas medem popularidade, não qualidade nem segurança.

| Repositório | Estrelas | Para que serve | Licença e observações |
| --- | --- | --- | --- |
| [`anthropics/skills`](https://github.com/anthropics/skills) | 187 mil | Referência principal: [template](https://github.com/anthropics/skills/tree/main/template), [`skill-creator`](https://github.com/anthropics/skills/tree/main/skills/skill-creator) e exemplos | Muitas são Apache 2.0; `docx`, `pdf`, `pptx` e `xlsx` são *source-available*, não open source. Os exemplos têm fins educativos |
| [`agentskills/agentskills`](https://github.com/agentskills/agentskills) | 27 mil | Especificação, documentação e validador `skills-ref` | Apache 2.0 |
| [`anthropics/claude-plugins-official`](https://github.com/anthropics/claude-plugins-official) | 46 mil | Diretório oficial de plugins do Claude Code | Apache 2.0 |
| [`openai/plugins`](https://github.com/openai/plugins) | 7,8 mil | Exemplos atuais de skills e plugins para o Codex | Confira a licença de cada item |
| [`openai/skills`](https://github.com/openai/skills) | 29 mil | Catálogo com [`skill-creator`](https://github.com/openai/skills/tree/main/skills/.system/skill-creator) e skills selecionadas | **Depreciado**: o README indica `openai/plugins`. Útil só como referência. Licença por skill |
| [`github/awesome-copilot`](https://github.com/github/awesome-copilot) | 41 mil | Skills, instruções e agentes para Copilot | MIT. Conteúdo da comunidade |
| [`microsoft/skills`](https://github.com/microsoft/skills) | 3,2 mil | Skills, agentes e MCP com foco em SDKs do Azure e AI Foundry | MIT. O README recomenda instalar seletivamente |
| [`vercel-labs/agent-skills`](https://github.com/vercel-labs/agent-skills) | 34 mil | Coleção oficial da Vercel | Licença não identificada pela API do GitHub; confira |
| [`huggingface/skills`](https://github.com/huggingface/skills) | 11 mil | Ecossistema Hugging Face | Apache 2.0 |
| [`google-gemini/gemini-skills`](https://github.com/google-gemini/gemini-skills) | 4,4 mil | API e SDK do Gemini | Apache 2.0 |
| [`cloudflare/skills`](https://github.com/cloudflare/skills) | 3,3 mil | Desenvolvimento na Cloudflare | Apache 2.0 |

### Repositórios famosos da comunidade

| Repositório | Estrelas | Por que olhar | Licença |
| --- | --- | --- | --- |
| [`obra/superpowers`](https://github.com/obra/superpowers) | 312 mil | Metodologia de desenvolvimento em forma de skills, incluindo [`writing-skills`](https://github.com/obra/superpowers/tree/main/skills/writing-skills) | MIT |
| [`mattpocock/skills`](https://github.com/mattpocock/skills) | 313 mil | Skills de engenharia usadas pelo próprio autor | MIT |
| [`addyosmani/agent-skills`](https://github.com/addyosmani/agent-skills) | 113 mil | Skills de engenharia para vários agentes; o repositório tem uma pasta `evals/` | MIT |
| [`trailofbits/skills`](https://github.com/trailofbits/skills) | 8 mil | Pesquisa de segurança e fluxos de auditoria | CC-BY-SA 4.0 |

### Listas curadas e ferramentas

| Repositório | Estrelas | Tipo | Observação |
| --- | --- | --- | --- |
| [`vercel-labs/skills`](https://github.com/vercel-labs/skills) | 38 mil | CLI `npx skills` | Instala, lista, busca, cria e atualiza skills em vários agentes |
| [`VoltAgent/awesome-agent-skills`](https://github.com/VoltAgent/awesome-agent-skills) | 37 mil | Lista | Mais de 1.000 skills de fabricantes e da comunidade |
| [`ComposioHQ/awesome-claude-skills`](https://github.com/ComposioHQ/awesome-claude-skills) | 79 mil | Lista | Licença não identificada pela API do GitHub |
| [`travisvn/awesome-claude-skills`](https://github.com/travisvn/awesome-claude-skills) | 16 mil | Lista | Atualizada com menos frequência; confira a data do último commit |

No GitHub CLI, [`gh skill`](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills) também encontra e instala skills de repositórios do GitHub.

```bash
npx skills find auditoria                # busca skills
npx skills add vercel-labs/agent-skills  # instala de um repositório
npx skills init minha-skill              # cria um template
```

> **Antes de instalar:** as listas e os repositórios da comunidade não garantem a segurança do conteúdo. Aplique o [checklist de segurança](#10-segurança).

### Como avaliar um repositório

**(sugestões do guia)**

- Quem mantém o repositório, e ele ainda é atualizado?
- A licença permite o uso pretendido?
- As `description` são específicas, e os `SKILL.md`, enxutos?
- Os scripts são legíveis e têm poucas dependências?
- Há testes ou avaliações?
- A skill melhora o resultado **no seu caso**, em comparação com não usar nenhuma?
