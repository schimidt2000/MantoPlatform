# Contrato — elenco do evento (feature 322)

## `GET /api/events/<id>` — cada item de `elenco[]`

Chaves novas (todo papel que já recebe `elenco` recebe estas; nenhuma carrega dinheiro):

```jsonc
{
  "perfil": "Cantor · show · com maquiagem", // string | null — perfil_vendido (tipo + "show") seguido
                                              // das marcas das flags atuais ("cantor", "com maquiagem");
                                              // sem orçamento só as marcas; null quando não há nada
                                              // (converge: as marcas não são gravadas)
  "criada_pelo_sistema": true,                // boolean — vaga criada por regra do sistema
  "escalado_pelo_comercial": false            // boolean — o talento atual veio do formulário do evento
}
```

Inalterados: `needs_makeup`, `is_singer`, `cache_cap` e `cache_cap_note` (só superadmin), resumo
`maquiagem { precisa, fechado }`.

No TS (`RoleItem`), as três chaves nascem **opcionais** — bundle novo com servidor antigo (janela do
deploy, serviços separados no Render) lê `undefined` e não mostra nada.

## `PATCH /api/events/<id>` (formulário de edição)

- Papéis inalterados (`_can_edit_event`).
- `characters[].needs_makeup` é **ignorado** quando quem salva não é superadmin: vaga existente
  mantém o valor; vaga nova nasce sem maquiagem. Sem erro (a tela já trava a caixa).
- Depois de salvar, se algum personagem tem maquiagem e não há maquiador, a vaga "Maquiador" nasce.
- `characters[].talent_id` que troca o talento de uma vaga liga `escalado_pelo_comercial`; o mesmo
  vale para `coordinator_talent_id`.

## `POST /api/events` (criação)

- `characters[].needs_makeup` continua livre.
- Vagas pareadas com o orçamento recebem `perfil_vendido`.
- Pré-escala (`characters[].talent_id`, `coordinator_talent_id`) liga `escalado_pelo_comercial`.
- Personagem maquiado sem maquiador no orçamento → vaga "Maquiador" criada.

## `PATCH /api/events/<id>/orcamento` (vínculo 273)

- Personagem casado ganha `perfil_vendido` se não tinha.
- Extras criados levam `criada_pelo_sistema`.
- Depois do vínculo, a regra do maquiador roda.

## `POST /api/roles/<id>/assign` (card do casting)

- Trocar o talento (ou tirar) desliga `escalado_pelo_comercial`.
