# Gate de verificação (anti falso-positivo)

Todo candidato passa por estas perguntas **antes** de virar achado. Registre as respostas
de forma resumida no campo "Evidência" do achado.

## Perguntas obrigatórias

1. **Alcançabilidade:** existe um caminho de uma entrada real (rota, UI, ferramenta, CLI) até
   o trecho? Cite a cadeia, por exemplo: `POST /chat` → `route()` → `tool_read()` → `open(path)`.
2. **Controle do atacante:** o dado que chega ao *sink* é controlado por quem não deveria?
3. **Mitigação existente:** há validação, middleware, dependência de auth, schema, proxy ou
   constraint de banco que já impede o problema? Leia de fato, não presuma.
4. **Reprodução:** é possível demonstrar com teste existente, `curl`, script ou leitura completa
   do fluxo? Prefira reprodução executável em ambiente local.
5. **Causa-raiz única?** Outro candidato tem a mesma origem? Se sim, consolide.
6. **Linha exata:** o `arquivo:linha` aponta para o trecho causador, não só para o sintoma.

## Níveis de confiança

A nota numérica segue a escala do `anthropics/claude-code-security-review`.

| Confiança | Nota | Critério | Entra no relatório? |
| --- | --- | --- | --- |
| **Confirmado** | 0,9–1,0 | Caminho de exploração reproduzido (teste, requisição) ou fluxo integralmente lido sem mitigação | Sim |
| **Provável** | 0,8–0,9 | Padrão claro de vulnerabilidade, sem reprodução dinâmica por limitação de ambiente | Sim, marcado como "Provável" |
| **Hipótese** | 0,7–0,8 | Depende de condição específica ou suposição não verificada | Só em "Observações" |
| **Descartado** | < 0,7 | Especulativo, mitigado ou inalcançável | Não |

## Exclusões fixas (não reportar, salvo impacto comprovado)

Adaptadas das *hard exclusions* do `claude-code-security-review`:
- DoS, falta de rate limiting e esgotamento de memória/CPU.
- Validação ausente em campo **sem** efeito de segurança ou de regra de negócio demonstrado.
  Se o efeito existir (ex.: data inválida infla uma meta), reporte o efeito, não "falta validação".
- Open redirect sem cadeia de exploração.
- Boas práticas genéricas ("usar HTTPS", "adicionar logs") sem defeito concreto no código.
- Achados em código de teste, exemplo ou script que não roda em produção. Exceção: um teste que
  fixa o comportamento inseguro, que vale como evidência de outro achado e não como achado próprio.

## Sinais de falso positivo
- Código de teste, exemplo ou script de desenvolvimento não implantado.
- Valor aparentemente perigoso que é constante e não vem de entrada externa.
- ORM/driver que parametriza automaticamente.
- Framework que escapa por padrão (React escapa `{texto}`; só `dangerouslySetInnerHTML` não).

## Sinais de achado subestimado
- Um teste existente **afirma** o comportamento inseguro, o que confirma o achado e indica o risco de regressão.
- O identificador "secreto" aparece em respostas, URLs, logs ou listagens.
- A ferramenta é acionável por texto livre de usuário (agentes LLM).
