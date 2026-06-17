# Research: Avaliações anônimas + função no evento

Decisões técnicas da feature 056. Sem `NEEDS CLARIFICATION` pendentes.

---

## 1. Anonimização no servidor (não no cliente)

- **Decisão**: decidir a autoria no servidor. Calcular `show_authors = is_superadmin and
  not settings.ratings_fully_anonymous`. Em `_comment_item`, quando `show_authors` é falso,
  `author = "Anônimo"` e `função = None` — o nome/função **não** entram no HTML.
- **Rationale**: FR-006/privacidade — esconder via CSS deixaria o dado no HTML (inspeção
  revelaria). A anonimização tem de ser na origem.
- **Alternativas**: ocultar no template/CSS (rejeitado: vaza o dado no HTML).

## 2. Modo anônimo total: flag global em `SiteSetting`

- **Decisão**: novo campo `SiteSetting.ratings_fully_anonymous` (Boolean, default False),
  no singleton `SiteSetting` (id=1). Um botão na página faz POST para alternar.
- **Rationale**: "um botão na página" = interruptor único e persistente; `SiteSetting` já é
  a fonte de config global do sistema (Princípio I).
- **Alternativas**: flag por comentário (rejeitado: o pedido fala de um botão único na
  página); estado em sessão (rejeitado: não é persistente nem global, fere FR-005).

## 3. Quem controla o toggle: somente super admin

- **Decisão**: a rota de toggle exige super admin; o botão só é renderizado para super
  admin. Demais perfis nunca veem o autor mesmo, então o botão não faz sentido para eles.
- **Rationale**: FR-003/FR-004 — o modo total afeta o que o super admin vê; é um controle de
  governança de privacidade.
- **Alternativas**: qualquer um com acesso à página alterna (rejeitado: muda o que o super
  admin vê sem ser decisão dele).

## 4. Auditoria do toggle: `AuditLog`

- **Decisão**: registrar a mudança do modo total em `AuditLog` (entity_type="site_setting",
  action="ratings_fully_anonymous_on/off", detail com autor) — log de sistema, não por
  evento.
- **Rationale**: FR-010 + Princípio I; `AuditLog` é o mecanismo geral de auditoria de
  sistema (vs. `EventLog`, que é por evento).
- **Alternativas**: `EventLog` (rejeitado: é por evento; o toggle é global).

## 5. Função no evento: `EventRole` em uma query batch

- **Decisão**: para os comentários exibidos com autoria, montar um mapa
  `{(event_id, talent_id): "função"}` com **uma** query a `EventRole` filtrando pelos pares
  exibidos; a função é o `character_name` (com `strip_role_prefix`, já existente). Mais de
  uma função → juntar por vírgula.
- **Rationale**: FR-008/Princípio IV (sem N+1). Reusa `strip_role_prefix`.
- **Alternativas**: 1 query por comentário (rejeitado: N+1); guardar função na avaliação
  (rejeitado: dado já existe em `EventRole`, não duplicar).

## 6. "Autor" = talento que avaliou; subject inalterado

- **Decisão**: o anonimato protege `rating.talent` (quem avaliou). A exibição de
  `subject_talent` (pessoa avaliada em subcategoria) **não muda** nesta feature.
- **Rationale**: escopo do pedido (autoria do comentário). Mexer no subject seria
  ampliar escopo sem pedido.
- **Alternativas**: anonimizar subject também (adiado: não solicitado).

## 7. Aviso de anonimato no portal

- **Decisão**: adicionar um aviso textual (pt-BR) nas telas de avaliação do portal
  (`rate.html` e `rate_detail.html`), no padrão visual existente (alert/aviso), sem alterar
  o fluxo de envio.
- **Rationale**: FR-007; informativo, baixo risco.
- **Alternativas**: aviso só em uma das telas (rejeitado: ambas coletam avaliação).

## 8. Migration manual

- **Decisão**: `..._ratings_fully_anonymous.py`, `down_revision = r4a5b6c7d8e9`,
  `add_column` com `server_default="0"` para linhas existentes nascerem com modo desligado.
- **Rationale**: autogenerate quebrado por drift (memória do projeto); default desligado
  preserva o comportamento atual (super admin vê autor).
