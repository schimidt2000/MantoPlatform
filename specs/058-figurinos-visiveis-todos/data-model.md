# Data Model: Figurinos visíveis a todos (edição restrita)

## Mudança no modelo

**Nenhuma.** Sem nova coluna, sem nova entidade, sem migration. A feature é puramente de
controle de acesso (visualização aberta a todos; edição restrita).

## Entidade reutilizada (`FigurinoSheet`)

Sem alteração de campos. O que muda é **quem pode ler vs. editar**.

## Regra de autorização (derivada)

```
pode_ver_figurinos    ⇔  usuário autenticado (qualquer perfil)
pode_editar_figurinos ⇔  usuário tem papel SUPERADMIN ou FIGURINO
```

| Rota / Ação | Tipo | Acesso depois da feature |
|---|---|---|
| `GET /figurinos` (lista) | leitura | qualquer autenticado |
| `GET /figurinos/<id>/print` | leitura | qualquer autenticado |
| `GET /figurinos/print-event/<id>` | leitura | qualquer autenticado |
| `GET/POST /figurinos/new` | edição | SUPERADMIN/FIGURINO (senão 403) |
| `GET/POST /figurinos/<id>/edit` | edição | SUPERADMIN/FIGURINO (senão 403) |
| `POST /figurinos/<id>/rotate-photo` (girar foto) | edição | SUPERADMIN/FIGURINO (senão 403) |
| `POST /figurinos/<id>/delete` | edição | SUPERADMIN/FIGURINO (senão 403) |
| `GET /figurinos/sync-drive` (+ stream) | edição | SUPERADMIN/FIGURINO (senão 403) |

> Os caminhos exatos de `rotate-photo`/`delete`/`sync` seguem os já definidos em
> `figurino/routes.py`; a feature só adiciona a guarda de papel no topo de cada um.

## Migração

Nenhuma.
