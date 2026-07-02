# Research — Revisão: Progresso de Upload, Convite e Fix do Popup (105)

## R1. Por que o popup de histórico não fecha (causa raiz)

**Decision**: corrigir com uma regra CSS `.rv-modal[hidden] { display: none; }` em
`asset.html`.

**Rationale**: o modal usa o atributo `hidden` para abrir/fechar (JS seta
`modal.hidden = true/false`). O `hidden` funciona via regra do user-agent
(`[hidden] { display: none }`), que tem especificidade mínima — a regra da feature 104
`.rv-modal { display: flex; ... }` a sobrepõe, então o modal fica SEMPRE visível e o ✕
"não funciona" (o JS até seta `hidden`, mas o CSS ignora). Classe+atributo (0,2,0) vence.

**Alternatives considered**: trocar para classe `.open` controlada por JS — mais mudança
para o mesmo efeito; `<dialog>` nativo — suporte móvel ok hoje, porém reescrita
desnecessária. Rejeitados (fix de 1 linha resolve e mantém o padrão `hidden` do template).

## R2. Progresso real de upload

**Decision**: `XMLHttpRequest` + `FormData(form)` com `xhr.upload.addEventListener('progress')`
(e.loaded / e.total) num helper único `app/static/upload_progress.js` —
`uploadFormWithProgress(form, options)` — usado pelo form de criação e pelo de nova versão.

**Rationale**: `fetch()` não expõe progresso de UPLOAD (só de download; request streams ainda
são experimentais/limitados em Safari). XHR é universal, sem dependências, e o `onprogress`
entrega bytes reais → "45% — 135 MB de 300 MB". Helper único = fonte única (Princípio I).

**Alternatives considered**: libs (Uppy, tus) — peso e complexidade injustificados, sem
resume exigido; barra "fake" animada — proibida pela spec ("mostre de fato quanto está
subindo"). Rejeitados.

## R3. XHR × redirect × flash messages

**Decision**: as rotas `new_space` e `replace_asset` respondem
`{"redirect": "<url>"}` (200, JSON) quando o request traz
`X-Requested-With: XMLHttpRequest`; caso contrário mantêm o `redirect()` 302 atual. Helper
`_wants_json() -> bool` no blueprint. O cliente navega com `window.location = resp.redirect`.

**Rationale**: XHR segue 302 automaticamente (não dá para desligar) — o GET embutido
consumiria as flash messages ("Espaço criado…", avisos de arquivos rejeitados), que sumiriam
da navegação real. Devolver JSON evita o GET fantasma; as flashes ficam na sessão e aparecem
na página de destino. Erros de validação (ex.: título vazio) continuam re-renderizando o
form no fluxo tradicional e, no fluxo XHR, respondem `{"error": ...}` com status 400 para o
helper exibir sem recarregar (dados preservados — Constituição V).

**Alternatives considered**: `fetch(redirect:'manual')` — resposta `opaqueredirect` não expõe
a URL de destino; gravar flags na sessão — estado desnecessário. Rejeitados.

## R4. Botão "Copiar convite"

**Decision**: botão na tela do espaço (visível a quem pode ver o espaço), com texto do
convite embutido no template:

```text
Olá! 👋 Você foi adicionado(a) como revisor(a) de "<título>" na Plataforma Manto.
Acesse aqui: <link absoluto>
(entre com seu login de sempre)
```

Cópia via `navigator.clipboard.writeText()`; se rejeitar (HTTP local/permissão), abre um
`<textarea>` readonly com o texto selecionado para copiar manualmente. Confirmação:
botão vira "✓ Copiado!" por ~2,5s. Pós-criação: `new_space` redireciona para
`/revisao/<id>?novo=1` e o template destaca um painel de convite (uma vez, sem persistir
nada).

**Rationale**: clipboard API cobre produção (HTTPS); fallback cobre o resto; link usa
`url_for('revisao.space_detail', _external=True)` respeitando host/proxy. Sem entidade nova.

**Alternatives considered**: envio automático por WhatsApp/e-mail — integração fora do
escopo da spec (assumption registrada); link público sem login — mudaria o modelo de
permissões, explicitamente descartado (FR-010). Rejeitados.

## R5. Progresso também no "Adicionar materiais" do espaço

**Decision**: aplicar o mesmo helper no form de upload de `space.html` (rota
`upload_assets` ganha o mesmo modo JSON). Custo marginal ~zero por reusar o helper.

**Rationale**: assumption da spec ("por usar o mesmo padrão de envio") e Princípio I — deixar
um form de upload sem progresso criaria inconsistência visível.
