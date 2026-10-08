# Checklist de arquitetura e qualidade

Achados desta lista só entram no relatório com **consequência concreta**: um bug observável,
um risco, uma regra impossível de testar ou um custo de mudança demonstrável. Não imponha uma
arquitetura específica (MVC, hexagonal etc.). Proponha limites coerentes com a stack e o domínio.

## A. Responsabilidades e acoplamento
- [ ] Rotas/handlers concentram regra de negócio, SQL, serialização e efeitos colaterais no mesmo bloco?
- [ ] A regra de domínio crítica (cálculo de meta, decisão de aprovação) pode ser testada sem HTTP/banco?
- [ ] Módulo "deus" (`main.py`, `App.jsx` com centenas de linhas) mistura camadas?
- [ ] Dependências ocultas: singletons, variáveis globais, conexões criadas no import.
- [ ] Fronteiras invertidas: domínio importando framework web, frontend duplicando regra do backend.

## B. Estado e concorrência
- [ ] Estado mutável em nível de módulo compartilhado entre requisições/usuários (dicts globais, caches, configuração do agente).
- [ ] Padrão ler-modificar-escrever sem transação/lock/constraint (contadores, saldos, metas, "check then insert").
- [ ] SQLite: `check_same_thread=False` com conexão compartilhada; ausência de `UNIQUE` em chaves naturais; falta de `commit`/`rollback`.
- [ ] Idempotência: repetir a requisição duplica efeito?

## C. Validação e regras de domínio
- [ ] Tipos e faixas validados (Pydantic `Field`, `Literal`, `constr`, datas válidas, futuras/passadas).
- [ ] Enum/estado como string livre.
- [ ] Datas e fuso horário: `datetime.now()` sem tz, comparação de strings de data, mês/ano limites.
- [ ] Regra implementada só no frontend.

## D. Tratamento de erros
- [ ] `except Exception: pass` ou retorno de sucesso após falha.
- [ ] Códigos HTTP incorretos (200 com erro, 500 para entrada inválida).
- [ ] Mensagens de erro vazando internals (cruzar com `SEC-DATA`).

## E. Persistência
- [ ] Esquema criado em runtime sem migração; colunas sem constraint; JSON em texto sem validação.
- [ ] Caminho de banco relativo ao CWD (comportamento diferente entre teste, Docker e dev).
- [ ] N+1 ou consultas sem índice em fluxo quente (só se houver impacto real).

## F. Frontend
- [ ] Estado derivado duplicado; efeitos sem dependências corretas; condição de corrida em fetch (resposta antiga sobrescreve nova).
- [ ] URL da API hard-coded; tratamento de erro de rede ausente (UI fica inconsistente).
- [ ] Controles sem rótulo/teclado (acessibilidade), normalmente LOW.
- [ ] Componentes gigantes que impedem teste; lógica de negócio na UI.

## G. Testes
- [ ] Fluxos críticos sem teste (autorização, HITL, regra de meta).
- [ ] Testes que **afirmam o comportamento vulnerável**. Registre isso como evidência e como risco de regressão.
- [ ] Testes dependentes de ordem/estado global; banco compartilhado entre testes.

## H. Manutenção
- [ ] Código morto, duplicação relevante, magic numbers de regra de negócio, nomes enganosos.
- [ ] Configuração espalhada (constantes em vários arquivos).
- [ ] Dependências sem pin; Dockerfile não reprodutível.
