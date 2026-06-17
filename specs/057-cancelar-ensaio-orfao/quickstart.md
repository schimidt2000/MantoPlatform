# Quickstart — Verificação manual da feature 057

Validar o cancelamento de ensaios órfãos e a exposição do botão, no app real
(`python run.py`), logado com perfil de ensaio (ENSAIO/CASTING/SUPERADMIN).

> Pré-requisito para simular o órfão: ter (ou criar) um evento `event_type="ENSAIO"` sem
> show pai (`parent is None`) — equivale ao ensaio cujo show foi removido da agenda.

## Passo 1 — Órfão aparece e pode ser cancelado pela home (US1, FR-001/FR-002)

1. Abrir a home com perfil de ensaio.
2. No setor de Ensaios, conferir a seção **"Ensaios sem show (órfãos)"**.
   - ✅ O ensaio órfão (inclusive de data passada, ex.: novembro) aparece listado.
3. Clicar em **"Cancelar ensaio"** e confirmar.
   - ✅ Mensagem de sucesso; o órfão some do sistema e da agenda (Google Calendar).
4. Recarregar a home.
   - ✅ O órfão não aparece mais.

## Passo 2 — Botão na própria página do ensaio (US2, FR-003)

1. Abrir a página de um evento do tipo ensaio (órfão ou não).
   - ✅ Há um botão **"Cancelar ensaio"** (com confirmação).
2. Cancelar um ensaio **com** show pai por essa página.
   - ✅ Volta para a página do show pai; o **show não é afetado** (FR-004).
3. Cancelar um ensaio **sem** show pai.
   - ✅ Volta para a home, sem erro.

## Passo 3 — Cancelar na lista "Ensaios agendados" da home (US3, FR-008)

1. Na home, no painel "Ensaios agendados" (ensaios sob um show), localizar um ensaio.
   - ✅ Há **"Cancelar ensaio"** ao lado de "Editar".
2. Cancelar e confirmar.
   - ✅ O ensaio some; o show pai permanece.

## Passo 4 — Permissão (FR-007)

1. Acessar com um perfil **sem** gestão de ensaio.
   - ✅ Os botões de cancelar não aparecem; a rota recusa (403) se chamada direto.

## Passo 5 — Falha externa graciosa (FR-006)

1. Cancelar um ensaio sem vínculo com o Google (ou simular falha).
   - ✅ O ensaio é removido do sistema; se o Google falhar, aparece aviso (sem travar).

## Checklist de qualidade (Portões da constituição)

- [ ] Sem migration (modelo inalterado).
- [ ] `ruff check` sem erros novos nos arquivos tocados.
- [ ] Confirmação presente em todos os botões de cancelar (ação destrutiva).
- [ ] Comportamento conferido no app real (Princípio IV) — passos 1 a 5.
