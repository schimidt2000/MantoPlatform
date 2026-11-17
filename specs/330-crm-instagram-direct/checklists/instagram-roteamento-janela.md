<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Checklist de integração, roteamento e janela: 330 Instagram Direct

**Propósito**: testar a qualidade dos requisitos (não a implementação) em quatro frentes: o aviso e o roteamento da
Meta, a janela do Instagram, a mídia e o envio, e a tela.
**Created**: 2026-11-03
**Feature**: [spec.md](../spec.md)

**Nota**: profundidade padrão, para revisão. O que faltava foi corrigido na spec na mesma rodada: o `standby` e o envio
recusado pelo roteamento, e a mesma pessoa nos dois canais.

## Portões da Manto (fixos — constituição, §Portões de Qualidade)

- [x] CHK001 `cd frontend && npm run typecheck` limpo (três SPAs)
- [x] CHK002 `ruff check` limpo nos arquivos Python tocados; `ruff format` só em arquivo novo
- [x] CHK003 `verify_330.py` verde contra `manto_local`, com conexão separada e os cenários que falham; `verify_325` e `verify_328` verdes
- [x] CHK004 Tela aberta de verdade, em desktop e em 375×812
- [x] CHK005 Migration manual criada e aplicada no `manto_local`
- [x] CHK006 `scripts/validar_startcommand.py` — não se aplica (sem mudança no `startCommand`)
- [x] CHK007 Gate de RBAC (webhook assinado; rotas com `pode_conversas`) e linha em `docs/01` §4.3
- [x] CHK008 Docs por fonte única (`docs/01`, `02`, `03`, `04`, `05`, plano)
- [x] CHK009 Nível 1: `/speckit-converge` sem gaps
- [x] CHK010 Texto novo revisado pelo Princípio XV
- [x] CHK011 Antes de "em produção": git limpo, `docs/03` batendo, sonda `/api/` — **não publicado** (o dono
  adiou); conferir no deploy do lote 325 → 328 → 330

## Aviso e roteamento

- [x] CHK012 A recusa do aviso sem assinatura, com assinatura errada ou com o canal desligado está definida? [Completeness, Spec §FR-001, §FR-015]
- [x] CHK013 Está definido que o aviso do Instagram passa pela mesma garantia de "nada se perde" do WhatsApp? [Consistency, Spec §FR-002]
- [x] CHK014 Está definido o que acontece com a mensagem que chega "em espera" (outro app no controle)? [Gap → resolvido, Spec §Casos de borda, §FR-004]
- [x] CHK015 O envio recusado porque a conversa está com outro app tem resultado e texto definidos? [Gap → resolvido, Spec §Casos de borda]
- [x] CHK016 Está definido que a Plataforma nunca responde nem toma o controle sozinha? [Clarity, Spec §História 3, SC-003]
- [x] CHK017 O eco da própria Plataforma × eco de outro app está diferenciado, sem duplicar? [Clarity, Spec §FR-007]

## Janela do Instagram

- [x] CHK018 As três faixas (24 h, até 7 dias, depois) estão definidas com fronteiras e com a base do cálculo (última mensagem da cliente)? [Clarity, Spec §FR-010]
- [x] CHK019 O texto de cada faixa na caixa de envio está especificado? [Completeness, Spec §FR-014, cenário 12]
- [x] CHK020 Está definido o que acontece se a Meta recusar a marca de resposta humana (permissão não liberada)? [Edge Case, Spec §Casos de borda]
- [x] CHK021 Está dito que o Instagram não tem modelos e o que a tela faz com isso? [Consistency, Spec §FR-014, §História 2]

## Mídia e envio

- [x] CHK022 Os tipos e tamanhos aceitos no envio estão quantificados por tipo? [Measurability, Spec §FR-008]
- [x] CHK023 A conversão do áudio gravado por navegador está definida (webm/ogg → m4a; mp4 direto)? [Coverage, Spec §FR-009, §Casos de borda]
- [x] CHK024 Os anexos sem link (efêmera) e os tipos que a Plataforma não exibe (story, reels, publicação, não suportado) têm texto definido? [Edge Case, Spec §Casos de borda]
- [x] CHK025 O limite de texto do Instagram está quantificado? [Measurability, Spec §FR-008]

## Tela e dados

- [x] CHK026 O filtro de canal e quando ele aparece (só com os dois canais ligados) estão definidos? [Clarity, Spec §FR-013, §FR-015]
- [x] CHK027 O que aparece no lugar do telefone, e o caso do perfil indisponível, estão definidos? [Completeness, Spec §FR-003, §Casos de borda]
- [x] CHK028 Está definido que a conversa do Instagram não liga à ficha nesta fase (e por quê)? [Scope, Spec §Fora de escopo, §Casos de borda]
- [x] CHK029 A regra de 328 (responsável, espera, alerta, notas, respostas rápidas) está declarada igual para o Instagram? [Consistency, Spec §FR-012]

## Notas

- Os três pontos que a documentação da Meta não fecha (codificação do upload, campos do perfil e códigos de recusa da
  marca humana e do roteamento) ficam no quickstart §3 para a conta de teste. A spec define o comportamento visível
  em qualquer caso.
