# 342b — Formulário com nota e sem nota

**Branch**: `342b-formulario-com-e-sem-nota` · **Created**: 2026-11-27 · **Status**: Pronta · **Migration**: nenhuma

Nível 2 (hotfix da 342). Domínio: formulários públicos (com a lista de links da conversa, que só
reflete os links novos).

## O pedido

O dono (27/11): a caixa "Preciso de nota fiscal" que a 342 pôs nos formulários está gerando
confusão. A cliente que combinou sem nota marca a caixa, preenche os dados, e o valor muda. "Eu preciso
de 2 versões: um formulário com nota, outro sem nota. A pessoa não escolhe; ela só preenche o que foi
enviado para ela." Vale para o pré-contrato e para o corporativo.

## O que muda

- **Quatro links**: `/f/pre-contrato/com-nota`, `/f/pre-contrato/sem-nota`, `/f/corporativo/com-nota`,
  `/f/corporativo/sem-nota`. Mesma estrutura de campos (editor único por formulário). Nada novo no
  banco: a versão vem no link.
- **Com nota**: a caixa não aparece; as perguntas da nota já aparecem e são obrigatórias, e o documento
  e o e-mail acompanham o que a cliente digita acima enquanto ela não os muda.
- **Sem nota**: a seção "Nota fiscal" não aparece.
- **Servidor**: o envio leva `versao_nota`; o `POST /api/formularios/<tipo>` fixa a resposta de
  "Preciso de nota fiscal" (`Sim` / `Não`) pela versão, seja o que for que a tela mande. Versão
  desconhecida = 404. A mensagem do WhatsApp mostra "Preciso de nota fiscal: Sim/Não", e a vendedora
  vê de qual link veio.
- **Onde a equipe copia o link**: a tela Formulários mostra os dois links de cada formulário; "Enviar
  formulário" da conversa oferece as quatro versões.
- **Link antigo** (`/f/pre-contrato`, `/f/corporativo`): segue no ar como era (a cliente marca a caixa),
  porque está impresso em bio e integrações. Não é mais copiado de lugar nenhum do sistema.

## Verificação

`verify_342b.py` (espelho `manto_342b`, dump de 26/11 02h): 6/6. Com o endpoint antigo, 4 cenários
falham (1 a 4). Regressão: `verify_342` 19/19, `verify_333` 15/15 (cenário 9 atualizado para as
quatro versões). `npm run typecheck` limpo; telas abertas no celular (as quatro versões, o link antigo,
a tela Formulários) e o envio conferido na tela (com nota manda `versao_nota` e os dados; sem nota, só
a versão).

## Fora de escopo

- Tirar a caixa do link antigo ou redirecioná-lo para uma das versões (pergunta ao dono).
- Formulário separado no editor por versão.
