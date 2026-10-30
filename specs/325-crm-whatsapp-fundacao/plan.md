<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: 325 — Conversas (WhatsApp na Plataforma)

**Branch**: `325-crm-whatsapp-fundacao` | **Data**: 2026-10-30 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/325-crm-whatsapp-fundacao/spec.md`

**Nota**: preenchido pelo `/speckit-plan`. A constituição v3.1.0 foi lida em tempo de execução.

## Resumo

A Plataforma passa a falar WhatsApp pela Cloud API oficial da Meta.

- **Entrada.** Um webhook público e assinado grava cada aviso cru e devolve 200 na hora. Um
  processador idempotente transforma o aviso em conversa, mensagem e status, e baixa a mídia para o
  storage antes que o link da Meta expire. Uma varredura refaz o que morreu no meio.
- **Saída.** Um núcleo de envio grava a mensagem antes de chamar a Meta (a chave de clique duplo vem
  do navegador), respeita a janela de 24h e a trava do ambiente local, e registra a resposta.
- **Tela.** A tela **Conversas** do app interno (lista + conversa) atualiza por consulta periódica
  curta.

Tudo copia moldes que já existem: o webhook assinado da ClickSign (317), o aviso cru com varredura
da InfinitePay (310), o cliente HTTP sem Flask com exceções "recusou × indisponível × travada", a
trava `_suppress_*` e o storage com subpasta protegida por papel.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite) no
frontend.

**Dependências principais**:
- Backend: Flask, SQLAlchemy, Alembic (migrations à mão), `requests` (já em `requirements.txt`;
  nenhuma dependência nova).
- Frontend: React, TanStack Query (`refetchInterval`), Tailwind, `@manto/ui`, Framer Motion e
  `@manto/api-client` (`apiFetch`, upload multipart).

**Armazenamento**:
- PostgreSQL, com quatro tabelas novas ([data-model.md](data-model.md)).
- A mídia fica em `CONVERSAS_MEDIA_FOLDER`, pasta **irmã** de `uploads` (padrão da 205/261: nunca
  bucket público). Ela é servida só por endpoint com gate e entra no backup (`_MEDIA_SUBDIRS`).
  Decisão R7 em `research.md`.

**Verificação**:
- `specs/325-crm-whatsapp-fundacao/verify_325.py` contra o `manto_local`.
- A Meta é substituída por um dublê no processo do verify.
- `cd frontend && npm run typecheck`.
- Tela aberta em desktop e em 375×812.

**Plataforma-alvo**: Render (o `manto-backend` recebe o webhook em `/api/webhooks/whatsapp`, que já é
coberto pelo prefixo `/api` do `frontend/server.js`).

**Tipo de projeto**: SPA desacoplada (API JSON + React).

**Metas de desempenho**:
- O webhook responde em menos de 1 s, só gravando o cru.
- A mensagem aparece na tela em até 10 s (SC-001), com consulta periódica de 5 s na lista e de 4 s na
  conversa aberta, só com a aba visível.
- Carga estimada: 3 pessoas × 2 consultas a cada 5 s ≈ 1 requisição por segundo, desprezível para
  as 36 threads.

**Restrições**:
- O módulo nasce desligado (variáveis vazias); banco local = envio travado (Princípio XIV).
- A URL do webhook é pública e precisa ser estável: `/api/webhooks/whatsapp` vira contrato
  registrado na Meta (armadilha 20).
- Nenhuma chamada à Meta dentro de transação com trava de linha.
- Sem websocket (o proxy Node não faz upgrade).

**Escala/escopo**:
- 4 tabelas, 0 colunas alteradas.
- 2 endpoints públicos (GET/POST do webhook) e 7 internos.
- 1 tela nova (`/conversas`, lista + conversa), 1 item de menu e 1 comando `flask`
  (`whatsapp-reprocessar`) para operação.
- 1 thread de varredura atrás de `MANTO_SEM_THREADS`.

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1.*

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | **Reusa:** o molde do webhook assinado (`clicksign_webhook.py`: corpo cru, `compare_digest`, 404 sem segredo, limiter `60/min`); o aviso cru com claim atômico e varredura (`virtuais_webhook.py` / `reprocessar_avisos`); o cliente HTTP sem Flask com três exceções e o download com teto (`clicksign_client.py`: `_requisitar`, `baixar`); a trava `_suppress_*` (`app/config.py:185-223`); o padrão de mídia sensível em pasta irmã servida por endpoint (`NFC_MEDIA_FOLDER`, `nfc_read.py:125-154`) e o `_MEDIA_SUBDIRS` do backup; o nono dígito via `chave_telefone` (`app/contratos/contratos_ops.py:167`), sem uma segunda regra; o disjuntor de rede e os dublês do `verify_317`; `json_error`, `api_login_required` e o gate em função. **Novo só o que não existe:** o cliente da Graph API e o domínio `app/conversas/`. |
| II. Padrões de código | Type hints, docstrings Google, funções ≤ ~30 linhas, constantes `UPPER_CASE` (`CANAL_WHATSAPP`, situações, teto de mídia) em `app/conversas/constantes.py`. TS estrito com interfaces em `lib/conversas.ts`. `ruff check` nos tocados e `ruff format` nos novos. |
| III. Camadas / API First | **Núcleo puro** em `app/conversas/*_ops.py`, sem `flask.request` (a config chega por parâmetro, como `_ipc_cfg()` da 310). **Endpoints** em `whatsapp_webhook.py`, `conversas_read.py` e `conversas_write.py`, importados em `app/api/__init__.py`. O webhook fica sob `/api`, já coberto pelo `BACKEND_PREFIXES`. |
| IV. Não quebrar o que funciona | Só aditivo: tabelas novas, `Client` ganha só o backref, variáveis vazias = nada muda. O despacho de `/uploads` e o `site_settings` não são tocados (a varredura usa claim por linha, R5). Compartilhado tocado: só o `_MEDIA_SUBDIRS` do backup, que ganha um nome. |
| V. UI/UX com feedback | TanStack Query com skeleton, erro e vazio. O botão Enviar mostra "Enviando…" e fica desabilitado. A mensagem otimista aparece com relógio e vira a situação real. O texto digitado nunca se perde no erro (o rascunho fica no campo). Toasts em pt-BR. |
| VI. Esteira (Nível 1) | Esteira completa: specify → clarify → plan → checklist → tasks → analyze → implement → converge. |
| VII. Living Spec | A spec foi escrita e clarificada antes do plano. Mudança de comportamento volta para a spec. |
| VIII. Verify antes do núcleo | `verify_325.py` na fase Foundational do `tasks.md`, com 21 cenários (6 que **devem** falhar). Ele falha primeiro por "tabela/rota não existe". |
| IX. Dinheiro BRL | Não se aplica: nenhum valor monetário. |
| X. Mobile-first público | Não é superfície pública, mas a equipe usa no celular, então a tela é conferida em 375×812 (SC-006), com alvos ≥ 44 px no envio. |
| XI. Framer Motion | A mensagem nova entra com fade/slide de 150–200 ms e a troca de conversa com 200 ms, ambas com `useReducedMotion`. |
| XII. Combobox / Maps | A seleção de modelo usa o `Combobox` do `@manto/ui` (a lista pode passar de 10). Sem endereço. |
| XIII. RBAC declarado | Gate `_pode_conversas()` (COMERCIAL, SUPERADMIN) no início de cada view. O webhook é público e autenticado por assinatura/token. Mídia sem papel responde 404. Uma linha por endpoint em `docs/01` §4.3 e comentário `RBAC:` no topo de cada módulo. |
| XIV. Config / efeito externo | Segredos só por env (`sync: false` no `render.yaml`), vazios por default, com aviso no log da subida. Não secretos com default real. Trava `_suppress_whatsapp()` (banco local = travado) com o escape `WHATSAPP_ALLOW_LOCAL_SEND`, **no mesmo commit**. Entrada em `docs/05` como desligada até o dono preencher. |
| XV. Texto por superfície | Superfície **interna**: imperativo curto ("Enviar", "Enviar modelo", "Tentar novamente"); estado vazio "Nenhuma conversa encontrada."; erro "Não foi possível enviar. Tente novamente."; "Situação" no rótulo. Os `codigo` do 409 não são texto e o frontend compara só `codigo`, nunca a mensagem. |
| Stack | Migration à mão (`down_revision` = head atual), aditiva. Sem Jinja e sem segredo no repositório. |
| Operação e Deploy | Não toca o `startCommand`. Migração aditiva, sem ensaio destrutivo. Deploy em lote noturno. Variáveis novas vazias = nenhuma mudança visível para a equipe. |

**Resultado do gate**: ✅ sem violação a justificar.

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/325-crm-whatsapp-fundacao/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/api.md
├── checklists/requirements.md (+ o do /speckit-checklist)
├── tasks.md
└── verify_325.py
```

### Código (caminhos reais)

```text
app/models.py                                  # WhatsappAviso, Conversa, ConversaMensagem, ConversaMidia
migrations/versions/<rev>_conversas_whatsapp.py # à mão, aditiva
app/config.py                                  # WHATSAPP_* + _suppress_whatsapp()
app/integracoes/whatsapp_client.py             # Graph API sem Flask: enviar, subir/baixar mídia, modelos, marcar lida
app/conversas/__init__.py
app/conversas/constantes.py                    # canais, situações, tipos, tetos, textos de tipo não exibido
app/conversas/telefone.py                      # variantes do nono dígito (sobre contratos_ops.chave_telefone)
app/conversas/aviso_ops.py                     # gravar cru, claim, processar aviso → conversa/mensagem/status/eco
app/conversas/midia_ops.py                     # baixar e guardar mídia recebida; guardar a enviada (CONVERSAS_MEDIA_FOLDER)
app/backup_drive.py                            # _MEDIA_SUBDIRS ganha "conversas_midia"
app/conversas/envio_ops.py                     # janela, trava, idempotência, texto/mídia/modelo, marcar lida
app/conversas/leitura_ops.py                   # lista, conversa, serialização
app/conversas/varredura.py                     # reprocessar avisos e mídias pendentes (thread + comando)
app/api/whatsapp_webhook.py                    # GET/POST públicos
app/api/conversas_read.py | conversas_write.py # internos; importados em app/api/__init__.py
app/__init__.py                                # thread de varredura (atrás de MANTO_SEM_THREADS), pasta de mídia, aviso de config
app/api/auth.py                                # serialize_user ganha conversas_ligadas (aditivo; opcional no TS)
app/cli.py                                     # flask whatsapp-reprocessar [--aplicar]
render.yaml                                    # envVars sync:false (sem tocar startCommand)
frontend/apps/internal/src/lib/conversas.ts    # tipos + hooks TanStack
frontend/apps/internal/src/pages/ConversasPage.tsx
frontend/apps/internal/src/components/conversas/{ListaDeConversas,ConversaAberta,Mensagem,CaixaDeEnvio,EnviarModeloDialog}.tsx
frontend/apps/internal/src/App.tsx · lib/navigation.tsx  # rota + item de menu
```

**Decisão de estrutura**:
- Domínio novo `app/conversas/`, porque a Fase 2 põe o Instagram aqui sem misturar com
  `app/clientes/`.
- O cliente da Meta fica em `app/integracoes/`, como os da InfinitePay e da ClickSign.
- O núcleo é separado por ato (aviso, mídia, envio, leitura), para cada arquivo ficar curto e o
  verify mirar cada um.

## Rastreamento de complexidade

Sem violação a justificar.

## Fase 0 e Fase 1

- Pesquisa e decisões: [research.md](research.md).
- Modelo: [data-model.md](data-model.md).
- Contratos: [contracts/api.md](contracts/api.md).
- Validação: [quickstart.md](quickstart.md).

**Reavaliação pós-design do Constitution Check**: ✅ nada mudou. A decisão R7 (onde servir a mídia)
mantém o 404 para quem não tem o papel nos dois caminhos.
