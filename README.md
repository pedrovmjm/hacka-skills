# Desafio de auditoria e refatoracao de projetos legados

Este repositorio e um conjunto de avaliacao para uma futura skill capaz de reconhecer uma codebase, auditar arquitetura, seguranca e qualidade, produzir um relatorio revisavel, refatorar com criterio e provar que os fluxos continuam funcionando. Os alvos sao dois sistemas ficticios, executaveis localmente, com stacks e dominios diferentes.

> Os projetos contem comportamentos deliberadamente inadequados. Eles existem para avaliacao em ambiente local e nao devem ser publicados como sistemas de producao. Nenhuma credencial ou dado pessoal real e usado.

## Origem e adaptacao

O metodo foi inspirado no desafio [Criação de Skills — Refatoração Arquitetural Automatizada](https://github.com/devfullcycle/mba-ia-refactor-projects-skill): reconhecer o projeto, registrar achados com severidade e localizacao, submeter o relatorio a revisao humana, refatorar e validar a aplicacao.

Esta versao muda o objeto da avaliacao. Em vez dos tres projetos Flask/Express originais e de uma migracao obrigatoria para MVC, ha dois projetos novos: uma plataforma de agentes com LangGraph e uma aplicacao React + FastAPI. A skill futura devera recomendar uma arquitetura coerente com cada contexto; MVC nao e uma resposta predefinida. Tambem se exige que ela trate seguranca, isolamento de estado, fluxos HITL, frontend e preservacao observavel de comportamento.

Este repositorio entrega os alvos legados e o gabarito de avaliacao. Ele nao contem nem executa a skill que sera avaliada.

## Projetos-alvo

### 1. Plataforma de agentes

Diretorio: `langgraph-agent-platform/`

- Stack: Python 3.12, FastAPI, LangGraph e SQLite.
- Modelo: simulador deterministico, sem chave de API e sem servico externo.
- Fluxos: consultar/configurar agentes; conversar; consultar politicas; executar ferramenta local; solicitar envio de notificacao; interromper o grafo; aprovar ou recusar; retomar a execucao; recuperar historico persistido.
- Persistencia: agentes e conversas em SQLite, com checkpoints do LangGraph tambem em SQLite.
- Estrutura principal: `app/main.py`, `app/database.py`, `tests/` e `Dockerfile`.

Instrucoes e exemplos: [`langgraph-agent-platform/README.md`](langgraph-agent-platform/README.md).

### 2. Gestao de idas ao polo

Diretorio: `polo-visits/`

- Dominio: agendamento e registro de visitas presenciais a um polo ficticio. Uma "ida ao polo" e uma visita com data, horario, finalidade, observacoes, quantidade de acompanhantes e status.
- Stack: React + Vite no frontend; Python 3.12, FastAPI e SQLite no backend.
- Fluxos: consultar visitas; pesquisar; agendar; alterar; cancelar; trocar o perfil ficticio; visualizar resumo por status.
- Persistencia: SQLite com dados de demonstracao de Ana e Bruno.
- Estrutura principal: `backend/app`, `backend/tests`, `frontend/src` e Dockerfiles por aplicacao.

Instrucoes e exemplos: [`polo-visits/README.md`](polo-visits/README.md).

## Processo esperado da futura skill

1. **Reconhecimento do projeto:** identificar linguagem, frameworks, dependencias, entradas, persistencia, testes, fronteiras de confianca, fluxos importantes e arquitetura atual.
2. **Auditoria:** analisar codigo e configuracao; produzir achados classificados como CRITICAL, HIGH, MEDIUM ou LOW; apontar arquivo e linha; incluir evidencia, impacto, recomendacao e forma de validacao. Achados sobre o mesmo defeito-raiz nao devem ser inflados artificialmente.
3. **Revisao humana:** salvar o relatorio e interromper o trabalho antes de qualquer edicao. A pessoa avaliadora decide se o escopo e as correcoes propostas estao adequados.
4. **Refatoracao:** apos aprovacao explicita, corrigir os problemas confirmados e melhorar limites arquiteturais sem impor um padrao unico. Contratos publicos e fluxos legitimos devem ser preservados ou ter qualquer mudanca justificada e migrada.
5. **Validacao:** instalar dependencias, executar testes, iniciar as aplicacoes, repetir os fluxos ponta a ponta e acrescentar testes que falhem no legado e passem na versao corrigida. O relatorio final deve registrar comandos e resultados.

## Criterios de aceite

| Area | Criterio |
| --- | --- |
| Reconhecimento | Stack, dominio, estrutura, persistencia e fluxos sao descritos corretamente nos dois projetos. |
| Qualidade da auditoria | Achados tem causa concreta, severidade defensavel, evidencia e referencia precisa a arquivo/linha. Duplicatas e suposicoes sem prova contam negativamente. |
| Cobertura | A auditoria encontra problemas relevantes de arquitetura, seguranca e qualidade em ambos os projetos e cobre severidades variadas. |
| Revisao humana | Nenhum arquivo de implementacao e alterado antes da aprovacao do relatorio. |
| Refatoracao | As causas-raiz aceitas sao corrigidas; apenas reorganizar arquivos ou renomear simbolos nao basta. |
| Preservacao | Conversacao, HITL, persistencia, CRUD de visitas, resumo e interface continuam funcionais. |
| Seguranca | As verificacoes que reproduzem comportamentos indevidos deixam de reproduzi-los e sao substituidas ou complementadas por expectativas seguras. |
| Testes | Suites Python e frontend passam; aplicacoes iniciam; ao menos um fluxo completo de cada projeto e verificado. |
| Rastreabilidade | Entrega final relaciona achado, mudanca, teste e resultado. |

## Entregas esperadas de quem resolver

- A skill reutilizavel e suas referencias, fora dos projetos-alvo ou no local exigido pela ferramenta escolhida.
- Um relatorio de reconhecimento e auditoria para cada projeto, preservado antes da refatoracao.
- Registro da aprovacao humana do escopo.
- Codigo refatorado dos dois projetos, com commits ou diff facilmente revisavel.
- Testes novos ou ajustados que comprovem as correcoes e evitem regressoes.
- Relatorio final com matriz `achado -> correcao -> teste`, comandos executados, resultados e decisoes que alteraram contratos.

## Execucao rapida com Docker

Pre-requisito: Docker Engine com Compose.

```bash
docker compose up --build -d
docker compose ps
```

Servicos:

- plataforma de agentes: `http://localhost:8000/docs`
- API de idas ao polo: `http://localhost:8001/docs`
- interface de idas ao polo: `http://localhost:5173`

Para encerrar:

```bash
docker compose down
```

Os READMEs dos projetos mostram instalacao nativa, chamadas HTTP e suites de teste. Para testar em containers sem depender dos runtimes da maquina:

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

As suites completas usam as dependencias de desenvolvimento descritas em cada projeto.

## Validacao antes e depois da refatoracao

Antes de executar a skill, rode todas as suites e guarde os resultados como baseline:

```bash
cd langgraph-agent-platform
python -m pytest -q

cd ../polo-visits/backend
python -m pytest -q

cd ../frontend
npm install
npm test
npm run build
```

Depois da refatoracao, repita exatamente esses comandos, suba os tres servicos e execute os fluxos manuais documentados nos READMEs. Testes de caracterizacao podem precisar ter suas expectativas atualizadas quando documentam um comportamento que foi deliberadamente corrigido; nesse caso, o diff deve mostrar a nova expectativa segura.

## Avaliacao cega e gabarito

O gabarito privado da primeira validacao fica em `evaluation/answer-key.md`. Ele nao deve entrar no contexto da skill: apontar a ferramenta somente para `langgraph-agent-platform/` e `polo-visits/` e a opcao mais simples. Se for necessario fornecer uma copia da raiz, crie um pacote sem `evaluation/`:

```bash
tar --exclude=evaluation --exclude=.git --exclude=node_modules -czf challenge-blind.tar.gz .
```

Em um repositorio Git, outra alternativa e criar explicitamente um arquivo somente com os alvos:

```bash
git archive --format=zip --output=challenge-blind.zip HEAD README.md compose.yaml langgraph-agent-platform polo-visits
```

Somente depois que a skill concluir o relatorio, compare-o com o gabarito. Avalie correspondencia por causa-raiz e evidencia, nao apenas por palavras iguais. Registre verdadeiros positivos, achados parciais, falsos positivos, achados nao encontrados, severidade divergente e se a correcao eliminou o comportamento demonstravel. O conteudo dos achados nao e repetido neste README para preservar a avaliacao cega.

## Estrutura

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
