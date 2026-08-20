# Plano de extração do `app/calendar/routes.py`

**Data:** 20/08/2026 · Pré-requisito final da Fase 6 da remoção do Jinja
(ver [`PLANO_REMOCAO_JINJA.md`](PLANO_REMOCAO_JINJA.md)).

## Por que este documento existe

O plano da Fase 6 dizia "apagar as 18 views Jinja". Isso está errado, e a medição mostra por quê:
**`calendar/routes.py` exporta 47 símbolos distintos, em 86 pontos de import, para 13 módulos
vivos** e 15 scripts. A maioria não é view — é criação e validação de evento, consulta de mês,
parsing de título e registros financeiros.

O arquivo é uma **biblioteca compartilhada com views penduradas**. Apagar as views não o apaga.

O caminho é o mesmo já percorrido com sucesso quatro vezes neste projeto (`group_ops`,
`comercial_ops`, `formularios_ops`, `comissoes_ops`): mover o núcleo para módulos `*_ops.py`
puros, fazer o Jinja delegar, reapontar os importadores.

---

## Os quatro cortes, em ordem de risco crescente

| # | Grupo | Destino | Move / Fica | Risco |
| --- | --- | --- | --- | --- |
| 1 | **título** | `app/calendar/titulo_ops.py` | 14 / 0 | **Baixo** — nenhum símbolo toca `db`, models ou outro domínio. Só `re`, `unicodedata` e 3 constantes. |
| 2 | **registros** | `app/calendar/registros_ops.py` | 11 / 2 | **Médio** — mexe em `EventPayment`/`EventContract`/`EventInvoice`/`EventReimbursement`. |
| 3 | **consulta/sync** | `app/calendar/consulta_ops.py` | 14 / 3 | **Alto** — `_build_orcamento_prefill` calcula dinheiro. |
| 4 | **evento** | `app/calendar/evento_ops.py` | 27 / 8 | **O mais alto** — contém `_compute_performer_caches`. |

**Passo 0, antes de qualquer corte:** mover as constantes para `app/constants.py`, onde `RoleName`
já vive — `CALENDAR_ID`, os `_CAN_*`, `PRESENCE_CHARACTER`, `SOUND_TECH_CHARACTER`,
`SOUND_TECH_TALENT_ID`. Elas **não pertencem a um `ops`**. São 5 importadores vivos + 5 scripts;
merece commit próprio, com risco descorrelacionado dos cortes.

---

## O que a apuração encontrou e que não se deve descobrir de novo

### O maior risco do repositório neste trabalho

`_compute_performer_caches` (~255 linhas, features 172/236/239) calcula o cachê de cada artista:

```
round(int(prices[i]) + noturno_add + transport_add + sosia_custom_add_per_artist)
```

**Um único arredondamento aplicado por parcela em vez de na soma muda o cachê em até R$ 1 por
artista, em silêncio.** Colar **verbatim** — não reformatar, não "melhorar". O mesmo vale para
`_create_event_row`, que grava `sale_value` e calcula acréscimo percentual com `ROUND_HALF_UP`.

### Injeções obrigatórias (para não puxar outro domínio)

- `sincronizar_comissao` em `_create_event_core` — hoje faz
  `from app.financeiro.routes import _sync_commission_payment`. Mesmo padrão de `group_ops.agrupar`.
  **Passar nos DOIS call sites** (`routes.py:3905` e `api/agenda_write.py:747`): o default `None`
  não pode virar no-op silencioso em produção.
- `delete_event_row` em `cleanup_stale_events` — evita puxar `cancel_ops.aplicar_estorno_comissao`.
- `sync_events` em `sync_single_event_flow` — sem isso há **ciclo de import**. Bônus: o monkeypatch
  de `verify_151_excluir_sync.py:46` continua funcionando.
- `compute_performer_caches` em `build_orcamento_prefill` — só 2 call sites, não se espalha.
- Os diretórios de upload (`payments_dir`, `contracts_dir`, `invoice_dir`) vindos de
  `current_app.config`, no grupo **registros**.

**Avaliado e descartado:** injetar `app.orcamento.pricing` em `_compute_performer_caches`. Não é
domínio hostil — é a fonte da tabela de preços, o import já é lazy, e injetar seis funções só
aumentaria o diff no único símbolo onde o diff precisa ser zero.

**Não injetar** `notify_ensaio_team`, `convidar_recem_escalados` nem `aplicar_estorno_comissao`:
são do mesmo domínio `calendar`. Mantê-los lazy **no corte**, para o diff não misturar mudança de
import com mudança de módulo.

### Armadilhas nomeadas

- **`_save_bounded_upload` e `_save_file_upload` parecem a mesma função e não são.** Limites
  diferentes (10 vs 20 MB) e — pior — o primeiro prefixa `YYYYMMDDHHMMSS_<uuid6>_` no nome e o
  segundo **não**, então arquivos homônimos se sobrescrevem, de propósito documentado. Os dois vão
  para `app/storage.py`, não para o `registros_ops`.
- **`_ensure_coordinator` e `_ensure_sound_technician` são gêmeos** — `_apply_default_roles` chama
  os dois e a idempotência depende de casarem na mesma sessão. Separá-los quebra o comportamento.
- **`_delete_event` usa `current_app.logger`.** Aceitável num `ops` (vários já usam). **Não** trocar
  por `logging.getLogger` durante o corte: é mudança de comportamento fora de escopo.
- `_talent_time_conflict` faz `replace(tzinfo=None)` inline — **não** precisa levar `_dt_naive`.

---

## Como verificar cada corte

O mesmo protocolo que a extração da régua de comissão usou, e que provou zero divergência em 450
eventos:

1. `python -c "from app import create_app; create_app()"` — o Flask registra na importação.
2. `ruff check app/<modulo> --select F821` — é ele que acha o import que faltou no recorte.
3. **Para qualquer corte que toque dinheiro** (grupos 3 e 4): calcular o resultado para os **450
   eventos** do espelho num worktree do `main` e no branch, e comparar item a item. Nem o `ruff`
   nem o boot pegam mudança de número.
4. `verify_206`, `verify_246`, `verify_249`, `verify_251` e `check_url_for_orfaos`.

**Um corte por commit.** Nunca dois grupos no mesmo — se um número mudar, o `git revert` precisa
isolar qual.
