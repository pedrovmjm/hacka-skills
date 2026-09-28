# Desafio: três skills para auditoria e refatoração de projetos legados

Este repositório contém dois projetos legados fictícios, executáveis localmente e com problemas intencionais de arquitetura, segurança e qualidade.

O desafio é criar **três skills reutilizáveis** que trabalhem em sequência:

1. reconhecer uma base de código desconhecida;
2. auditá-la e produzir achados verificáveis;
3. refatorar somente o que foi aprovado e validar o resultado.

> Os projetos são intencionalmente vulneráveis. Use-os apenas em ambiente local. Não há credenciais nem dados pessoais reais.

Para apresentar a motivação do desafio, abra [`apresentacao.html`](apresentacao.html) no navegador.

## O que deve ser criado

As três skills abaixo são obrigatórias. Os nomes são sugestões; as responsabilidades são requisitos.

| Skill | Responsabilidade | Saída mínima |
| --- | --- | --- |
| **1. Reconhecimento** (`project-discovery`) | Identificar stack, domínio, entradas, persistência, testes, arquitetura e fronteiras de confiança. | Relatório de reconhecimento por projeto. |
| **2. Auditoria** (`secure-audit`) | Encontrar problemas de segurança, arquitetura e qualidade, sem alterar a implementação. | Relatório de auditoria com severidade, evidência, localização, impacto e recomendação. |
| **3. Refatoração e validação** (`approved-refactor`) | Consumir apenas os achados aprovados, corrigir suas causas-raiz e verificar que os fluxos legítimos continuam funcionando. | Código refatorado, testes e matriz de rastreabilidade. |

Cada skill deve ter seu próprio `SKILL.md` e os arquivos de referência necessários. Elas devem ser independentes do projeto e funcionar nos **dois projetos-alvo**.

Não é esperado impor MVC ou qualquer arquitetura única. A solução deve propor limites coerentes com a stack e o domínio encontrados.

## Fluxo obrigatório

```text
baseline → reconhecimento → auditoria → revisão humana → refatoração → validação
```

1. Execute os testes atuais e guarde o resultado como baseline.
2. Execute a skill de reconhecimento nos dois projetos.
3. Execute a skill de auditoria e salve os relatórios.
4. Pare e peça revisão humana.
5. Registre quais achados foram aprovados, rejeitados ou ajustados.
6. Somente após aprovação explícita, execute a skill de refatoração.
7. Repita os testes e valide ao menos um fluxo ponta a ponta de cada projeto.

**Nenhum arquivo de implementação pode ser alterado antes da aprovação do relatório de auditoria.**

## Formato da auditoria

A skill de auditoria deve analisar código e configuração sem editar a implementação. Cada achado deve conter:

- identificador e título;
- severidade `CRITICAL`, `HIGH`, `MEDIUM` ou `LOW`, com justificativa;
- arquivo e linha;
- evidência ou reprodução;
- comportamento esperado e comportamento atual;
- impacto;
- recomendação;
- estratégia de validação da correção.

Achados com a mesma causa-raiz devem ser consolidados. Suposições sem evidência e duplicação artificial de achados contam negativamente.

## Projetos-alvo

| Projeto | Stack | O que deve continuar funcionando |
| --- | --- | --- |
| [`langgraph-agent-platform/`](langgraph-agent-platform/README.md) | Python 3.12, FastAPI, LangGraph e SQLite | Configuração de agentes, conversa, ferramentas, HITL, retomada e histórico persistido. |
| [`polo-visits/`](polo-visits/README.md) | React/Vite, FastAPI e SQLite | Calendário, marcações, meta mensal, troca de perfil, visão do time e interface web. |

Os READMEs de cada projeto contêm instalação, endpoints e fluxos manuais. A plataforma de agentes usa um modelo determinístico local: não exige chave de API nem serviço de IA externo.

## Entregas obrigatórias

- As **três skills**, cada uma com `SKILL.md` e suas referências.
- Um relatório de reconhecimento para cada projeto.
- Um relatório de auditoria para cada projeto, preservado antes da refatoração.
- Registro da revisão humana e do escopo aprovado.
- Código refatorado dos dois projetos, com diff revisável.
- Testes que comprovem as correções e evitem regressões.
- Relatório final com a matriz `achado → correção → teste → resultado` e os comandos executados.
- `README.md` da solução explicando como instalar e executar as skills na ferramenta escolhida.

Crie as skills fora dos projetos-alvo, no local exigido pela ferramenta escolhida, e salve as saídas em uma pasta `reports/` na raiz. Não copie uma implementação diferente para cada projeto: a mesma skill deve ser reutilizável.

## Bônus: agente coordenador

Como bônus, configure um agente que tenha acesso às três skills e coordene o fluxo completo.

O agente deve:

- escolher a skill adequada para cada etapa;
- transferir as saídas entre elas sem perder evidências;
- impedir a refatoração antes da aprovação humana;
- permitir executar cada skill separadamente;
- gerar ao final uma visão única da rastreabilidade.

O bônus não substitui nenhuma das três skills obrigatórias.

## Critérios de aceite

| Área | Critério |
| --- | --- |
| Skills | Existem três skills distintas, reutilizáveis e com responsabilidades claras. |
| Reconhecimento | Stack, domínio, estrutura, persistência, testes e fluxos são descritos corretamente nos dois projetos. |
| Auditoria | Achados têm causa concreta, severidade defensável, evidência e localização precisa. |
| Revisão humana | Nenhum arquivo de implementação é alterado antes da aprovação explícita. |
| Refatoração | As causas-raiz aprovadas são corrigidas; mudanças apenas cosméticas não bastam. |
| Preservação | Os fluxos legítimos dos dois projetos continuam funcionando. |
| Testes | Suítes existentes e novos testes passam; aplicações iniciam; ao menos um fluxo completo por projeto é verificado. |
| Rastreabilidade | Cada achado aprovado aponta para sua correção, teste e resultado. |

## Validação local

Os detalhes de instalação, endpoints e testes estão nos READMEs dos projetos. Para iniciar todos os serviços com Docker:

```bash
docker compose up --build -d
docker compose ps
```

Execute as três suítes abaixo antes e depois da refatoração:

```bash
cd langgraph-agent-platform
python -m pip install -r requirements-dev.txt
python -m pytest -q

cd ../polo-visits/backend
python -m pip install -r requirements-dev.txt
python -m pytest -q

cd ../frontend
npm install
npm test
npm run build
```

Use `docker compose down` para encerrar os serviços.

## Origem

Este desafio foi inspirado em [Criação de Skills — Refatoração Arquitetural Automatizada](https://github.com/devfullcycle/mba-ia-refactor-projects-skill). A adaptação separa o processo em três skills, usa projetos com stacks e fluxos diferentes e não determina uma arquitetura final única.
