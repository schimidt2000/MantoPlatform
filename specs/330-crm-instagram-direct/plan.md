<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: 330 — Instagram Direct na caixa de Conversas

**Branch**: `330-crm-instagram-direct` (sobre a `328-crm-equipe-na-caixa`) | **Data**: 2026-11-03 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/330-crm-instagram-direct/spec.md`

## Resumo

O Instagram entra como **segundo canal** da caixa da 325, sem uma segunda caixa:
- um webhook próprio grava o aviso cru na mesma fila e no mesmo processamento idempotente;
- um processador `instagram_ops` cria conversas `canal="instagram"`, mensagens, mídias, ecos, reações e vistos;
- um cliente `instagram_client` usa o mesmo transporte da Graph API do WhatsApp;
- um adaptador de canal (`canais.py`) deixa o `envio_ops` mandar pelo canal da conversa, com a janela do Instagram
  (24 h normal, até 7 dias com a marca de resposta humana).

Responsável, espera, alerta, notas e respostas rápidas da 328 valem sem mudança. Na tela entram o ícone e o filtro do
canal, o @usuário e o aviso da janela.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy); TypeScript + React 18 (Vite).

**Dependências principais**: as da 325/328, nenhuma nova. A Graph API `v26.0` em `graph.facebook.com` (mensageria do
Instagram pela Página). O ffmpeg do sistema, para o áudio em m4a.

**Armazenamento**: PostgreSQL, com 2 colunas em `conversas` e 2 colunas alargadas em `conversa_mensagens`
([data-model.md](data-model.md)). Nenhuma tabela nova.

**Verificação**: `specs/330-crm-instagram-direct/verify_330.py` contra o `manto_local` (molde `verify_328`), com dublê
do cliente do Instagram. `verify_325` e `verify_328` continuam verdes, como regressão. `npm run typecheck`. Tela pela
worktree em desktop e 375×812.

**Plataforma-alvo**: Render. Entram três variáveis no `render.yaml`, com `sync: false`.

**Metas de desempenho**:
- o aviso é processado na hora, como no WhatsApp;
- a conversão do áudio para m4a recodifica, mas 5 minutos de voz levam poucos segundos na CPU do Render.

**Restrições**:
- o IGSID é numérico e não pode virar telefone (R3);
- a janela conta pela `ultima_recebida_em` (UTC);
- a trava é a mesma do WhatsApp;
- a base é uma branch fora da `main`.

**Escala/escopo**:
- 2 endpoints novos (o webhook GET e o POST) e 4 alterados (lista, envio, modelo e lida);
- 1 cliente HTTP, 1 processador, 1 adaptador de canal e 1 migration;
- na tela, 1 componente novo (`IconeDoCanal`) e 5 alterados.

## Constitution Check

| Princípio / seção | Como o plano cumpre |
|---|---|
| I. Reutilizar | Reusa: a fila crua, o claim e a varredura da 325; `assinatura_valida`; o transporte da Graph API do `whatsapp_client` (`requisitar`, os erros, a trava); `envio_ops` como orquestrador; `midia_ops` (`baixar_midia`, `guardar_bytes`, o espaçamento); toda a 328; o gravador da 328. Novo: `instagram_client`, `instagram_ops`, `canais`, `IconeDoCanal`. |
| II. Padrões | type hints, docstrings, funções ≤ ~30 linhas, constantes do Instagram em `constantes.py`; TS estrito. |
| III. Camadas | O núcleo puro fica em `app/conversas/*_ops.py`, e o cliente sem Flask em `app/integracoes/`. O endpoint `instagram_webhook.py` é importado em `app/api/__init__.py`. |
| IV. Não quebrar | Só aditivo. O WhatsApp passa a ir pelo adaptador **sem mudar comportamento** (`verify_325` e `verify_328` como regressão). O payload ganha campos opcionais no TS. A URL do webhook do WhatsApp não muda. |
| V. Feedback | Erro no campo (`fields.texto`/`fields.arquivo`), aviso de janela, botão com `loading`. |
| VI/VII/VIII | Esteira completa; o `verify_330.py` na fase Foundational, com 6 cenários que devem falhar. |
| IX | Não se aplica. |
| X | Interno, mas conferido em 375×812. |
| XI | O filtro e o aviso entram com o motion existente, sem animação nova. |
| XII | O filtro de canal tem 3 opções (botões de alternância). |
| XIII | O webhook é público e assinado (404 sem assinatura ou com o canal desligado). As rotas alteradas mantêm `pode_conversas`. Uma linha nova em `docs/01` §4.3. |
| XIV | As três envs novas nascem vazias (canal desligado), e a subida loga a ausência (`[instagram] ligado=False …`). A trava `_suppress_whatsapp` cobre o Instagram. Dívida em `docs/05`. |
| XV | Textos internos: "Enviada por outro app", "Mensagem apagada pela cliente.", aviso de janela, recusas no padrão "… não aceito pelo Instagram…". |
| Stack | Migration à mão, aditiva, sobre `f328b2d4e6a1`. |
| Operação e Deploy | Sem `startCommand`. Entra no lote 325 → 328 → 330. |

**Resultado**: ✅ sem violação.

## Estrutura do projeto

```text
app/models.py                                   # Conversa.usuario, Conversa.perfil_em; externo_id/resposta_a 255
migrations/versions/a330c4e8f1b2_conversas_instagram.py
app/config.py                                   # INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_PAGE_ID, INSTAGRAM_ACCOUNT_ID (vazios)
app/__init__.py                                 # log [instagram] na subida
render.yaml                                     # 3 envs sync:false
app/integracoes/whatsapp_client.py              # _requisitar → requisitar (público, alias mantido)
app/integracoes/instagram_client.py             # ConexaoInstagram, enviar, enviar_arquivo, perfil
app/conversas/configuracao.py                   # cfg_instagram() → CfgInstagram
app/conversas/constantes.py                     # tipos de anexo do IG, tetos, textos, códigos de erro
app/conversas/canais.py                         # CanalWhatsapp / CanalInstagram: pré-condições, janela, envio
app/conversas/instagram_ops.py                  # processar_entradas: mensagem, eco, reação, visto, apagada; perfil
app/conversas/aviso_ops.py                      # despacho por object; conversa_do_contato sem telefone fora do WhatsApp
app/conversas/envio_ops.py                      # orquestra pelo canal da conversa
app/conversas/midia_ops.py                      # baixar pelo link do IG; audio_para_m4a
app/conversas/leitura_ops.py                    # janela/usuario no cartão; filtro canal
app/api/instagram_webhook.py                    # GET/POST /api/webhooks/instagram
app/api/conversas_read.py / conversas_write.py  # canal, canais_ligados, sem_modelos
app/api/auth.py                                 # conversas_ligadas com qualquer canal
frontend/apps/internal/src/lib/conversas.ts
frontend/apps/internal/src/components/conversas/{IconeDoCanal,FiltroDaLista,ListaDeConversas,ConversaAberta,CaixaDeEnvio}.tsx + pages/ConversasPage.tsx
```

## Rastreamento de complexidade

Sem violação a justificar.

**Reavaliação pós-design**: ✅.
