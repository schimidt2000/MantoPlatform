# Implementation Plan: Checkup Mobile do Portal + Feedback de Validação no Cadastro

**Branch**: `106-portal-mobile-cadastro-feedback` | **Date**: 2026-07-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/106-portal-mobile-cadastro-feedback/spec.md`

## Summary

Checkup mobile do Portal do Artista guiado por **auditoria já executada** das 12 telas
(achados concretos em [research.md](./research.md)) + validação com feedback visual completo
no `/cadastro` (substitui `alert`/balão nativo por: scroll até o campo, borda de erro +
shake, mensagem junto ao campo, foco — Princípio V da constituição).

Achado extra da auditoria que entra no escopo por ser violação da constituição (VII):
o portal formata dinheiro com `"{:,.0f}".format(...)` (padrão americano, ex.: "4,000") em
`home.html` e `historico.html` — o filtro `| brl` (fonte única, `app/money.py`) existe e não
é usado ali.

## Technical Context

**Language/Version**: Python 3.12 + Flask; templates Jinja2 + CSS/JS vanilla

**Primary Dependencies**: nenhuma nova — CSS existente (`app/static/style.css` já tem bloco
`@media (max-width: 768px)` com regras do portal), filtro Jinja `brl` já registrado
(`app/__init__.py:208`)

**Storage**: nenhuma mudança — zero migrations

**Testing**: test client contra `manto_local` (requests fora de app_context) para renderização
e presença dos elementos; conferência visual em 320/360/390/430px

**Target Platform**: smartphones (Safari iOS / Chrome Android) — portal e cadastro são as
superfícies públicas

**Project Type**: web app Flask monolítico

**Performance Goals**: nenhum impacto — mudanças de CSS/HTML/JS local

**Constraints**: não redesenhar telas nem mudar fluxos; trocar cores hardcoded por variáveis
apenas onde o checkup tocar; não regredir regras responsivas existentes (ex.: empilhamento do
telefone/DDI no cadastro)

**Scale/Scope**: ~7 templates do portal tocados + `style.css` (bloco portal) +
`cadastro/form.html` (CSS+JS de validação); rotas intocadas

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar antes de criar | ✅ Usa o filtro `brl` existente (não reinventa formatação); media queries entram no bloco portal já existente do `style.css`; validação do cadastro num único bloco JS do próprio form (página standalone). |
| II. Padrões Python | ✅ Nenhuma mudança Python além de templates (rotas intocadas). |
| III. Arquitetura em camadas | ✅ Só apresentação. |
| IV. Não quebrar o que funciona | ✅ Auditoria primeiro, mudanças pontuais por tela, verificação de renderização + fluxos após cada fase. Regras responsivas existentes preservadas. |
| V. UI/UX + feedback | ✅ É o objetivo da feature — inclusive implanta a regra de feedback de campo no /cadastro (scroll + destaque + foco + mensagem, sem limpar dados). |
| VI. Planejar antes de codar | ✅ Este plano, com auditoria prévia. |
| VII. Valores monetários BR | ✅ Corrige violação existente no portal (`{:,.0f}` → `| brl`). |

**Gate: PASS.**

## Project Structure

### Documentation (this feature)

```text
specs/106-portal-mobile-cadastro-feedback/
├── plan.md              # Este arquivo
├── research.md          # Auditoria mobile tela a tela (achados A–H)
├── data-model.md        # Sem entidades — registro
├── quickstart.md        # Roteiro de verificação (viewports + fluxos)
├── contracts/
│   └── ui-contract.md   # Contrato de comportamento da validação do cadastro
└── tasks.md             # Fase 2
```

### Source Code (repository root)

```text
app/
├── static/style.css                       # bloco portal @media 768: touch targets ≥44px,
│                                          #   colapso .grid-pair, fontes mínimas de badges
└── templates/
    ├── portal/
    │   ├── home.html                      # dinheiro → |brl; indent 98px; wrap do histórico
    │   ├── historico.html                 # dinheiro → |brl
    │   ├── profile.html                   # .grid-pair nos pares 1fr 1fr; × de foto maior;
    │   │                                  #   cores hardcoded → vars
    │   ├── rate_detail.html               # mini-stars maiores (toque)
    │   └── (demais telas: ajustes só se a auditoria residual apontar)
    └── cadastro/form.html                 # novalidate + validação própria: destaque, scroll,
                                           #   foco, mensagens por campo/grupo, limpeza ao corrigir
```

**Structure Decision**: mudanças 100% em templates + CSS compartilhado; nenhum arquivo novo
além dos artefatos de spec.

## Decisões de design (detalhe em research.md)

1. **Dinheiro no portal**: trocar `R$ {{ "{:,.0f}".format(x) }}` por `R$ {{ x | brl }}`
   (menor diff; filtro é a fonte única). 7+ ocorrências entre home e histórico, incluindo
   cachê/transporte dos convites.
2. **Touch targets**: regra no bloco portal do `style.css` —
   `@media (max-width:768px) { .portal-wrap .btn { min-height:44px; } }` (+ × de remover
   foto/link do profile ≥28px visível com área de toque maior).
3. **Profile**: classe `.grid-pair` nos 4 pares inline `1fr 1fr` + media query ≤480px → 1
   coluna; greys hardcoded → `var(--muted)`/`var(--line)`; × de foto 20px → 28px.
4. **Home**: indent dos materiais de ensaio 98px → 16px; cluster direito do "Histórico
   recente" ganha `flex-wrap` para não estourar 360px.
5. **Badges/hints 11px → 12px** (FR-003): `.days-badge`, `.pay-badge`, hints de login e
   figurino viewer.
6. **rate_detail**: `.mini-stars label` 26px → 30px + gap 6px + padding (alvo de toque
   maior; o label inteiro é o alvo do rádio estilizado).
7. **Cadastro — validação própria**: `novalidate` no form (suprime o balão nativo); no
   submit coleta `:invalid` visíveis/habilitados + grupos `data-required-group` sem seleção;
   marca todos (`.field-invalid` no container + mensagem `.field-errmsg`), rola até o
   primeiro (`scrollIntoView` center) e foca; erro some no `input/change`; botão reabilita;
   grupos deixam de usar `alert`. CSS: borda `var(--danger)` + keyframes shake (~400ms).
   Arquivos obrigatórios recebem o mesmo tratamento.
8. **Auditoria residual** (first_access, forgot/reset, change_password, terms): verificação
   no implement; ajustes só se algo concreto aparecer (login e figurino_viewer já auditados
   — ok).

## Complexity Tracking

Sem violações — tabela não aplicável.
