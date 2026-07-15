# Implementation Plan: Nome Obrigatório na Avaliação + Mensagem Pronta ao Copiar o Link (132)

**Branch**: `132-nome-obrigatorio-mensagem-feedback` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

## Summary

Duas mudanças independentes sobre a feature 130:

1. `ClientFeedback` ganha `client_name` (obrigatório no envio público, opcional/`None`
   nas linhas antigas). Campo de nome no topo de `feedback/public.html`, validado no
   servidor junto da nota.
2. O botão "Pedir feedback da cliente" (`event_detail.html`) copia uma mensagem pronta
   (texto fixo fornecido) em vez do link cru — mesmo padrão de `buildConfirmacao()`/
   `buildCobranca()` já existentes no arquivo.

## Technical Context

**Stack**: o existente (Flask + SQLAlchemy + Jinja2 + JS vanilla). **Storage**: 1 coluna
nova — `client_feedbacks.client_name` (`String(200)`, `nullable=True` — nulo cobre
avaliações já enviadas antes desta mudança, FR-005; obrigatoriedade é imposta na validação
do formulário público, não no schema).

**Arquivos**:
- `migrations/versions/<hash>_client_feedback_name.py` — `ALTER TABLE client_feedbacks ADD
  COLUMN client_name VARCHAR(200)`.
- `app/models.py` — `ClientFeedback.client_name = db.Column(db.String(200), nullable=True)`.
- `app/feedback/routes.py::avaliar_submit` — lê `client_name = (request.form.get(
  "client_name") or "").strip()[:200]`; se vazio, mesma rota de erro já usada para nota
  inválida (`render_template("feedback/public.html", ..., error=...)`, preservando o
  restante do formulário); grava `client_name=client_name` no `ClientFeedback` criado.
- `app/templates/feedback/public.html` — novo campo de texto "Seu nome" no topo do
  `<form>`, antes do grupo de estrelas, `required` no HTML (validação client-side) +
  mensagem de erro do servidor já exibida no topo da página (reaproveita o bloco `{% if
  error %}` existente).
- `app/templates/event_detail.html` — dentro do IIFE que já define `buildConfirmacao()`/
  `buildCobranca()`: nova função `buildFeedbackMsg(url)` retornando o texto fixo do
  FR-006 (linhas literais do spec, com `url` interpolado no lugar de "Link aqui"); no
  wiring do `btn-feedback-cliente`, troca `copiar(data.url, bf)` por
  `copiar(buildFeedbackMsg(data.url), bf)`.
- `app/templates/event_detail.html` (painel "💬 Feedback da Cliente") e
  `app/templates/clientes/avaliacoes.html` (lista de avaliações + painel "Pontos de
  atenção") — exibem `fb.client_name` (ou um indicador tipo "Nome não informado" quando
  nulo, cobrindo avaliações antigas — FR-005) junto da nota/data já mostradas.

**Testing**: verificação funcional vs `manto_local` — envio sem nome é rejeitado (não
salva, mostra erro); envio com nome salva e nome aparece nas duas telas internas;
avaliação antiga (sem nome, simulada com `client_name=None`) continua aparecendo sem
quebrar a renderização; texto copiado bate exatamente com o modelo do FR-006, com a URL
real interpolada; link dentro da mensagem continua sendo o mesmo token reaproveitado
(gerar o link duas vezes não troca o token).

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar | ✅ Mensagem pronta segue o mesmo padrão já existente (`buildConfirmacao`/`buildCobranca`) no mesmo arquivo — só mais uma função `build*`, sem inventar um mecanismo novo. Erro de validação do nome reaproveita o mesmo bloco `{% if error %}`/rota de re-render já usado pela validação de nota (feature 130). |
| IV. Não quebrar | ✅ `client_name` é `nullable=True` no schema — avaliações antigas continuam existindo e sendo exibidas (FR-005); só o formulário público passa a exigir o preenchimento dali em diante. Link/token do evento não muda (FR-007) — a mudança é só no texto ao redor do link. |
| V. UI/UX | ✅ Erro de nome ausente usa a mesma indicação clara já usada para nota ausente (mensagem no topo da página, formulário preservado) — sem alterar o padrão de feedback visual já estabelecido. |
| VI. Planejar | ✅ Este plano, escrito depois de reler o código exato de `feedback/routes.py`, `feedback/public.html` e o bloco de mensagens de `event_detail.html` (features 130/131) para reaproveitar a estrutura já existente. |
| VIII. Mobile-first | ✅ Aplica-se à página pública `/avaliar/<token>` — o campo de nome segue o mesmo estilo mobile-first já usado pelos demais campos daquela tela (mesma classe de input, mesmo espaçamento). |

**Gate: PASS.**

## Decisões

1. **`client_name` nulo no schema, obrigatório só na validação do formulário**: evita uma
   migration de "preencher retroativamente" dados que não existem para avaliações
   antigas — e mantém a mesma convenção já usada para `comment` (`nullable=True`) na
   feature 130.
2. **Texto da mensagem fixo, sem saudação dinâmica**: o texto pedido já tem sua própria
   abertura ("Olá! Como vai?") — usar a função `saudacao()` (Bom dia/Boa tarde/Boa noite)
   dos outros botões substituiria ou duplicaria essa abertura sem necessidade; o pedido do
   usuário foi por um texto específico, não por adaptação ao padrão dos outros botões.
3. **Nome não bloqueia a revelação progressiva de estrelas/cards**: só é cobrado no envio
   final (mesma mecânica de "campo obrigatório" de qualquer form) — inventar um gate
   adicional (ex.: "só mostra as estrelas depois do nome") não foi pedido e adicionaria um
   passo a mais numa página cujo objetivo é ser rápida de preencher no celular.
