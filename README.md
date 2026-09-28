# Desafio de auditoria e refatoração de projetos legados

Este repositório é um ambiente de avaliação para uma **skill de auditoria e refatoração de software**. Ele contém dois projetos legados fictícios, executáveis localmente, com problemas deliberados de arquitetura, segurança e qualidade.

O objetivo é avaliar se uma skill consegue:

1. reconhecer uma base de código desconhecida;
2. produzir uma auditoria técnica verificável;
3. aguardar revisão humana antes de alterar o código;
4. corrigir as causas-raiz aprovadas;
5. comprovar que os fluxos legítimos continuam funcionando.

> Os projetos deste repositório são intencionalmente vulneráveis ou inadequados. Use-os somente em ambiente local. Não há credenciais nem dados pessoais reais.

## Comece aqui: o que deve ser feito

Quem resolver o desafio deve seguir esta ordem:

1. **Criar ou configurar a skill que será avaliada.** A skill não está incluída neste repositório.
2. **Executar os testes atuais e guardar os resultados.** Esses resultados formam o baseline anterior à refatoração.
3. **Apontar a skill apenas para os dois projetos-alvo:**
   - `langgraph-agent-platform/`
   - `polo-visits/`
4. **Solicitar reconhecimento e auditoria.** A skill deve analisar os projetos e salvar um relatório com evidências, severidade e localização dos problemas.
5. **Interromper o processo para revisão humana.** Nenhum arquivo de implementação pode ser alterado antes da aprovação explícita do relatório.
6. **Após a aprovação, executar a refatoração.** Somente os achados aceitos devem orientar as mudanças.
7. **Validar a solução.** Repetir os testes, iniciar as aplicações, verificar os fluxos ponta a ponta e registrar os resultados.
8. **Entregar a rastreabilidade.** Relacionar cada achado à correção aplicada e ao teste que comprova o resultado.

### Regra mais importante

O arquivo `evaluation/answer-key.md` é um gabarito privado. Ele **não pode entrar no contexto da skill durante a auditoria**. O gabarito só deve ser consultado depois que o relatório da skill estiver concluído.

Também é obrigatório preservar a etapa de revisão humana: primeiro auditar e salvar o relatório; somente depois de uma aprovação explícita, alterar o código.

## Roteiro rápido

### 1. Verifique o baseline

Na raiz do repositório, execute as três suítes antes de usar a skill:

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

Guarde os comandos, resultados e eventuais falhas. Eles serão comparados com a execução posterior à refatoração.

### 2. Execute a auditoria

Forneça à skill somente os diretórios `langgraph-agent-platform/` e `polo-visits/`. Solicite que ela:

- reconheça stack, domínio, entradas, persistência, testes e arquitetura atual;
- identifique fronteiras de confiança e fluxos importantes;
- registre achados com severidade `CRITICAL`, `HIGH`, `MEDIUM` ou `LOW`;
- informe arquivo, linha, evidência, impacto, recomendação e forma de validação;
- consolide ocorrências que tenham a mesma causa-raiz;
- salve o relatório e pare antes de editar qualquer implementação.

### 3. Revise e aprove o escopo

Leia o relatório, confira as evidências no código e registre quais achados foram aceitos, rejeitados ou ajustados. A autorização para refatorar deve ser explícita.

### 4. Refatore e valide

Depois da aprovação, peça à skill para corrigir as causas-raiz aceitas. Ela deve preservar os contratos públicos e os fluxos legítimos ou documentar e migrar qualquer mudança necessária.

Ao final:

- repita os testes do baseline;
- inicie os três serviços;
- execute pelo menos um fluxo completo de cada projeto;
- adicione testes que reproduzam os problemas corrigidos;
- produza uma matriz `achado → correção → teste → resultado`.

## Execução das aplicações com Docker

Pré-requisito: Docker Engine com Docker Compose.

```bash
docker compose up --build -d
docker compose ps
```

Serviços disponíveis:

| Serviço | Endereço |
| --- | --- |
| Plataforma de agentes | `http://localhost:8000/docs` |
| API de idas ao polo | `http://localhost:8001/docs` |
| Interface de idas ao polo | `http://localhost:5173` |

Para encerrar:

```bash
docker compose down
```

### Testes isolados em containers

```bash
docker build --target test -t agent-platform-test -f langgraph-agent-platform/Dockerfile langgraph-agent-platform
docker run --rm agent-platform-test

docker build --target test -t polo-api-test -f polo-visits/backend/Dockerfile polo-visits/backend
docker run --rm polo-api-test

docker build --target test -t polo-web-test -f polo-visits/frontend/Dockerfile polo-visits/frontend
docker run --rm polo-web-test

docker build --target e2e -t polo-web-e2e -f polo-visits/frontend/Dockerfile polo-visits/frontend
docker run --rm --add-host=host.docker.internal:host-gateway polo-web-e2e
```

Os READMEs de cada projeto também apresentam instalação nativa, endpoints, chamadas HTTP e fluxos manuais.

## Projetos-alvo

### Plataforma de agentes

Diretório: `langgraph-agent-platform/`

- **Stack:** Python 3.12, FastAPI, LangGraph e SQLite.
- **Modelo:** simulador determinístico local, sem chave de API ou serviço externo.
- **Fluxos:** configuração de agentes, conversa, consulta de políticas, ferramenta de leitura, solicitação de notificação, interrupção HITL, aprovação ou recusa, retomada e histórico persistido.
- **Persistência:** agentes, conversas e checkpoints em SQLite.
- **Pontos principais:** `app/main.py`, `app/database.py`, `tests/` e `Dockerfile`.

