<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Feature [NNN] — [TÍTULO CURTO, EM PT-BR, QUE DIZ O QUE MUDA PARA QUEM USA]

**Branch**: `[NNN-nome-curto]` (da `main`) · **Created**: [AAAA-MM-DD] · **Status**: Rascunho ·
**Migration**: nenhuma | `<rev>` (aditiva | destrutiva — destrutiva exige ensaio em banco descartável,
`DEVELOPMENT.md` §Migrations) · **Nível**: 1 (feature) | 2 (correção) — constituição, Princípio VI

**Input**: pedido do dono: "$ARGUMENTS"

## O pedido, nas palavras do dono *(obrigatório)*

[Cite o pedido. Se veio de incidente ou print, descreva o sintoma como a pessoa viu — é o que
diz se a feature resolveu.]

## Cenários e Verificação *(obrigatório)*

<!--
  Histórias PRIORIZADAS (P1 = MVP) e INDEPENDENTES: cada uma implementável, verificável e
  entregável sozinha. Cada história nomeia o cenário do verify_NNN.py que a prova (Princípio VIII).
-->

### História 1 — [Título] (Prioridade: P1)

[Jornada em linguagem simples: quem, faz o quê, e o que muda para essa pessoa.]

**Por que esta prioridade**: [valor para quem usa]

**Verificação**: cenário [N] do `verify_NNN.py` — [o que ele prova, contra `manto_local`]

**Cenários de aceite**:

1. **Dado** [estado inicial], **Quando** [ação], **Então** [resultado esperado]
2. **Dado** [estado inicial], **Quando** [ação], **Então** [resultado esperado]

---

### História 2 — [Título] (Prioridade: P2)

[Jornada]

**Por que esta prioridade**: [valor]

**Verificação**: cenário [N] do `verify_NNN.py`

**Cenários de aceite**:

1. **Dado** [estado inicial], **Quando** [ação], **Então** [resultado esperado]

---

[Mais histórias, cada uma com prioridade]

### Casos de borda

- O que acontece quando [condição de fronteira]?
- Como o sistema trata [erro / dado ausente / concorrência]?

## Requisitos *(obrigatório)*

### Requisitos funcionais

- **FR-001**: O sistema DEVE [capacidade específica e testável]
- **FR-002**: O sistema DEVE [capacidade]
- **FR-003**: [Quem] DEVE poder [interação-chave]

*Marcação de dúvida (máx. 3 na spec inteira)*:

- **FR-00X**: O sistema DEVE [...] [NEEDS CLARIFICATION: pergunta específica]

### Entidades *(se houver dados)*

- **[Entidade]**: [o que representa, atributos-chave, relações] — modelo em `app/models.py`,
  migration à mão

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

- `[MÉTODO /api/...]` — papéis: [...] (Princípio XIII); linha na tabela de `docs/01` §4.3

## Verificação (`verify_NNN.py`) *(obrigatório — Princípio VIII)*

<!-- Esta seção é o que faz o /speckit-tasks gerar a tarefa do verify ANTES do núcleo. -->

Arquivo: `specs/NNN-nome/verify_NNN.py`, contra `manto_local` (`DATABASE_URL` de `.local-db-url`,
`FLASK_ENV=development`, `MANTO_SEM_THREADS=1`). Login só por `POST /api/auth/login`; escrita
conferida por conexão separada; limpeza no `finally`.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | [...] | [...] | não |
| N | [papel sem permissão tenta] | 403/404 | **sim** |
| N+1 | limpeza | usuários e registros descartáveis apagados (`roles.clear()` antes do usuário) | — |

Conferência de tela (se tocar UI): [telas a abrir no Browser pane; superfície pública em
viewport mobile 375×812].

## Critérios de sucesso *(obrigatório)*

- **SC-001**: [métrica mensurável do ponto de vista de quem usa, sem tecnologia]
- **SC-002**: [...]

## Fora de escopo

- [o que NÃO entra, para a spec não crescer no implement]

## Docs a atualizar

`docs/01` [§], `docs/02` [tela], `docs/03` (entrada no topo); [`docs/00` / `04` / `05` se a mudança
tocar topologia, invariante de domínio ou dívida].

## Premissas

- [defaults assumidos onde o pedido não disse]
