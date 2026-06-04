# Revisão do módulo de Orçamento

**Data**: 2026-06-04 | **Autor**: revisão técnica (Claude) | **Escopo**: `app/orcamento/*` +
`app/static/js/orcamento.js` + `app/templates/orcamento/*`

> Objetivo: registrar os pontos de complexidade/risco que fazem a tela "sair do padrão", com uma
> recomendação para cada um. **Nada aqui foi refatorado nesta entrega** (decisão: fazer separado e
> com calma, pois mexe no cálculo de dinheiro). Itens já corrigidos na feature 019 estão marcados ✅.

## Veredito geral

A calculadora **funciona e os cálculos conferem**, mas a manutenção é arriscada por causa de
**duplicação de lógica** e **valores fixos espalhados**. Não há bug de cálculo evidente; o risco é
de *divergência futura* (alguém muda um lado e esquece o outro).

## Achados

### 1. Cálculo duplicado: servidor × navegador  (RISCO ALTO)
A mesma regra de preço existe em dois lugares que precisam ser mantidos iguais à mão:
- **Servidor**: `app/orcamento/pricing.py` + `_process_quote` em `app/orcamento/routes.py`.
- **Navegador**: `calcTotals()` e `updateDebugPanel()` em `app/static/js/orcamento.js`.

Hoje o JS calcula o preview ao vivo e o servidor recalcula no envio. Se as duas implementações
divergirem (ex.: mudou markup só num lado), o vendedor vê um valor e o sistema grava outro.

**Recomendação**: ter **uma fonte única**. Opção mais segura: o navegador pede o cálculo ao
servidor (endpoint de "preview") em vez de reimplementar a fórmula. Migrar aos poucos, comparando o
resultado dos dois antes de remover o cálculo do JS.

### 2. Configuração de preços como JSON no banco  (RISCO MÉDIO)
Os preços vivem num campo JSON (`SiteSetting.pricing_config`), não em tabelas. Além disso, a função
`load()` roda `_migrate()` **a cada leitura** — ou seja, lógica de migração de formato misturada com
a leitura, em todo request.

**Consequências**: difícil de consultar/auditar; migrações de formato "escondidas" no `load()`;
sem histórico de quem mudou qual preço.

**Recomendação**: manter o JSON por enquanto (funciona), mas (a) rodar a migração **uma vez** ao
salvar/abrir o painel, não a cada leitura; (b) avaliar, num passo futuro, normalizar em tabela de
preços com histórico. Baixa prioridade frente ao item 1.

### 3. Valores fixos espalhados (hardcode)  (RISCO MÉDIO)
Mesmo número repetido em vários lugares, fora do config:
- **BGE** `+R$130` (dinossauro) / `+R$70` (transformers): em `routes.py`, em `orcamento.js` e nos
  rótulos do `<select>` — **3 lugares**.
- **Adicional noturno** `R$50/pessoa`: `_ADICIONAL_NOTURNO` no `routes.py` **e** `50` solto no JS.
- **Show customizado** `+R$50/artista`, **brinde** show, **markup de serviço** `1.5×` (técnico e
  maquiador), **Nota Fiscal** `/0.84`: fixos em código (servidor e/ou JS).
- ✅ **Dica "(+R$100)/(+R$20)" do cantor** (era hardcode só no JS) — **removida na 019**.

**Recomendação**: mover esses números para o `pricing_config` (ou um bloco de constantes único) e
ler dos dois lados — idealmente resolvido junto com o item 1.

### 4. Falha silenciosa ao ler o config  ✅ (corrigido na 019)
`load()` usava `except Exception: pass` — config corrompida caía nos preços padrão **sem avisar**.
Agora registra no log antes do fallback (mantém a tela funcionando).

### 5. `orcamento.js` muito grande  (RISCO BAIXO)
~1.200 linhas concentrando estado, cálculo, render de linhas, debug, histórico e personalização.
**Recomendação**: ao mexer no item 1, quebrar em arquivos menores (estado, cálculo, UI).

## Ordem sugerida (do mais seguro ao mais arriscado)
1. ✅ (feito) Consistência do cantor + log no `load()` + dropdown ao adicionar (feature 019).
2. Centralizar os valores fixos (item 3) no config — médio, mexe em cálculo: testar com cenários.
3. Migração do config uma vez (item 2a) — pequeno.
4. Fonte única de cálculo (item 1) — maior; fazer por último, comparando os dois lados antes de
   desligar o cálculo do JS.
5. Modularizar o `orcamento.js` (item 5) — junto com o passo 4.

> Cada passo desses deve ser uma feature spec-kit própria, com verificação de que os **valores
> calculados não mudam** para os mesmos inputs.
