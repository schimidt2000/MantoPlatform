# Data Model — Revisão 105

**Sem mudanças de dados.** Nenhuma entidade nova, nenhuma coluna nova, nenhuma migration.

A feature é inteiramente de camada de apresentação/rotas:

- `ReviewSpace` (existente): título e id usados para montar o texto/link do convite.
- Estado "recém-criado" é transiente (query param `?novo=1` no redirect) — não persiste.
- O progresso de upload é estado de UI (bytes enviados no cliente) — não persiste.
