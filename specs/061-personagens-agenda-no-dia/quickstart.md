# Quickstart — Verificação manual da feature 061

Validar a exibição de personagens da agenda no dia, na calculadora. **Rodar contra a cópia local
`manto_local` (Postgres)**:

```powershell
.\scripts\db\run-local.ps1
```

## Passo 1 — Data com personagens (US1, FR-001/FR-003/FR-008)

1. Abrir a calculadora de orçamento e informar uma data que tenha eventos com personagens
   escalados.
   - ✅ Logo abaixo do campo de data aparece a lista de personagens daquele dia.
   - ✅ Cada personagem aparece uma vez; mostra o(s) evento(s) do dia.

## Passo 2 — Apoio e ensaio fora (FR-002)

1. Numa data que tenha Coordenador/Técnico de Som/Presença e/ou ensaio.
   - ✅ Esses papéis **não** aparecem; só personagens vendáveis.

## Passo 3 — Estado vazio e troca de data (FR-004/FR-005)

1. Informar uma data sem eventos.
   - ✅ Mensagem "Nenhum personagem agendado neste dia".
2. Trocar para outra data com agenda.
   - ✅ A lista atualiza. Limpar a data → some.

## Passo 4 — Endpoint (contrato)

1. `GET /orcamento/personagens-no-dia?date=YYYY-MM-DD` autenticado como comercial/superadmin.
   - ✅ JSON com `personagens` distintos; apoio/ensaio ausentes; vaga sem talento presente.
2. Sem permissão → 403/401.

## Checklist de qualidade (Portões da constituição)

- [ ] Sem migration (modelo inalterado).
- [ ] `ruff check` sem erros novos nos arquivos tocados.
- [ ] Verificado contra `manto_local` (Postgres).
- [ ] Recurso aditivo — calculadora e POST do orçamento sem regressão.
