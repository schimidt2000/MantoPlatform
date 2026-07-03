# Research — Auditoria Mobile do Portal + Validação do Cadastro (106)

Auditoria executada tela a tela (código-fonte + regras responsivas existentes do
`app/static/style.css`, bloco `@media (max-width: 768px)` linhas ~989–1014).

## O que JÁ está coberto (não mexer, não regredir)

- `portal-header` empilha em ≤768px (style.css) ✅
- `.invite-actions` empilha botões; `.invite-detail-row` empilha label+valor ✅
- `.grid-medidas` (perfil, 4 colunas) vira 2 colunas em ≤768px ✅
- `login.html`, `rate.html` (estrelas 40px, botões full-width), `figurino_viewer.html`
  (lightbox com pinch-zoom) — já mobile-friendly ✅
- Cadastro: telefone/DDI empilha em ≤480px (feature 092) ✅
- Todos os templates têm `<meta name="viewport">` ✅

## Achados (A–H) — o que corrigir

### A. Dinheiro em formato AMERICANO no portal (viola Constituição VII) — CRÍTICO

`R$ {{ "{:,.0f}".format(...) }}` produz "R$ 4,000" (milhar com vírgula).
Ocorrências: `home.html` (cachê do convite + transporte, cachê do card de evento +
transporte, financeiro Recebido/Pendente, histórico recente) e `historico.html`
(3 cards de resumo + valor por evento).

**Decision**: usar o filtro existente `| brl` (`app/money.py`, registrado em
`app/__init__.py:208`) — `R$ {{ x | brl }}`. Única fonte de formatação (Princípio VII).
**Alternatives**: criar helper local no template — proibido (fonte única).

### B. home.html

1. Materiais de ensaio com `margin-left:98px` — o indent alinhava com o label em desktop,
   mas os detail rows empilham no mobile → 98px come 1/4 da tela. **Decision**: 16px fixo.
2. "Histórico recente": cluster direito (`flex-shrink:0` com botão Avaliar + valor + badge)
   pode estourar 360px. **Decision**: permitir `flex-wrap` no cluster e no row.

### C. profile.html

1. 4 pares inline `style="display:grid; grid-template-columns: 1fr 1fr"` (tel/e-mail,
   nascimento/gênero, raça/idiomas, PIX tipo/chave, RG/CNH) não colapsam (a media query
   existente só cobre `.grid-medidas`). **Decision**: classe `.grid-pair` + regra
   `@media (max-width:480px) { .grid-pair { grid-template-columns: 1fr !important; } }`
   no style.css (bloco portal).
2. Botão × de remover foto: 20×20px — alvo de toque pequeno demais. **Decision**: 28×28px
   visível (fica sobre a foto; 44px cobriria a imagem).
3. Cores hardcoded tocadas pelo checkup: `#666`, `#888` → `var(--muted)`; `#e0e0e0`,
   `#f0f0f0` → `var(--line)`; `#e45858` (× de link) → `var(--red)`.

### D. Touch targets globais do portal

`.btn-sm` = ~26px de altura. **Decision**: no bloco portal do style.css:
`@media (max-width:768px) { .portal-wrap .btn { min-height:44px; align-items:center; } }`
— cobre home (Termo/Perfil/Sair, Avaliar, figurino), histórico, profile, figurino_viewer.

### E. historico.html

Só o dinheiro (achado A); o cluster direito já empilha em coluna. ✅ restante ok.

### F. rate_detail.html

`.mini-stars label` 26px com gap 2px → alvos de ~26px colados. **Decision**: 30px,
gap 6px, padding 2px 4px (alvo efetivo ≥38px por estrela; rate.html usa 40px e está ok).

### G. Fontes < 12px (FR-003)

`.days-badge`/`.pay-badge` 11px (home/histórico), hint "Estrangeiros sem CPF" 11px (login),
`.fig-photo-hint` 11px (figurino) → 12px. Metadados 11px com peso normal viram 12px onde
tocados.

### H. Telas residuais

`first_access`, `forgot_password`, `reset_password`, `change_password` (usam auth-card,
pequenas) e `terms.html` (max-width 720 + media queries próprias): verificação de
renderização + viewport no implement; ajustes apenas se aparecer problema concreto.

## Cadastro — validação com feedback (US2)

**Estado atual** (`app/templates/cadastro/form.html`):
- Grupos obrigatórios (idiomas/habilidades): `alert()` + `scrollIntoView` — sem destaque
  visual no grupo, mensagem efêmera fora da página.
- Campos `required`: balão nativo do navegador (some sozinho, fácil de perder num
  formulário longo; sem lista de todos os problemas).
- Sem limpeza de estado de erro ao corrigir.

**Decision** (contrato completo em [contracts/ui-contract.md](./contracts/ui-contract.md)):

1. `novalidate` no `<form>` — assume-se o controle da validação (o HTML `required`
   continua nos campos como fonte da regra, lido via `field.willValidate/checkValidity`).
2. No submit: coletar campos inválidos (`:invalid`, ignorando `disabled` e invisíveis) e
   grupos `data-required-group` sem seleção; para cada um: classe `.field-invalid` no
   container `.field` (borda `var(--danger)` + animação shake 400ms) + mensagem
   `.field-errmsg` logo abaixo (texto do `data-required-group` para grupos; mensagem padrão
   pt-BR por tipo para campos).
3. Rolar até o PRIMEIRO inválido (`scrollIntoView({block:'center'})`) e focar
   (`focus({preventScroll:true})`).
4. Ao corrigir (`input`/`change`), remover destaque e mensagem daquele campo.
5. Só travar o botão ("Enviando…") quando o form passa na validação.
6. Sem `alert`; dados preservados (nenhum reset).

**Alternatives considered**: manter balão nativo + só estilizar `:invalid` — não rola até o
campo em todos os navegadores, não mostra múltiplos erros, e o balão some; biblioteca de
validação — proibido (sem libs novas, página standalone). Rejeitados.
