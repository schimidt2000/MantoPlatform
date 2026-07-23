# Quickstart — Verificação da correção

Verificação funcional contra `manto_local` (Postgres), script com test client do Flask,
requests **fora** de `app.app_context()` (regra do projeto).

```powershell
.\scripts\db\run-local.ps1   # garante manto_local atualizado, se preciso rodar o app localmente
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe scripts\verify_172_orcamento_elenco.py   # script de verificação da feature
```

## Casos cobertos pelo script

1. **Orçamento sem "show customizado"** (o caso comum, `show_sosia_tipo == "predefinido"`):
   `_compute_performer_caches` continua devolvendo os mesmos cachês de antes da correção
   (nenhuma regressão) — comparado com `get_ator_prices`/`get_cantor_prices`/`get_especial_prices`
   chamados diretamente.
2. **Orçamento com "show customizado"** (`show_sosia_tipo == "customizado"`): soma dos cachês
   dos personagens (excluindo coordenador/técnico/maquiador) devolvidos por
   `_compute_performer_caches`, mais o acréscimo, bate com `entry.total_1h..4h` menos os custos
   fixos de coordenador/técnico/maquiador — ou seja, o "+R$50/artista" agora aparece no cachê de
   cada personagem, não só no total.
3. **`has_show` unificado**: para um snapshot com performer `especial` tendo `cantor=True` mas
   `show=False`, `compute_show_pricing` e o cálculo original do orçamento (`app/orcamento/
   routes.py`) concordam sobre `has_show` — e a linha "Técnico de Som" aparece/some de forma
   idêntica nos dois cálculos.
4. **Paridade com orçamentos reais existentes**: reroda `_build_orcamento_prefill` contra os 5
   `OrcamentoHistory` mais recentes de `manto_local` (mesmo que já foi testado manualmente
   durante a investigação) e confirma que o elenco continua saindo completo — sem regressão para
   o caso comum.
5. **Criação de evento fim-a-fim**: cria um orçamento novo via `app/orcamento` com "show
   customizado" ativo, gera o evento a partir dele (`POST /events/new` com o `orc_caches_json`
   pré-preenchido), e confere que os `EventRole` salvos têm `cache_value` já incluindo o
   acréscimo.
