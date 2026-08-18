# Botao para visualizar catalogo (acesso rapido para qualquer pessoa do sistema, talvez perto da agenda)

## Resumo
Já existe um link "Catálogo" no menu interno (frontend/apps/internal/src/lib/navigation.tsx:299-308) que abre /catalogo/ em nova aba, mas ele está dentro da seção "Comercial" (bem abaixo de Agenda) e restrito a COMERCIAL/FINANCEIRO/SUPERADMIN. O pedido do João é mover esse acesso para perto da Agenda (primeira seção, sem label, visível a todos) e liberar para qualquer papel — o backend do catálogo já não exige login (app/catalogo/routes.py não tem login_required em nenhuma rota), então a restrição de hoje é puramente de menu, não de segurança.

## Comportamento atual (evidencia)
O item de menu "Catálogo" já existe hoje em frontend/apps/internal/src/lib/navigation.tsx:298-308, dentro da seção "Comercial":
- href: "/catalogo/", external: true, ícone BookOpen, hint "Abre o catálogo público em outra aba".
- isVisible: `(user) => notRevendedor(user) && hasRole(user, "COMERCIAL", "FINANCEIRO", "SUPERADMIN")` — ou seja, só aparece para quem tem um desses três papéis, e some completamente para REVENDEDOR_EDUCAMANTO e para qualquer papel puro que não seja esses três (ex.: CASTING, MARKETING, ARTISTA_3D, ENSAIO isolados não veem o link hoje).
- Fica na 4ª seção da sidebar (Comercial), bem abaixo da 1ª seção onde mora "Agenda" (navigation.tsx:97-105, isVisible: `everyone` — literalmente sempre true, inclusive para o perfil restrito REVENDEDOR_EDUCAMANTO).

Do lado do backend, `app/catalogo/routes.py` não tem nenhum `login_required`/checagem de papel nas rotas de índice, categoria ou detalhe do catálogo público (confirmado por grep: nenhuma ocorrência de `login_required` no arquivo) — a vitrine em `/catalogo/*` já é 100% pública/anônima por desenho (spec 185, US5, trata inclusive da diretiva de não-indexação para buscadores). Logo, restringir o link do menu por papel não protege nada — só esconde um atalho que qualquer pessoa poderia digitar na URL.

Spec 185-catalogo-vitrine-completo (specs/185-catalogo-vitrine-completo/spec.md) não trata de navegação interna/RBAC do link — é só sobre o conteúdo da vitrine (temas/personagens, vídeo, tags, auto-vínculo de figurino). docs/03_HISTORICO_MUTACOES.md confirma o histórico de mudanças de rota de `/catalogo` (raiz do domínio de vendas, `/catalogo/v/<slug>`, `/catalogo/midia/*` público) mas não menciona a posição do link no menu interno.

## Arquivos relevantes
- frontend/apps/internal/src/lib/navigation.tsx — Config declarativa da sidebar interna — contém o item 'catalogo-publico' (linhas 298-308) a ser movido/reliberado, e o item 'agenda' (linhas 97-105) que serve de referência de posição/visibilidade ('everyone').
- app/catalogo/routes.py — Blueprint público do catálogo — confirma que /catalogo/* não exige login nem papel, então a restrição de menu pode ser removida sem abrir superfície nova.
- specs/185-catalogo-vitrine-completo/spec.md — Spec mais recente do catálogo (conteúdo da vitrine); não cobre navegação interna, então este item não conflita com nada especificado lá.
- frontend/packages/ui/src/components/app-layout.tsx — Componente que renderiza as NavSectionData (sidebar) — não precisa mudar, só consumirá a nova posição do item.

## Abordagem proposta pela investigacao
Alteração é só de configuração declarativa em frontend/apps/internal/src/lib/navigation.tsx, sem endpoint novo, sem migração:

1. Remover o objeto do item `key: "catalogo-publico"` de dentro da seção "Comercial" (linhas 298-308).
2. Inserir um item equivalente na 1ª seção (sem label, a que hoje tem Home/Agenda/Gastos Extras — linhas 86-115), logo depois de "agenda" (ou antes de "gastos-extras", a definir com o João) para ficar fisicamente perto da Agenda como pedido.
3. Trocar `isVisible` de `(user) => notRevendedor(user) && hasRole(user, "COMERCIAL", "FINANCEIRO", "SUPERADMIN")` para `everyone` (mesma função já usada pela Agenda), liberando para "qualquer pessoa do sistema" — incluindo o perfil restrito REVENDEDOR_EDUCAMANTO, que hoje só vê Agenda + EducaManto (mesmo padrão que a própria Agenda já segue).
4. Manter `external: true` e `href: "/catalogo/"` como estão — já funciona (abre em nova aba, sem exigir sessão, confirmado pela ausência de login_required no backend).
5. Nenhuma mudança necessária no backend (app/catalogo/routes.py) nem no app-layout.tsx — a sidebar já sabe renderizar itens `external`.
6. Após a mudança, rodar `npx tsc --noEmit` em frontend/apps/internal (regra do projeto) e atualizar docs/02_MAPA_DE_PAGINAS_E_UX.md e docs/03_HISTORICO_MUTACOES.md conforme a regra de documentação viva do CLAUDE.md, já que é uma mudança de UX/navegação visível.

## Riscos mapeados
- Se REVENDEDOR_EDUCAMANTO ganhar acesso ao catálogo interno de vendas, isso pode expor um contexto comercial (preços/pacotes) que hoje esse perfil restrito não vê em nenhuma outra tela — vale confirmar com o João antes de estender a 'everyone' literal.
- Mover o item para a 1ª seção aumenta a altura dessa seção para todo usuário (inclusive quem já tinha o link mais abaixo) — impacto visual pequeno mas real na sidebar.