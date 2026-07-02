# Contrato de Rotas — Revisão 105

Nenhuma rota nova. Três rotas existentes ganham um **modo JSON** ativado pelo header
`X-Requested-With: XMLHttpRequest` (fluxo com barra de progresso). Sem o header, o
comportamento atual (302 + flash) permanece intacto.

## `POST /revisao/novo` — new_space

| Fluxo | Resposta |
|---|---|
| Tradicional (sem header) | 302 → `/revisao/<id>?novo=1` (sucesso) ou re-render com erro |
| XHR, sucesso | `200 {"redirect": "/revisao/<id>?novo=1"}` — flashes (sucesso/avisos) ficam para a página de destino |
| XHR, validação (título vazio) | `400 {"error": "Informe um título para o espaço."}` |

Mudança adicional: o redirect de sucesso (ambos os fluxos) ganha `?novo=1` (destaque do
convite na tela do espaço).

## `POST /revisao/asset/<id>/replace` — replace_asset

| Fluxo | Resposta |
|---|---|
| Tradicional | 302 → tela do material (atual) |
| XHR, sucesso | `200 {"redirect": "/revisao/<space>/asset/<id>"}` |
| XHR, erro de validação (sem arquivo/tipo errado/512MB) | `400 {"error": "<mensagem atual>"}` (sem flash no modo XHR) |

## `POST /revisao/<id>/upload` — upload_assets (adicionar materiais)

| Fluxo | Resposta |
|---|---|
| Tradicional | 302 → tela do espaço (atual) |
| XHR, sucesso | `200 {"redirect": "/revisao/<id>"}` |

## Contrato do helper JS (`app/static/upload_progress.js`)

```js
uploadFormWithProgress(formElement, {
  progressEl,   // container da barra (recebe % via CSS width)
  labelEl,      // texto "45% — 135 MB de 300 MB"
  errorEl,      // onde exibir {"error": ...} sem recarregar
  submitBtn,    // botão a desabilitar/restaurar
})
```

Comportamento: intercepta `submit`; envia `FormData` via XHR com o header
`X-Requested-With`; `upload.onprogress` atualiza barra/label; sucesso →
`window.location = json.redirect`; erro/rede → mensagem amigável, form reabilitado, dados
intactos. Se o form não tiver arquivos selecionados, deixa o submit tradicional seguir
(sem barra).

## UI — convite (space.html)

- Botão "🔗 Copiar convite" (page actions) para todos com acesso ao espaço.
- Painel de destaque quando `?novo=1`: "Espaço criado! Envie o convite aos revisores" +
  o mesmo botão.
- Texto copiado: saudação + `"<título>"` + link absoluto do espaço + lembrete de login.
- Feedback: botão vira "✓ Copiado!" por ~2,5s; fallback: textarea readonly selecionada.
