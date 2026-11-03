<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: 328 — Conversas em equipe

**Branch**: `328-crm-equipe-na-caixa` (sobre a `325-crm-whatsapp-fundacao`) | **Data**: 2026-11-03 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/328-crm-equipe-na-caixa/spec.md`

## Resumo

Cinco peças sobre a fundação da 325, todas no domínio `app/conversas/`:

- **Responsável** (fila livre, assumir, transferir, devolver), com gravação condicional para a corrida não
  "roubar" a conversa.
- **Espera** (`aguardando_desde`) e um **alerta** de 15 min, das 9h às 21h, emitido pelo sistema de notificações
  da 272, na varredura que já existe.
- **Notas internas** (tabela nova).
- **Respostas rápidas** (tabela nova, CRUD da equipe).
- **Áudio gravado** no navegador, com o webm do Chrome convertido para ogg pelo ffmpeg que a casa já usa.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy); TypeScript + React 18 (Vite).

**Dependências principais**: as da 325, nenhuma nova. No navegador, `MediaRecorder` (nativo). No servidor, o
ffmpeg do sistema (`video_ops`).

**Armazenamento**: PostgreSQL, com 3 colunas em `conversas` e 2 tabelas novas, mais dois kinds novos em
`notifications`, sem tabela ([data-model.md](data-model.md)).

**Verificação**: `specs/328-crm-equipe-na-caixa/verify_328.py` contra o `manto_local` (molde `verify_325`);
`npm run typecheck`; tela aberta em desktop e 375×812, a partir da worktree.

**Plataforma-alvo**: Render; nada novo no `render.yaml`.

**Metas de desempenho**:
- o alerta sai entre 15 e 16 min, porque a varredura roda a cada 60 s;
- a conversão do áudio leva menos de 1 s para 5 min de áudio, porque só troca o recipiente.

**Restrições**:
- o horário 9h–21h é de São Paulo (`now_sp()`), nunca UTC (armadilha 3 do `docs/00`);
- notificações usam `now_sp()` em `created_at` (armadilha 2), e só a regra de espera compara UTC com UTC;
- a base é uma branch fora da `main`.

**Escala/escopo**:
- 2 tabelas e 3 colunas;
- 7 endpoints novos (equipe, responsável, notas e 4 de respostas rápidas) e 3 alterados;
- 2 kinds de notificação (esperando e transferida);
- na tela, 4 componentes novos e 4 alterados.

## Constitution Check

| Princípio / seção | Como o plano cumpre |
|---|---|
| I. Reutilizar | **Reusa**: a fundação da 325 (gate `pode_conversas`, `envio_ops`, `aviso_ops`, varredura); `notificacoes_ops.emitir`, `apagar_por_entidade` e `resolver_destinatarios`; o `video_ops` para o ffmpeg (ganha só um `caminho_do_ffmpeg()` público); o `ConfirmDialog`, o `Combobox` e o `Dialog` do `@manto/ui`. **Novo**: `equipe_ops.py` (responsável, espera, alerta, notas) e `respostas_ops.py`. |
| II. Padrões | type hints, docstrings, funções ≤ ~30 linhas, constantes (`ESPERA_PARA_ALERTA`, `HORARIO_DE_ALERTA`, limites) em `constantes.py`; TS estrito. |
| III. Camadas | núcleo puro em `app/conversas/*_ops.py`; endpoints em `conversas_read/write.py` (e `conversas_equipe_write.py` para responsável, notas e respostas, mantendo os arquivos curtos), importados em `app/api/__init__.py`. |
| IV. Não quebrar | só aditivo; o payload ganha campos novos, opcionais no TS (armadilha 21); o `_despachar` só acrescenta a atribuição condicional. |
| V. Feedback | botões com `loading`; erro apontado no campo (`fields`); excluir resposta rápida com `ConfirmDialog`; microfone negado com mensagem. |
| VI/VII/VIII | esteira completa; `verify_328.py` na fase Foundational, com 5 cenários que devem falhar. |
| IX | não se aplica. |
| X | interno, mas conferido em 375×812, com alvos ≥ 44 px no microfone e no menu do responsável. |
| XI | o menu e os diálogos entram com Framer Motion; a nota e o item novo também; tudo com `useReducedMotion`. |
| XII | a transferência usa `Combobox` (a equipe pode passar de 10 pessoas); as respostas rápidas usam lista com busca. |
| XIII | `pode_conversas` em toda view nova; linha em `docs/01` §4.3. |
| XIV | nenhuma env nova; nada externo novo (a nota não sai; o áudio usa o envio já travado da 325). |
| XV | textos internos com o glossário: "Assumir", "Transferir", "Devolver à fila", "Nota interna", "Respostas rápidas", "Gravar áudio", "Excluir esta resposta?"; recusas no padrão "Informe…"/"Já existe…". |
| Stack | migration à mão, aditiva, sobre `e325a7c1d9f2`. |
| Operação e Deploy | sem `startCommand`. Entra no mesmo lote da 325, na ordem 325 → 328. |

**Resultado**: ✅ sem violação.

## Estrutura do projeto

```text
app/models.py                                   # Conversa (+3 colunas), ConversaNota, RespostaRapida
migrations/versions/f328b2d4e6a1_conversas_equipe.py
app/conversas/constantes.py                     # ESPERA_PARA_ALERTA, HORARIO_DE_ALERTA, limites, textos
app/conversas/relogio.py                        # agora_utc() (sai de aviso_ops: equipe_ops não pode importá-lo)
app/conversas/recusa.py                         # Recusa (EnvioRecusado herda dela)
app/conversas/equipe_ops.py                     # responsável (atribuir/assumir/transferir/devolver), espera, alerta, notas, equipe
app/conversas/respostas_ops.py                  # CRUD das respostas rápidas
app/conversas/aviso_ops.py                      # recebida abre a espera; eco fecha
app/conversas/envio_ops.py                      # envio aceito: atribui + fecha a espera; webm → ogg; voice
app/conversas/midia_ops.py                      # webm_para_ogg
app/conversas/leitura_ops.py                    # filtro, responsavel, aguardando_desde, notas
app/conversas/varredura.py                      # alertar_esperas na passada
app/impressoes3d/video_ops.py                   # caminho_do_ffmpeg() público (aditivo)
app/notificacoes/notificacoes_ops.py            # KIND_CONVERSA_ESPERANDO e KIND_CONVERSA_TRANSFERIDA; apagar_por_entidade(kind=)
app/api/conversas_read.py                       # filtro, equipe, notas no detalhe
app/api/conversas_equipe_write.py               # responsável, notas, respostas rápidas (registrado em app/api/__init__.py)
frontend/apps/internal/src/lib/conversas.ts     # tipos novos + hooks
frontend/apps/internal/src/components/conversas/{FiltroDaLista,ResponsavelDaConversa,TransferirDialog,NotaInterna,RespostasRapidas,GerenciarRespostasDialog,GravadorDeAudio}.tsx
frontend/apps/internal/src/components/conversas/{ListaDeConversas,ConversaAberta,CaixaDeEnvio}.tsx + pages/ConversasPage.tsx
```

## Rastreamento de complexidade

Sem violação a justificar.

**Reavaliação pós-design**: ✅.
