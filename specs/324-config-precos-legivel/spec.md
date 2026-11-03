# 324 — Configuração de Preços legível

**Branch**: `324-config-precos-legivel` (da `main`) · **Created**: 2026-10-30 · **Status**: Pronta, aguardando merge ·
**Migration**: não · **Nível**: 2 (correção de tela, um domínio) — constituição, Princípio VI

## O pedido

> "Preciso que revise a página de configuração de gastos, porque ela está toda meio mal formatada e mal
> escrita. E está difícil de entender o que é o quê. Então, é para você mudar apenas a visualização
> dela. E uma pergunta, essa página é visível para as pessoas de casting?"

A página é a **Configuração de Preços** (`/orcamento/configuracoes`, "Config. Preços" no menu) — o dono
confirmou ao escolher entre as telas candidatas. Resposta à pergunta: **não**. O item do menu só aparece
para `SUPERADMIN` (`frontend/apps/internal/src/lib/navigation.tsx`, `config-precos`) e os endpoints
`GET/POST /api/orcamento/settings` e `/api/orcamento/settings/especiais*` passam por
`_require_superadmin()` (`app/api/orcamento_read.py`, `app/api/orcamento_write.py`). Casting que digitar o
endereço vê só "Não foi possível carregar a configuração de preços" (403 da API).

## O que muda

Só a tela; nenhum endpoint, chave salva, regra de cálculo ou migration.

- **Estrutura**: oito seções com título e uma frase que diz o que cada valor faz — Markup; Cachês do
  elenco (atores e bonecos, cantores, coordenador, personagens especiais); Técnico, maquiador e brinde;
  Transporte (veículos e adicionais da equipe); Acréscimos; Datas especiais; Produtos de tabela;
  EducaManto (som e iluminação, caminhão de cenografia). Antes eram onze cartões soltos numa grade de duas
  colunas, sem ordem de assunto.
- **Cartão "Como a calculadora monta o preço"** no topo: cachês → × markup → + produtos de tabela →
  + serviços (brinde, noturno, técnico, maquiador) → + transporte e acréscimos.
- **Atalhos** para cada seção e **"Salvar configurações" numa barra fixa** no rodapé (antes ficava no fim
  de uma página de várias telas).
- **Rótulos que eram chave técnica**: `boneco|true|false` → "Boneco · Com show · sem maquiagem";
  `van_com_carretinha`, `afsp_divisor`, `ashow_min_km`… → "Van com carretinha (R$/km)", "Adicional fora de
  SP — divisor" com exemplo, "Adicional de show — a partir de (km)"; variantes do especial `false/true`,
  `none/show/cantor` → "Sem show", "Com show", "Cantando".
- **Ações na linha**: "Remover" do personagem especial e "Tirar" do cachê próprio da data especial ficam
  na linha da tabela, com `ConfirmDialog` (Princípio V) no lugar do `window.confirm`. A remoção do especial
  só some da tela depois que o servidor confirma.
- **Campos em reais** (R$/km, som e iluminação, caminhão) passam a `MoneyInput`; divisores e km seguem
  numéricos.
- `PriceTable` ganhou `hint`, `key` e `acao` (coluna extra opcional). Datas especiais e Produtos de tabela:
  textos revistos (Princípio XV), `htmlFor` nos rótulos, vagas com botões de tipo que quebram linha no
  celular (antes estouravam 30px a 320px).

## Verificação

Sem `verify_324.py`: nada no backend muda. Conferido no Browser pane contra o `manto_local`, como
Superadmin:

- `npm run typecheck` limpo nas três SPAs.
- "Salvar configurações" sem alterar nada: `GET /api/orcamento/settings` antes e depois idênticos.
- Alterar "Adicional de show — a partir de (km)" para 600 e o divisor fora de SP para 3,5 → salvos em
  `transporte.ashow_min_km` e `transporte.afsp_divisor`; voltar a 500 e 3 → tabela igual à inicial.
- "Remover" do Bailarino abre o diálogo; "Cancelar" fecha sem chamar a API (Bailarino segue no banco).
- Sem rolagem horizontal a 320, 375 e 1440px; nenhuma tabela com rolagem interna a 1440px.

## Fora de escopo

- **Achado, não corrigido** (comportamento, não visual): "Adicionar personagem" grava na hora e substitui
  a tabela da tela pela do servidor, descartando alterações não salvas. A tela agora avisa ("salve antes
  as alterações pendentes"); corrigir o comportamento é outra correção.
- Os valores em si (ex.: van com carretinha 6,30 e sem carretinha 5,50 no banco, invertidos em relação aos
  defaults do código) não foram tocados.
