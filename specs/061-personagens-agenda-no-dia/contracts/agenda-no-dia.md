# Contrato: consulta de personagens na agenda por dia (061)

## Endpoint

`GET /orcamento/personagens-no-dia?date=YYYY-MM-DD`

- **Acesso**: autenticado + COMERCIAL/SUPERADMIN (`@login_required` + `@_require_vendas`).
- **Query param**: `date` (ISO `YYYY-MM-DD`).

### Resposta 200 (JSON)

```json
{
  "date": "2026-09-01",
  "personagens": [
    { "nome": "Homem-Aranha", "eventos": ["Festa X + Homem-Aranha"] },
    { "nome": "Elsa", "eventos": ["Aniversário Y", "Evento Z"] }
  ]
}
```

- `personagens`: ordenado por nome, **distinto** por `nome`; `eventos` lista os títulos do dia
  onde o personagem aparece.
- Apenas papéis `role_type = "character"`; exclui apoio (Coordenador, Técnico de Som, Presença,
  Maquiador) e eventos `ENSAIO`.

### Casos de borda

- `date` ausente/ inválida → `{ "date": null, "personagens": [] }` (HTTP 200, sem erro).
- Dia sem personagens → `{ "date": "...", "personagens": [] }`.

## UI (calculadora de orçamento)

- Campo de data recebe `id="event_date"`; container `#agenda-no-dia` logo abaixo do bloco
  data/horário.
- Ao `change` da data: busca o endpoint e renderiza:
  - **com personagens**: bloco de atenção "Já na agenda neste dia — não vender em dobro" + lista
    (nome + evento(s)).
  - **vazio**: "Nenhum personagem agendado neste dia."
  - **erro**: o bloco não é exibido (não quebra o orçamento).

## Critérios de aceite

- [ ] Datas com agenda retornam os personagens vendáveis distintos do dia.
- [ ] Apoio e ENSAIO nunca aparecem.
- [ ] Vaga sem talento aparece (personagem comprometido).
- [ ] Dia vazio → lista vazia → UI mostra estado vazio.
- [ ] Endpoint exige COMERCIAL/SUPERADMIN.
