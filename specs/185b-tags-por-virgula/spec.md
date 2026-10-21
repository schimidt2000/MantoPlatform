# 185b — As tags do catálogo se separam pela vírgula

**Branch**: `185b-tags-por-virgula` · **Created**: 2026-10-21 · **Status**: PRONTA na branch (não
mergeada) · **Migration**: nenhuma

## O pedido

O dono: "as tags quando classifico algo no catálogo ficam tudo junto, não fica separado por
vírgula".

O campo Tags do produto (`/admin/catalogo/:id`, `ChipInput` da 185) só separava quando o
navegador avisava a **tecla** ",":

- no celular, o teclado virtual manda `key: "Unidentified"`: a vírgula entrava no texto e
  "bruxa, fada" virava um chip só;
- colar "bruxa, fada, princesa" (ou uma lista em linhas) também virava um chip só, e o `<input>`
  ainda apagava as quebras de linha;
- o texto digitado sem Enter **sumia** ao salvar: o formulário mandava só os chips.

O servidor não tem culpa: `catalog_ops` já parte a string por vírgula ao gravar.

## O que muda

- `ChipInput` trata o separador no **texto**: a cada mudança, tudo antes da última vírgula vira
  chip e o resto continua no campo. Separam vírgula, ponto e vírgula e quebra de linha.
- Colar: o `paste` é lido antes do `<input>` apagar as quebras de linha; cada pedaço vira chip.
- O texto que ficou sem Enter não vira chip no blur — o chip novo pode quebrar linha e empurrar o
  botão Salvar no meio do clique, e o clique se perde. Em vez disso, o `ChipInput` expõe
  `commitPending()` (ref) e o `handleSubmit` do formulário o chama: o pendente vira chip e vai no
  salvamento.
- Tecla Enter/",", Backspace, sugestões e remoção de chip continuam como estavam.

## Verificação

Só frontend, sem regra no servidor: a prova é a tela, não um `verify_185b.py`. Harness temporário
(o `ChipInput` real com um Salvar que chama `commitPending`, como o formulário), no Browser pane:

1. Teclado de verdade: "bruxa, fada madrinha,princesa, castelo encantado" → 3 chips na hora e
   "castelo encantado" no campo.
2. Clique real em Salvar com o texto pendente → o clique chega e salva os 5 (o pendente incluso).
3. Celular (texto com vírgula sem tecla ","): "dragao," → chip "dragao".
4. Colar "ogro; elfo\nanão" → chips "ogro" e "elfo", "anão" no campo.
5. Clique numa sugestão → vira chip a sugestão, não o pedaço digitado.

Antes da correção, os casos 3 e 4 davam um chip só e o pendente do 2 se perdia. Mais o typecheck do
`internal`.

## Fora de escopo

- Tags antigas gravadas juntas não existem: o servidor sempre partiu por vírgula ao salvar.
- Outras telas não usam o `ChipInput`.
