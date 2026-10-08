# Formato de achado

Use o **formato completo** para CRITICAL, HIGH e MEDIUM e o **formato compacto** para LOW.
Os campos de metadados ficam em lista para não se fundirem no Markdown renderizado.

## Formato completo

### <ID> · <Título que diz o problema e onde, ex.: "Qualquer pessoa lê qualquer arquivo do servidor pela ferramenta de leitura">

- **Severidade:** <SEVERIDADE> (impacto <1-4> × probabilidade <1-3><, ajuste ±1: motivo>). <Justificativa em 1 frase.>
- **Tipo:** Vulnerabilidade | Bug | Dívida técnica
- **Categoria:** `<SEC-…>` / CWE-<n> · **Confiança:** Confirmado (0,9) | Provável (0,8)
- **Local:** `caminho/arquivo.ext:L1-L2`<, `outro.ext:L`>

**Evidência**

```<linguagem>
<trecho mínimo, no máximo 8 linhas>
```

- **Cenário:** <Vulnerabilidade: quem explora e como. Bug: em que uso normal o erro aparece.>
- **Reprodução:** `<um comando, requisição ou teste>` → <resultado observado>
- **Esperado:** <o que deveria acontecer>
- **Atual:** <o que acontece>
- **Impacto:** <quem é afetado e o que se perde, em 1-2 frases. Não repita a justificativa.>

**O que fazer**<, depois de `<ID>` se depender de outro achado>

1. <Ação concreta sobre a causa-raiz: o que mudar, em qual arquivo/função>
2. <Ação seguinte, se houver>

```<linguagem>
<esboço curto da correção, no máximo 10 linhas, quando ajudar>
```

**Validação:** <teste novo: asserção esperada> · <fluxo legítimo que deve continuar funcionando>

## Formato compacto (LOW)

### <ID> · <Título>

- **Severidade:** LOW (impacto <n> × probabilidade <n>). <Justificativa curta.>
- **Tipo / Categoria:** <Tipo> · `<categoria>` / CWE-<n> · **Confiança:** <…>
- **Local:** `arquivo:linha`
- **Evidência:** `<trecho de 1 linha ou fato observado>`
- **Esperado / Atual / Impacto:** <uma frase para cada, separadas por " · ">
- **O que fazer:** <1-2 passos concretos em uma linha>
- **Validação:** <como verificar>