Consulte [as instruções da plataforma de agentes](langgraph-agent-platform/README.md).

### Gestão de idas ao polo

Diretório: `polo-visits/`

- **Stack:** React com Vite no frontend; Python 3.12, FastAPI e SQLite no backend.
- **Domínio:** agendamento e registro de visitas presenciais a um polo fictício.
- **Fluxos:** consulta, pesquisa, criação, alteração e cancelamento de visitas, troca de perfil e resumo por status.
- **Persistência:** SQLite com dados demonstrativos de Ana e Bruno.
- **Pontos principais:** `backend/app`, `backend/tests`, `frontend/src` e os Dockerfiles de cada aplicação.

Consulte [as instruções da aplicação de visitas](polo-visits/README.md).

## Processo esperado da skill

### 1. Reconhecimento

Identificar linguagem, frameworks, dependências, entradas, persistência, testes, fronteiras de confiança, fluxos importantes e arquitetura atual.

### 2. Auditoria

Analisar código e configuração. Cada achado deve apresentar:

- causa concreta e severidade justificável;
- arquivo e linha;
- evidência reproduzível;
- impacto;
- recomendação;
- estratégia de validação.

Achados derivados do mesmo defeito-raiz não devem ser inflados artificialmente.

### 3. Revisão humana

Salvar o relatório e interromper o trabalho antes de qualquer alteração. A pessoa avaliadora decide se o escopo e as correções propostas estão adequados.

### 4. Refatoração

Após aprovação explícita, corrigir os problemas confirmados e melhorar os limites arquiteturais sem impor um padrão único. Apenas mover arquivos ou renomear símbolos não é suficiente.

### 5. Validação

Executar testes, iniciar as aplicações, repetir os fluxos ponta a ponta e acrescentar testes que falhem diante do comportamento vulnerável e passem com a correção. O relatório final deve registrar comandos e resultados.

## Critérios de aceite

| Área | Critério |
| --- | --- |
| Reconhecimento | Stack, domínio, estrutura, persistência e fluxos são descritos corretamente nos dois projetos. |
| Auditoria | Os achados têm causa concreta, severidade defensável, evidência e referência precisa. Duplicatas e suposições sem prova contam negativamente. |
| Cobertura | A análise encontra problemas relevantes de arquitetura, segurança e qualidade, com severidades variadas. |
| Revisão humana | Nenhum arquivo de implementação é alterado antes da aprovação do relatório. |
| Refatoração | As causas-raiz aceitas são corrigidas; mudanças apenas cosméticas não bastam. |
| Preservação | Conversa, HITL, persistência, CRUD de visitas, resumo e interface continuam funcionais. |
| Segurança | Os comportamentos indevidos deixam de ser reproduzíveis e passam a ter expectativas seguras. |
| Testes | Suítes Python e frontend passam, as aplicações iniciam e pelo menos um fluxo completo de cada projeto é verificado. |
| Rastreabilidade | A entrega final relaciona achado, mudança, teste e resultado. |

## Entregas esperadas

- Skill reutilizável e suas referências, no local exigido pela ferramenta escolhida e fora dos projetos-alvo.
- Um relatório de reconhecimento e auditoria para cada projeto, preservado antes da refatoração.
- Registro da revisão humana e da aprovação do escopo.
- Código refatorado dos dois projetos, com commits ou diff facilmente revisável.
- Testes novos ou ajustados que comprovem as correções e evitem regressões.
- Relatório final com a matriz `achado → correção → teste`, comandos executados, resultados e decisões que alteraram contratos.

## Avaliação cega e gabarito

Para fornecer uma cópia da raiz à skill sem expor o gabarito, gere um pacote que exclua `evaluation/`:

```bash
tar --exclude=evaluation --exclude=.git --exclude=node_modules -czf challenge-blind.tar.gz .
```

Em um repositório Git, também é possível gerar um ZIP somente com os arquivos públicos do desafio:

```bash
git archive --format=zip --output=challenge-blind.zip HEAD README.md compose.yaml langgraph-agent-platform polo-visits
```

Somente depois que a skill concluir o relatório, compare os achados com `evaluation/answer-key.md`. Avalie a correspondência pela causa-raiz e pelas evidências, não apenas por palavras iguais. Registre:

- verdadeiros positivos;
- achados parciais;
- falsos positivos;
- achados não encontrados;
- divergências de severidade;
- confirmação de que a correção eliminou o comportamento demonstrável.

## Estrutura do repositório

```text
.
├── README.md
├── compose.yaml
├── langgraph-agent-platform/
│   ├── app/
│   ├── tests/
│   ├── Dockerfile
│   └── README.md
├── polo-visits/
│   ├── backend/
│   ├── frontend/
│   └── README.md
└── evaluation/
    └── answer-key.md
```

## Origem e adaptação

O método foi inspirado no desafio [Criação de Skills — Refatoração Arquitetural Automatizada](https://github.com/devfullcycle/mba-ia-refactor-projects-skill): reconhecer o projeto, registrar achados com severidade e localização, submeter o relatório à revisão humana, refatorar e validar a aplicação.

Esta versão usa dois projetos novos: uma plataforma de agentes com LangGraph e uma aplicação React + FastAPI. A skill deve recomendar uma arquitetura coerente com cada contexto; MVC não é uma resposta predefinida. A avaliação também considera segurança, isolamento de estado, fluxos HITL, frontend e preservação observável de comportamento.

Este repositório entrega apenas os alvos legados e o gabarito de avaliação. Ele não contém nem executa a skill que será avaliada.
