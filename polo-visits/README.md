# Meu Polo — controle de presença

Aplicação fictícia para registrar os dias de trabalho presencial no polo. Cada pessoa acompanha um calendário mensal, marca se foi ou não ao polo e monitora o progresso até a meta de **8 dias por mês**.

O app também possui uma visão de gestor, com o consolidado mensal da equipe e o progresso individual de cada integrante.

> Projeto demonstrativo, sem vínculo com o Itaú. A identidade branca, laranja e azul é usada somente como referência visual para o desafio.

## Funcionalidades

### Minha presença

- calendário mensal com navegação entre meses;
- meta de 8 dias presenciais;
- total realizado, ausências, dias restantes e percentual da meta;
- marcação de cada data como `Fui ao polo` ou `Não fui`;
- edição e remoção de marcações feitas por engano;
- observação opcional por dia;
- troca entre perfis fictícios.

### Visão do time

- consolidado mensal da equipe;
- quantidade de dias presenciais por pessoa;
- progresso individual em relação à meta de 8 dias;
- total e média de presenças do time;
- detalhe dos dias marcados por integrante.

## Execução rápida com Docker

Na raiz do repositório:

```bash
docker compose up --build -d polo-api polo-web
docker compose ps
```

Acesse:

- interface: `http://localhost:5173`;
- documentação da API: `http://localhost:8001/docs`;
- health check: `http://localhost:8001/health`.

Para encerrar:

```bash
docker compose down
```

Use `docker compose down -v` somente quando quiser apagar os bancos persistidos e recriar os dados fictícios.

## Arquitetura do backend

O backend usa arquitetura hexagonal. FastAPI e SQLite ficam nas bordas, enquanto os casos de uso dependem apenas das portas do domínio.

```text
backend/app/
├── domain/                    # Modelos, erros e portas
├── application/               # Casos de uso de presença
├── adapters/
│   ├── http/                  # Adaptador de entrada FastAPI
│   └── persistence/           # Adaptador de saída SQLite
├── main.py                    # Composição das dependências
└── database.py                # Fachada de compatibilidade
```

```text
HTTP/FastAPI -> casos de uso -> porta do domínio <- SQLite
```

Essa organização é estrutural. Os comportamentos inseguros usados pelo benchmark continuam intencionalmente preservados para que a futura skill consiga encontrá-los e corrigi-los.

## API

| Método | Caminho | Uso |
| --- | --- | --- |
| GET | `/health` | Verifica o estado da API. |
| GET | `/api/attendance?user_id=ana&month=2026-09` | Retorna calendário e progresso pessoal do mês. |
| PUT | `/api/attendance/{data}` | Cria ou altera a marcação de uma data. |
| DELETE | `/api/attendance/{data}?user_id=ana` | Remove uma marcação feita por engano. |
| GET | `/api/team-attendance?manager_id=ana&month=2026-09` | Retorna o consolidado da equipe. |

As requisições usam perfis fictícios e enviam o cabeçalho `X-User`.

Exemplo de marcação:

```bash
curl -X PUT http://localhost:8001/api/attendance/2026-09-28 \
  -H "Content-Type: application/json" \
  -H "X-User: ana" \
  -d '{"user_id":"ana","status":"present","notes":"Trabalho no polo"}'
```

## Instalação nativa do backend

No PowerShell:

```powershell
cd polo-visits\backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8001
```

No macOS ou Linux, ative o ambiente com `source .venv/bin/activate`.

O banco padrão fica em `backend/data/polo.db`. A variável `POLO_DB_PATH` permite selecionar outro arquivo.

### Testes do backend

```bash
cd polo-visits/backend
python -m pytest -q
```

Alternativa com Docker:

```bash
docker build --target test -t polo-api-test polo-visits/backend
docker run --rm polo-api-test
```

## Instalação nativa do frontend

Com a API na porta 8001:

```bash
cd polo-visits/frontend
npm install
npm run dev
```

Acesse `http://localhost:5173`.

### Testes e build

```bash
npm test
npm run build
```

Alternativa com Docker:

```bash
docker build --target test -t polo-web-test polo-visits/frontend
docker run --rm polo-web-test
```

### Teste ponta a ponta

Com os serviços do Compose em execução:

```bash
docker build --target e2e -t polo-web-e2e polo-visits/frontend
docker run --rm --add-host=host.docker.internal:host-gateway polo-web-e2e
```

## Roteiro manual de validação

1. Abra `http://localhost:5173` na aba **Minha presença**.
2. Confirme a meta mensal de 8 dias e as marcações iniciais.
3. Selecione um dia e marque **Fui ao polo**.
4. Altere a mesma data para **Não fui**.
5. Limpe a marcação e confirme que o dia voltou ao estado neutro.
6. Navegue para o mês anterior e retorne ao atual.
7. Troque entre os perfis fictícios.
8. Abra a aba **Visão do time**.
9. Confira total, média e progresso de cada integrante.
10. Selecione uma pessoa e confira os dias registrados no calendário ou detalhe mensal.
