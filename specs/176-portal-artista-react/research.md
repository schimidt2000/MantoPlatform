# Research: Portal do Artista — App React (fatia 1)

## Decisão: sessão do app novo reaproveita a sessão Flask do portal clássico

- **Decisão**: `POST /api/portal/auth/login` seta `session["talent_id"]` — a MESMA chave que
  `app/talent_portal/routes.py::login()` já usa. `GET /api/portal/auth/me` e as demais rotas de
  API leem a mesma chave.
- **Racional**: Talent não é um `User` do Flask-Login (é uma entidade própria, sem os decorators/
  `current_user` do staff). Criar um segundo mecanismo de sessão paralelo duplicaria lógica de
  autenticação e criaria um cookie extra sem necessidade — reaproveitar a sessão existente
  significa que um talento logado no app novo também está logado na versão clássica (útil
  durante a transição, já que algumas telas só existem lá) e vice-versa.
- **Alternativas consideradas**: JWT próprio para o portal — rejeitado, adicionaria uma segunda
  forma de autenticação ao projeto sem necessidade (Princípio I); o cookie de sessão HttpOnly já
  atende ao mesmo requisito de segurança que o resto do projeto usa para o staff.

## Decisão: login bloqueado quando `must_change_password`/termos pendentes

- **Decisão**: `POST /api/portal/auth/login` retorna sucesso normal (200, sessão aberta) mas com
  um campo `must_redirect_to_classic: true` quando a conta ainda exige troca de senha ou aceite
  de termos; o app React, ao ver esse campo, faz um redirect de página inteira (não SPA) para
  `/portal/login` (Jinja), que já trata essas duas etapas.
- **Racional**: reproduzir as telas de troca de senha/termos no app novo está fora do escopo
  desta fatia (spec, Assumptions); a alternativa de simplesmente negar o login deixaria o
  talento sem conseguir prosseguir em NENHUM lugar. Redirecionar para a versão clássica (que já
  resolve as duas etapas) preserva o acesso sem duplicar tela.
- **Alternativas consideradas**: bloquear o login com erro genérico — rejeitado, sem saída para
  o talento; reproduzir troca de senha/termos no app novo — rejeitado por escopo (fatia futura).

## Decisão: identidade visual própria (preset Tailwind dedicado, não o do `internal`)

- **Decisão**: `frontend/apps/portal` ganha seu próprio `tailwind.config.ts` com tokens portados
  de `app/templates/portal/*` (cores/tipografia do portal clássico), usando os MESMOS nomes de
  token que `internal`/`public` (`bg`/`panel`/`ink`/`accent`/etc.) para que os componentes
  `@manto/ui` herdem a identidade automaticamente — mesmo padrão já usado na criação do `public`
  (feature 161, `research.md §1`).
- **Racional**: o Portal do Artista é uma superfície voltada a talentos externos, com identidade
  visual própria no sistema clássico — não faz sentido herdar o preset do painel administrativo
  interno (`internal`).
- **Alternativas consideradas**: reusar o preset do `internal` — rejeitado, identidade errada
  para o público-alvo (talentos, não staff).

## Decisão: mobile-first com navegação inferior (bottom nav), não sidebar

- **Decisão**: o shell autenticado do app usa uma barra de navegação inferior fixa (Agenda /
  Convites / Fotos-Documentos) em vez do menu lateral do `internal` — ficha de figurino é
  acessada a partir de um evento na Agenda, não é um item de nav de primeiro nível.
- **Racional**: Princípio VIII (mobile-first, NÃO-NEGOCIÁVEL) — bottom nav é o padrão de
  usabilidade mobile para 3-4 destinos principais; sidebar (padrão do `internal`, pensado para
  desktop com muitos itens) não se aplica a uma superfície mobile-only.
- **Alternativas consideradas**: menu hambúrguer (como o `internal` usa no mobile) — rejeitado,
  esconde a navegação primária atrás de um toque extra, pior para os 3 destinos de uso diário.

## Decisão: upload de foto/CNH reaproveita `app/storage.py`

- **Decisão**: os novos endpoints de upload chamam `app.storage.save_file`, mesma abstração
  local/S3 já usada por `app/cadastro` e pelo próprio `app/talent_portal/routes.py` legado.
- **Racional**: fonte única de upload (Princípio I); nenhuma mudança de infraestrutura
  necessária — mesmos limites/formatos já aceitos hoje.
- **Alternativas consideradas**: nenhuma — reaproveitamento direto, sem alternativa razoável.
