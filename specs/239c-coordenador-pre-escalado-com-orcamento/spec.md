# Hotfix 239c — o coordenador escolhido na criação some quando o evento vem do orçamento

**Branch**: `239c-coordenador-pre-escalado-com-orcamento` · **Created**: 2026-10-30 · **Status**: Pronto ·
**Migration**: nenhuma

## O pedido

O dono (30/10): "A comercial Thays vendeu um evento e colocou a Miminha para ser a coordenadora pré-escalada.
Mas quando o evento foi criado, ela não estava." Evento 1432, `(R&I) MICKEY - TRADICIONAL`, 20/12/2026, criado
pela Thays em 29/10 às 20h50 a partir de um orçamento. Em produção, a vaga de Coordenador nasceu aberta, com o
teto de R$ 300 do orçamento e a marca do sistema; a Miminha entrou às 21h22, pelo casting, à mão.

## Causa

`_apply_default_roles` (`app/calendar/routes.py`) só aplicava `coordinator_talent_id` quando o evento NÃO vinha do
orçamento (`came_from_orcamento = bool(orc_caches)`). A trava é herança do tempo em que a vaga de Coordenador do
orçamento chegava dentro de `characters` (152); a 239 passou a criá-la no servidor
(`_create_extra_roles_from_orcamento`) e manteve a trava, documentando-a no docstring. Nenhuma regra de negócio a
pedia. O formulário mostra o campo "Coordenador específico" em qualquer caso, então a escolha da comercial era
descartada sem aviso — e, sem `assigned_now`, o coordenador também não recebia convite (233). A edição
(`event_ops._reconcile_characters`) sempre aplicou a escolha; por isso pôr depois funcionava.

## O que muda

- `_apply_default_roles` perde o parâmetro `came_from_orcamento`. Com coordenador escolhido (talento ativo, não
  escalado num personagem do mesmo formulário), ele ocupa a **primeira vaga de Coordenador aberta** — a do
  orçamento, que mantém o teto e a marca do sistema e ganha `escalado_pelo_comercial`. Sem vaga aberta (evento sem
  orçamento, ou orçamento sem coordenador), nasce uma, como antes. Sem escolha, `_ensure_coordinator` como antes.
- Orçamento com 2+ coordenadores: o escolhido ocupa a primeira; as outras seguem abertas, com teto.
- O escolhido entra em `assigned_now`: recebe convite e aviso de conflito de agenda, como a pré-escala de personagem.

## Verificação

`verify_239c.py` contra o `manto_local` (Google dublado, e-mail suprimido): **7/7**. Cenários 1–3 falham no código
antigo (rodado com a correção em stash: `talent_id=None`, `invite_status=None`, ocupação `[None, None]`).
Regressão: `verify_322.py` 29/29 (mesmo caminho de criação, marcas do sistema e do comercial). `ruff check` sem erro
novo (o I001 de `routes.py` é do bloco de imports, anterior).

## Fora de escopo

- O evento 1432 já está certo (a Miminha foi posta à mão); nada a corrigir nos dados.
- Aviso na tela quando a escolha não pode ser aplicada (talento já escalado num personagem): segue silencioso,
  como sempre foi sem orçamento.
