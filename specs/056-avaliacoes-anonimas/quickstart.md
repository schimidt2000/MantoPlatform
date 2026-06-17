# Quickstart — Verificação manual da feature 056

Validar anonimato das avaliações, modo total, função no evento e aviso no portal, no app
real (`python run.py`).

> Pré-requisito: migration aplicada; existir ao menos uma avaliação com comentário, cujo
> autor tenha papel (função) cadastrado no evento.

## Passo 1 — Anônimo para não-super-admin (FR-001, SC-001)

1. Logar como usuário **CASTING** (não super admin) e abrir `/talents/avaliacoes`.
   - ✅ Todos os comentários e pontos de atenção mostram "Anônimo".
   - ✅ Nenhum nome, função ou link de perfil do autor aparece (inspecionar o HTML).
   - ✅ O botão de "modo anônimo total" **não** aparece.

## Passo 2 — Super admin vê o autor + função (FR-002, FR-008, SC-003)

1. Logar como **super admin**, modo total desligado, abrir a página.
   - ✅ Os nomes reais dos autores aparecem.
   - ✅ Ao lado do nome, a **função no evento** (personagem/papel) aparece quando houver.
2. Comentário de autor sem papel no evento:
   - ✅ Mostra só o nome, sem função, sem erro (FR-009).

## Passo 3 — Modo anônimo total (FR-003, FR-004, FR-005, SC-002)

1. Como super admin, clicar no botão para **ativar** o modo anônimo total (com confirmação;
   botão desabilita ao enviar).
   - ✅ Todos os comentários passam a "Anônimo", **inclusive para o super admin**.
   - ✅ Função some junto com o nome.
2. Recarregar / abrir em outra conta:
   - ✅ Estado persiste (global).
3. **Desativar** pelo botão.
   - ✅ Nomes (e funções) voltam para o super admin; seguem ocultos para os demais.
4. Tentar alternar como não-super-admin (via POST direto):
   - ✅ Recusado (sem efeito).

## Passo 4 — Aviso no portal (FR-007, SC-005)

1. No portal do talento, abrir a tela de avaliar um evento (nota geral e detalhada).
   - ✅ Há um aviso claro, em pt-BR, de que as avaliações são anônimas.

## Passo 5 — Não-regressão

1. Conferir que notas, médias, distribuição, ranking e tendência continuam corretos
   (a anonimização não altera números).
2. Conferir auditoria: a troca do modo total ficou registrada (FR-010).

## Checklist de qualidade (Portões da constituição)

- [ ] Migration aplicada (`flask db upgrade`); coluna `ratings_fully_anonymous` presente.
- [ ] `ruff check` sem erros novos nos arquivos tocados.
- [ ] Anonimato real conferido no HTML (nome/função ausentes quando anônimo).
- [ ] Comportamento conferido no app real (Princípio IV) — passos 1 a 5.
