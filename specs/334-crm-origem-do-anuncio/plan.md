<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: 334 — De qual anúncio veio cada cliente

**Branch**: `334-crm-origem-do-anuncio` (sobre a `333-crm-orcamento-na-conversa`) | **Data**: 2026-11-04 | **Spec**:
[spec.md](./spec.md)

## Resumo

O `referral` que a Meta manda na mensagem de quem clicou num anúncio vira um contato registrado na conversa
(`conversa_anuncios`). A campanha vem de uma consulta à Meta pelo ID do anúncio, guardada em `anuncios_meta`.
- A ficha guarda o primeiro e o mais recente anúncio e, no primeiro, a origem e a campanha nos campos de atribuição que
  o Desempenho já lê.
- A ficha nova que chegou sem anúncio ganha o canal como origem.
- O Desempenho conta os leads das Conversas e as repescagens ("Retornos") por campanha.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy); TypeScript + React 18 (Vite).

**Dependências principais**: as da casa; nenhuma nova. A consulta usa o transporte da Graph API da 325.

**Armazenamento**: PostgreSQL. 2 tabelas novas e 4 colunas ([data-model.md](data-model.md)).

**Verificação**: `verify_334.py` (molde do `verify_333`); 325, 328, 330, 332 e 333 como regressão; `npm run typecheck`;
tela pela worktree em desktop e 375×812.

**Restrições**: nenhuma chamada à Meta na transação do aviso; a consulta nunca derruba o processamento; a trava local; a
base fora da `main`.

**Escala/escopo**: nenhum endpoint novo; 3 endpoints com campos novos (conversa, ficha, Desempenho); 1 núcleo novo
(`anuncio_ops`), 1 cliente novo (`meta_anuncios_client`), 3 telas tocadas.

## Constitution Check

| Princípio / seção | Como o plano cumpre |
|---|---|
| I. Reutilizar antes de criar | Usa sem copiar: o transporte e a trava da Graph API, o pipeline do aviso (captura na transação, depois do commit, varredura) e os campos de atribuição e o casamento por nome de campanha do Desempenho (256). |
| II. Padrões de código | Type hints, docstrings, constantes em `app/conversas/constantes.py`; `ruff check` nos tocados. |
| III. Camadas / API First | `app/conversas/anuncio_ops.py` sem `request`, abaixo de `aviso_ops`/`instagram_ops`/`ficha_ops` (que o importam). O cliente da Meta fica em `app/integracoes/`. Endpoints só serializam. |
| IV. Não quebrar | Mudança aditiva. O `attributed_clients` passa a aceitar ficha sem `kommo_created_at` (a do Kommo segue igual). Verifies anteriores como regressão. |
| V. UI/UX com feedback | Textos de leitura, sem ação nova. Campos novos opcionais no front (`docs/00` §6.21). |
| VI/VIII | Esteira completa; verify antes do núcleo, com 2 cenários que devem falhar. |
| XIII. RBAC | Sem endpoint novo; os gates de hoje nos três que ganham campos. |
| XIV. Config / efeito externo | `META_ANUNCIOS_TOKEN` vazio por padrão, com o token do WhatsApp como reserva real; a trava `WHATSAPP_SUPPRESS_SEND` vale para a consulta. Sem token, desligado. |
| XV. Texto por superfície | Interno: "Veio do anúncio", "Origem", "Primeiro anúncio", "Anúncio mais recente", "Retornos". |
| Stack | Migration à mão, aditiva, sobre `c333e1a5b7d9`. |

**Resultado**: ✅ sem violação.

## Estrutura

```text
app/models.py                                     # ConversaAnuncio, AnuncioMeta; 4 colunas em Client
migrations/versions/d334b2c4e6f8_origem_do_anuncio.py
app/integracoes/meta_anuncios_client.py           # consultar_anuncio (GET /{ad_id}?fields=name,campaign{id,name})
app/conversas/anuncio_ops.py                      # registrar_contato, aplicar_na_ficha, origem_organica, consultar_pendentes, reconsultar, leitura
app/conversas/constantes.py                       # origens, tipos, prazos
app/conversas/aviso_ops.py, instagram_ops.py      # captura do referral; consulta depois do commit; _vincular_cliente aplica
app/conversas/ficha_ops.py                        # aplica os anúncios ao ligar e a origem orgânica na ficha nova
app/conversas/varredura.py                        # reconsultar
app/config.py, render.yaml, app/__init__.py       # META_ANUNCIOS_TOKEN; log [anuncios]
app/api/conversas_read.py                         # anuncio no detalhe da conversa
app/api/clientes_read.py                          # origem na ficha
app/marketing/desempenho_ops.py                   # janela por coalesce; retornos por campanha
frontend/apps/internal/src/lib/conversas.ts, clientes.ts, marketing.ts   # tipos
frontend/apps/internal/src/components/conversas/ConversaAberta.tsx      # "Veio do anúncio"
frontend/apps/internal/src/pages/ClientDetailPage.tsx                    # Origem
frontend/apps/internal/src/pages/MarketingDesempenhoPage.tsx             # Retornos
specs/334-crm-origem-do-anuncio/verify_334.py
```

**Reavaliação pós-design**: ✅.
