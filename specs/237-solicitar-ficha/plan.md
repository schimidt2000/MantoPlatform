# Implementation Plan: Solicitar ficha de figurino a partir da busca

**Branch**: `237-solicitar-ficha` | **Date**: 2026-08-14 | **Spec**: [spec.md](./spec.md)

## Summary

Novo `kind="ficha"` no módulo Produção e Compras (feature 225) — sem migração (kind é string;
fluxo curto reusa os status existentes, cópia do fluxo da manutenção). Um endpoint leve
`POST /api/figurino/producoes/solicitar-ficha` (RBAC: qualquer usuário logado interno — o mesmo
público do FigurinoPicker) cria o pedido com título = personagem, descrição = observação +
origem, `requested_by` do usuário. O `FigurinoPicker` ganha o botão "Solicitar ficha" no rodapé
+ dialog com o nome pré-preenchido. `mudar_status` bloqueia `→ pronto` de kind=ficha sem
`figurino_sheet_id`; a tela de detalhe permite vincular a ficha pelo próprio picker. Lista/
filtros reconhecem o tipo via constantes serializadas.

## Technical Context

**Stack**: Flask + SQLAlchemy (sem migração) · React 18/TS (Vite) · módulo 225 existente
**Testing**: `verify_237.py` contra `manto_local` + tsc + validação visual
**Constraints**: tipos existentes intocados (FR-008); RBAC de gestão do módulo inalterado —
só a ABERTURA do tipo ficha é ampla (FR-007)

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reuso | **PASS** — kind novo no módulo existente (fila, logs, anexos, agenda, RBAC de gestão); botão na busca única cobre todas as telas; vínculo usa o próprio picker. |
| II/III. Padrões/camadas | **PASS** — regra em `producao_ops`, endpoint só orquestra. |
| IV. Não quebrar | **PASS** — fluxos por kind são isolados (`FIGURINO_PROD_FLUXOS`); verify cobre regressão dos 3 tipos. |
| V. UX | **PASS** — dialog com loading/erro/sucesso; erro apontado no campo. |
| VI. SDD | **PASS** — esteira completa. |

## Estrutura (arquivos tocados)

```text
app/constants.py                      # FIGURINO_KIND_FICHA + label + fluxo (= manutenção)
app/figurino/producao_ops.py          # criar_solicitacao_ficha(); _erro_titulo; validação →pronto
app/api/figurino_producao_write.py    # POST /solicitar-ficha (login, sem gate de papel)
frontend/.../components/FigurinoPicker.tsx      # botão + dialog "Solicitar ficha"
frontend/.../lib/figurino.ts                    # useSolicitarFicha
frontend/.../pages/FigurinoProducao*Page.tsx    # rótulo/filtro do tipo + vínculo na conclusão
specs/237-solicitar-ficha/verify_237.py
```

## Data model / Contrato (resumo)

- **Sem schema novo.** `FigurinoProducao` usa campos existentes; `figurino_sheet_id` vira
  obrigatório na transição para `pronto` quando `kind="ficha"` (validação de negócio, não de
  banco).
- **POST /api/figurino/producoes/solicitar-ficha** `{personagem, observacao?, origem?}` →
  201 com o pedido; 400 `{personagem: "Informe o nome do personagem."}` se vazio. RBAC: login
  (mesmo público do picker).
- **POST .../status** para `pronto` em kind=ficha sem ficha vinculada → 400 com mensagem clara.
