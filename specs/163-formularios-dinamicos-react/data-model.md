# Data Model: Formulários Dinâmicos Públicos em React

Nenhum campo ou tabela novos. Os endpoints só leem `FormFieldDefinition` e criam `FormResponse`
(`app/models.py`) exatamente como o handler Jinja hoje (`_load_fields`, `_save_response`,
`_build_sections_dynamic` — inalterados, só importados).

## Schema de campo (serialização de `FormFieldDefinition` para a API — só leitura)

| Campo JSON | Origem | Observação |
|---|---|---|
| `key` | `field_key` | chave estável, nome do campo no `FormData` |
| `type` | `field_type` | um de `texto_curto/texto_longo/selecao/data/hora/telefone/email/cpf/cnpj/cep/sim_nao` |
| `label` | `label` | rótulo exibido |
| `help_text` | `help_text` | texto de ajuda opcional |
| `placeholder` | `placeholder` | opcional |
| `required` | `required` | booleano |
| `options` | `options_list` | só quando `type === "selecao"`, senão `null` |

Resposta de `GET /api/formularios/<form_type>/schema`:

```json
{
  "title": "…", "header": "…",
  "sections": [{ "secao": "Nome da seção", "campos": [ /* campos acima */ ] }]
}
```

## FormResponse — criado pelo POST (sem mudança de shape)

Mesmos campos já preenchidos por `_save_response`/`_submit_public_form` hoje: `form_type`,
`data` (JSON das seções `[chave, rótulo, valor]`), `contact_name`, `contact_phone`
(normalizado), `contact_phone_display`, `event_date`, e o vínculo automático de evento
(`event_id`/`event_link_source`/`event_link_ambiguous`, via `_attempt_auto_link` — sem mudança).
