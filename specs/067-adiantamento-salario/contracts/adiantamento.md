# Contrato: registrar adiantamento de salário (067)

## Endpoint

`POST /financeiro/pagamentos/salary/<int:sp_id>/advance` (multipart/form-data)

- **Acesso**: `require_financeiro` (financeiro/admin).
- **Campos**:
  - `advance_amount` (texto BR, ex. "300,00") — valor adiantado; vazio/0 = zerar.
  - `advance_proof` (arquivo, imagem/PDF) — comprovante.
  - `month` (para voltar à tela no mês certo).

### Regras

- `advance_amount > sp.amount` → recusa ("não pode exceder o salário").
- `advance_amount > 0` e **sem** comprovante novo nem existente → recusa ("comprovante
  obrigatório").
- `advance_amount` 0/vazio → zera `advance_amount` (comprovante deixa de ser exigido).
- Sucesso → salva `advance_amount`/`advance_proof`, audita, redireciona à tela de pagamentos.

## Efeito na listagem

- Item de salário: `amount` exibido = `sp.amount − advance_amount` (líquido); mostra também o
  adiantamento e link do comprovante.
- DRE/custo de salário: inalterado (usa `sp.amount` cheio).

## Critérios de aceite

- [ ] Adiantamento + comprovante → líquido reduzido; comprovante acessível.
- [ ] Adiantamento > 0 sem comprovante → recusado.
- [ ] Adiantamento > salário → recusado.
- [ ] Zerar adiantamento → volta ao valor cheio.
- [ ] Custo de salário do período inalterado.
