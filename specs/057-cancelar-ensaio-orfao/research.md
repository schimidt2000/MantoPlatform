# Research: Cancelar ensaio órfão

Decisões técnicas da feature 057. Sem `NEEDS CLARIFICATION` pendentes.

---

## 1. A ação de cancelar já existe — reusar `delete_ensaio`

- **Decisão**: reusar a rota `POST /events/<id>/delete-ensaio` (`delete_ensaio`), que: valida
  `event_type == "ENSAIO"`, valida RBAC (`_CAN_ENSAIO`), remove do Google Calendar (com aviso
  se falhar), apaga o ensaio do banco e redireciona — **para o show pai se existir, senão
  para a home**. Já trata o caso órfão.
- **Rationale**: Princípio I — não criar uma segunda rota de cancelamento. O gap é só de UI.
- **Alternativas**: nova rota dedicada a órfãos (rejeitado: duplicaria a lógica existente).

## 2. Como identificar um ensaio órfão

- **Decisão**: órfão = evento com `event_type == "ENSAIO"` e **sem show pai existente**, i.e.
  a relação `parent` é `None` (cobre tanto `parent_event_id` nulo quanto FK apontando para um
  show já removido). Na home, consultar os ensaios e filtrar `e.parent is None`.
- **Rationale**: o cenário real (show removido + re-sync) gera ensaios reimportados sem
  `parent_event_id`; `e.parent is None` também cobre FK pendente. Volume pequeno → filtro
  simples é suficiente.
- **Alternativas**: só `parent_event_id IS NULL` (rejeitado: não cobre FK pendente);
  outerjoin SQL (desnecessário para o volume).

## 3. Incluir órfãos passados

- **Decisão**: a lista de órfãos **não** filtra por data futura (o caso relatado é de
  novembro/passado). Mostra todos os órfãos para limpeza.
- **Rationale**: FR-002; o objetivo é justamente limpar ensaios antigos pendurados.
- **Alternativas**: só futuros (rejeitado: deixaria o caso do usuário de fora).

## 4. Onde expor o cancelamento

- **Decisão**: três pontos, todos reusando `delete_ensaio` com confirmação:
  1. **Home — seção "Ensaios sem show (órfãos)"** no setor de ensaios (lista os órfãos com
     botão "Cancelar ensaio"). Resolve diretamente o problema relatado.
  2. **Página do ensaio** (`event_detail` quando `event_type == "ENSAIO"`): banner com botão
     "Cancelar ensaio" — funciona para qualquer ensaio (órfão ou não).
  3. **Home — lista "Ensaios agendados"**: adicionar "Cancelar" ao lado de "Editar".
- **Rationale**: cobre tanto a descoberta (home órfãos) quanto o acesso direto (página do
  ensaio) e a conveniência (home agendados). Princípio V (confirmação em ação destrutiva).
- **Alternativas**: só a página do ensaio (rejeitado: o usuário precisa **achar** o órfão
  primeiro — a home órfãos resolve a descoberta).

## 5. Permissões

- **Decisão**: a opção só aparece e só executa para os perfis de `_CAN_ENSAIO` (ENSAIO,
  CASTING, SUPERADMIN), iguais aos que já criam/editam/cancelam ensaios. A própria rota já
  recusa os demais (403).
- **Rationale**: FR-007; sem ampliar permissões.

## 6. Sem mudança de modelo / migration

- **Decisão**: nenhuma. Reusa `CalendarEvent`/`parent`. A descoberta de órfãos é só leitura.
- **Rationale**: o gap é de exposição na UI, não de dados.
