<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: 341 — o Papai Noel liga para qualquer idade, e o vídeo tem data

**Branch**: `341-papai-noel-para-todos` | **Data**: 2026-11-10 | **Spec**: [spec.md](./spec.md)

## Resumo

Duas mudanças na Loja de Interações Virtuais, sem endpoint novo:
1. **Texto**: o fixo do site (`lojaTema.ts`, página da campanha, página do pedido), os e-mails, as
   mensagens de erro da ficha, a descrição do evento da venda e as duas telas internas do pedido passam
   a falar de "quem vai receber", com a criança como caso comum e a cartinha condicionada a ela.
2. **Data de entrega do vídeo**: coluna `virtual_campaigns.recorded_delivery_until` (data, opcional),
   uma função `prazo_do_video(campanha, hoje)` que decide o `due_date` da entrega, o campo na gestão e o
   texto "entregue até 13 de dezembro" na página e no e-mail.

A branch parte da `340-caixa-de-avisos` porque a migration encadeia em `e340c1a2b3d4` e as duas vão
juntas no deploy da noite (com a loja no ar, push só depois das 23h até a 340 estar em produção).

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy); TypeScript + React 18
**Armazenamento**: PostgreSQL; coluna nova, migration à mão `e341a1b2c3d4` sobre `e340c1a2b3d4`
**Verificação**: `verify_341.py` contra o `manto_340` (mesma exceção da 340: o `manto_local` está no
CRM); regressão `verify_304`, `verify_205`; `npm run typecheck`; tela em 375×812 e gestão
**Restrições**: chaves `child_name`/`child_age` não mudam; campo novo opcional no React; data por
recorte de texto, nunca `new Date(iso)` (desloca um dia em UTC)
**Escala**: 1 coluna, 2 serializers, 1 função de prazo, ~8 arquivos de texto

## Constitution Check

| Princípio | Como cumpre |
|---|---|
| I. Reutilizar | `_parse_date` existente para a data; `formatarData` da página do pedido vira helper de `lib/virtuais.ts` reusado pela campanha; o prazo sai de uma função só |
| II. Código | type hints, docstring, constante de meses em pt-BR no topo; `ruff check` nos tocados |
| III. Camadas | regra do prazo em `virtuais_ops.py`; rotas só repassam o campo |
| IV. Não quebrar | coluna nula = comportamento de hoje; regressão 304 (cartinha) e 205 |
| V. UI | campo de data com erro no campo (`FieldError`) como os vizinhos |
| VI–VIII | esteira Nível 1; spec antes; verify antes do núcleo |
| IX | nenhum valor monetário novo |
| X. Mobile | campanha e pedido conferidos em 375×812 |
| XIII. RBAC | sem endpoint novo; o campo segue `require_virtuais_access` |
| XIV. Config | nada novo |
| XV. Texto | site público caloroso e claro; interno "Para"; glossário: "Informe…"; nenhuma chave ou código muda |
| Stack | migration à mão, aditiva |
| Operação | sem `startCommand`; deploy à noite junto da 340 |

## Estrutura

```text
app/models.py                                   # VirtualCampaign.recorded_delivery_until
migrations/versions/e341a1b2c3d4_entrega_do_video.py
app/marketing/virtuais_ops.py                   # prazo_do_video; criar/atualizar; serializers; erros da ficha; "Para:"
app/api/virtuais_write.py                       # repassa recorded_delivery_until no POST
app/email_service.py                            # e-mails sem "criança"; prazo do vídeo pela entrega
frontend/apps/public/src/lib/lojaTema.ts        # copy da estação
frontend/apps/public/src/lib/virtuais.ts        # tipo + dataPorExtenso/formatarDataCurta
frontend/apps/public/src/pages/CampanhaVirtualPage.tsx
frontend/apps/public/src/pages/PedidoVirtualPage.tsx
frontend/apps/internal/src/lib/virtuais.ts      # tipo + input
frontend/apps/internal/src/pages/VirtuaisCampanhaFormPage.tsx  # campo "Entrega dos vídeos até"
frontend/apps/internal/src/pages/FilaProducaoMidiaPage.tsx     # "Para"
frontend/apps/internal/src/components/EventDetail/PedidoVirtualSection.tsx  # "Para"
```

## Decisões (pesquisa curta)

- **Coluna explícita, não regra implícita.** "7 dias depois do dia das chamadas" poderia ser
  calculado do primeiro horário da campanha, mas mudaria sozinho quando alguém criasse outro dia de
  horários. O dono disse "pode colocar direto, que é até dia 13 do 12": a data fica escrita na campanha.
- **Data passada vira dias.** Vídeo pago depois da data recebe pagamento + dias, para a Fila nunca
  nascer com prazo vencido.
- **O e-mail lê o prazo da entrega** (`VirtualMediaDelivery.due_date`), que já existe no momento do
  envio — mesma fonte da página do pedido e da Fila.
- **Meses por extenso no React por tabela**, não `Intl` com `Date` (fuso).

## Rastreamento de complexidade

| Violação | Por que | Alternativa rejeitada |
|---|---|---|
| Verify contra `manto_340` (Princípio VIII) | o `manto_local` está na migration do CRM 334 | refazer o `manto_local` apagaria o esquema das sessões do CRM |
