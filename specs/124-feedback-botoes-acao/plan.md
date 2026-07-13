# Implementation Plan: Feedback Visual em Todo Botão de Ação (124)

**Branch**: `124-feedback-botoes-acao` | **Date**: 2026-07-13 | **Spec**: [spec.md](./spec.md)

## Summary

O painel interno já tem um guard global contra duplo envio em `app/templates/base.html`
(feature 107): todo `<form>` desabilita seus botões ao ser enviado. O gap é que
`disabled` sozinho não muda a aparência do botão (nenhuma regra CSS trata esse estado) —
por isso o clique "some" aos olhos de quem usa. A correção: (1) o mesmo guard passa a
adicionar uma classe `.is-loading` nos botões envolvidos, com o `disabled` nativo; (2) uma
regra CSS nova em `style.css` torna esse estado visivelmente diferente (opacidade
reduzida, cursor de carregamento, reticências) para qualquer `.btn` do sistema, sem tocar
em nenhum template; (3) um `pageshow` com `event.persisted` restaura o estado normal ao
voltar do cache do navegador (bfcache do Safari/iOS — o navegador do incidente).

Os formulários públicos de pré-contrato (feature 118/123) já implementam "Enviando…"
corretamente em `_form_scripts.html` — não são tocados (FR-007).

## Technical Context

**Stack**: o existente (Jinja2 + JS vanilla, CLAUDE.md). **Storage**: nenhuma mudança.

**Arquivos**: `app/templates/base.html` (guard global existente — adiciona classe
`.is-loading` + listener `pageshow`), `app/static/style.css` (regra `.btn:disabled` /
`.btn.is-loading` nova), `.specify/memory/constitution.md` (já emendado: v1.3.0→v1.4.0,
Princípio V + item no portão de qualidade — feito antes desta spec).

**Testing**: verificação funcional/visual no app real (não é lógica de backend — é
comportamento de front-end). Confirma via leitura do HTML renderizado que a classe
`.is-loading` é aplicada pelo JS em qualquer tela testada (gastos extras, uma tela com
`confirm()` de exclusão) e que a regra CSS existe e se aplica ao seletor certo. Testado no
app real em viewport mobile (o incidente foi em iPhone).

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar | ✅ Estende o guard global já existente (feature 107) em vez de criar um novo mecanismo paralelo — zero duplicação. Formulários públicos mantêm a própria implementação (já correta), sem forçar consolidação arriscada de código que já funciona. |
| II. Padrões Python | N/A — mudança é JS/CSS/constituição, sem Python. |
| III. Camadas | N/A — front-end puro, sem lógica de negócio. |
| IV. Não quebrar | ✅ Guard global continua desabilitando exatamente como antes (comportamento funcional idêntico); só adiciona uma classe CSS a mais. `event.defaultPrevented` continua respeitado (envios cancelados por validação/`confirm()` negado nunca acionam o estado de loading — FR-004). |
| V. UI/UX | ✅ É a própria correção do Princípio V (reforçado nesta mesma feature). Cores via variável CSS existente (`opacity`, sem cor nova hardcoded). |
| VI. Planejar | ✅ Este plano; constituição emendada antes do plano (Princípio VI: correções de princípio antes da implementação). |
| VII. Moeda BR | N/A. |
| VIII. Mobile-first | ✅ Tela interna (painel), mas o incidente que motivou a feature foi mobile (iPhone) — comportamento verificado em viewport mobile mesmo não sendo superfície pública. |

**Gate: PASS.**

## Decisões

1. **Não reescrever para JS framework/lib nova**: a correção inteira cabe em ~10 linhas de
   JS (já existentes, só estendidas) + uma regra CSS — qualquer coisa maior violaria YAGNI.
2. **Não tocar nos formulários públicos** (`_form_scripts.html`): já implementam "Enviando…"
   corretamente de forma independente; consolidar as duas implementações em uma só
   traria risco de regressão numa superfície pública crítica (captação de contrato) por um
   ganho pequeno (reduzir ~8 linhas duplicadas) — Princípio IV (não quebrar o que funciona)
   pesa mais que a duplicação aqui. Registrado como duplicação conhecida e aceita.
3. **Auditoria de botões `onclick`/JS puro fora de escopo**: o guard global só resolve
   `<form>` — cobre a esmagadora maioria das telas do painel (inclusive a que gerou o
   incidente). Uma varredura de todo `onclick` do sistema é tarefa maior, sem gatilho
   concreto além do princípio geral; fica registrada na constituição (item do portão de
   qualidade) como responsabilidade contínua, não uma tarefa desta feature.
4. **`.is-loading` via classe CSS, não troca de `textContent`**: evita apagar ícones (SVG)
   dentro de botões — o mesmo problema que uma abordagem ingênua de "trocar o texto para
   Enviando…" teria em botões com ícone. Opacidade + cursor + reticências via `::after` dão
   sinal visível sem tocar no conteúdo do botão.
