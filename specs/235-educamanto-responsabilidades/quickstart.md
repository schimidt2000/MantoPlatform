# Quickstart de validação — Feature 235: EducaManto por responsabilidades

Roteiro para provar a feature de ponta a ponta. **Todo teste roda contra o espelho `manto_local`** (nunca o SQLite de `instance/`): suba com `.\scripts\db\run-local.ps1` e faça um refresh do dump antes de validar a migração.

## Pré-requisitos

1. Branch `235-educamanto-responsabilidades`, dependências instaladas, `manto_local` atualizado.
2. Migração aplicada (`flask db upgrade`) — ver validação da migração abaixo.
3. Frontend: `npx tsc --noEmit` limpo em `frontend/apps/internal`; app aberto pelo dev server.

## 1. Migração (uma vez, logo após `db upgrade`)

- `educamanto_musicals` tem **7 linhas** (ids 1, 11, 15, 18, 23, 26, 29), nomes sem " - Master".
- Nenhuma linha Intermediário/Econômica/"Cópia de" sobrou; `educamanto_musical_items` sem itens "Som", "Catering apresentação" ou "Transporte".
- `custo_som_*` de Uma Aventura Animal = 4000/4000/3500/3500; `custo_alimentacao_*` = 55/73; `num_ensaios` = 2 em todos.
- **Paridade numérica**: para cada musical, calcular 1 dia/1 sessão com tudo "por conta da Manto", ensemble 0, sem transporte/acréscimo, e comparar com o valor do pacote Master correspondente **antes** da migração ajustado pelas mudanças conhecidas (caminhão 600→800, ensaios ×2, técnicos/iluminação/cenário provisórios). Ex. Uma Aventura Animal (antes: sem NF 14.700 / com NF 17.400): conferir que a diferença é exatamente a soma dessas parcelas novas.

## 2. Matriz técnica e responsabilidades (SC-002)

Na calculadora, com Uma Aventura Animal, 1 dia/1 sessão, validar as 4 combinações:

| som | iluminação | técnicos exibidos | headcount (ensemble 0) |
|---|---|---|---|
| Manto | Manto | sonoplasta, téc. som, téc. iluminação | 14 |
| Manto | Contratante | sonoplasta, téc. som | 13 |
| Contratante | Manto | sonoplasta, téc. iluminação | 13 |
| Contratante | Contratante | sonoplasta | 12 |

Conferir a cada troca: valor final muda na direção certa (bloco sai → valor cai), tooltip visível em cada bloco, e o custo de alimentação some quando "contratante".

## 3. PDF (SC-003)

Gerar com d1=1, d2=0 e conferir na página:

- [ ] Linha "dias com 2 sessões" **ausente** (zero oculto).
- [ ] Por responsabilidade: texto "o que levaremos" (Manto) ou "mínimo exigido" (contratante).
- [ ] Quantidades: "9 personagens, 2 de produção, N técnicos" conforme o caso.
- [ ] Avisos: palco mínimo 5 m × 4 m; camarim (cadeiras = headcount, espelho, banheiro, água); som suficiente para área X/Y; visita técnica/chamada de vídeo para local aberto.
- [ ] Valores: SEM NF, COM NF e **à vista com 5%** (= total × 0,95, 2 casas).
- [ ] Observação do vendedor formatada (quando preenchida).
- [ ] Textos antigos de nível (Master/Intermediário/Econômica, "O QUE ESTÁ INCLUSO" por nível) **não aparecem**.

## 4. Multi-páginas (US3)

Criar página 2 (copiando a 1), trocar musical na página 2, editar a página 1 de novo, gerar: PDF com 2 páginas, cada uma com sua configuração; remover páginas até restar 1 (bloqueia a remoção da última).

## 5. Transporte (FR-012/013)

- Dentro de SP (padrão): transporte = R$ 800, km ignorado.
- Fora de SP + km 100 + headcount 13 + 2 dias, com tarifas default (5,5 / 4,5 / divisor 3): viagem = 200×(5,5+4,5) + 13×200÷3 = 2.000 + 866,67 = **R$ 2.866,67**; total = × 2 dias = **R$ 5.733,34**; caminhão ausente.
- Fora de SP sem km: transporte 0 e caminhão ausente; geração avisa km obrigatório.

## 6. Contratação Manto (US4, SC-007)

Adicionar contratação com 1 ator + coordenador, durações 1h e 2h: aparecem 2 totais combinados; conferir `combinado(1h) = ceil100((liquido_edu + total_1h_manto) )` sem NF e `ceil100(soma ÷ 0,84)` com NF; memória da parte Manto visível **só** para superadmin; sem contratação, nada aparece.

## 7. RBAC (SC-005)

Logar (ou "ver como") REVENDEDOR_EDUCAMANTO e COMERCIAL: a tela mostra só valores finais/à vista/transporte/acréscimo próprio; a resposta crua de `POST /api/educamanto/calcular` (aba Network) **não contém** `breakdown`, `item_rows`, `raw_cost` ou memória. Superadmin vê tudo.

## 8. Histórico e retrocompatibilidade (SC-006)

- Abrir um orçamento **antigo** (v1) no histórico: "Ver" mostra os dados congelados, "Baixar PDF" reproduz o PDF idêntico ao original (formato antigo).
- "Recalcular" de um v1 de pacote Econômica: abre a calculadora nova no musical certo, com alimentação/iluminação pré-marcadas "contratante" e aviso do mapeamento.
- Gerar um orçamento novo e conferir `snapshot.version == 2` e valores idênticos aos da tela.

## 9. Legado desligado (SC-008)

Acessar as URLs Jinja antigas (`/educamanto` view, `/educamanto/packages`, `/educamanto/history`): todas respondem redirect para o React; `templates/educamanto/` não existe mais no repositório.

## 10. Regressão de tipos e domínio vizinho

- `npx tsc --noEmit` limpo em `apps/internal`.
- Calculadora de orçamento de eventos (`/orcamento`) continua funcionando idêntica (nenhum arquivo de `app/orcamento` alterado; componentes extraídos renderizam igual na página original).
