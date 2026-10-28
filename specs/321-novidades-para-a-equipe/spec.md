# 321 — Novidades para a equipe: o que mudou vira mensagem por grupo de WhatsApp

**Branch**: `321-novidades-para-a-equipe` · **Created**: 2026-10-28 · **Status**: PRONTA, aguardando o
dono (merge só a pedido) · **Migration**: nenhuma · **Nível**: 2 (harness e documentação; um script
sem efeito no sistema em produção)

## O pedido

O dono (28/10): "Todas mudanças que faço não passam para o time pois eles muitas vezes não sabem que
mudou. Eu queria estabelecer uma forma on demand de enviar para os respectivos grupos no WhatsApp as
mudanças pertinentes às suas funções. É possível estabelecer uma checagem por push e um disparo com
texto explicativo por WhatsApp de forma automatizada? [...] Se isso não for possível, pode só fazer o
texto e dizer para quem enviar que eu faço manualmente."

## O que muda

Nada no sistema que a equipe usa. Entra um fluxo de trabalho no repositório:

- **`scripts/novidades.py`** (só stdlib, só leitura do git e dos docs): lista o que entrou na `main`
  (`--first-parent`) desde o marco `docs/novidades/ULTIMO_AVISO`; para cada mudança acha a spec, a
  seção "O pedido", a data de produção na entrada do `docs/03` e o sinal de "desligada/interruptor"
  (⚠ = não anunciar); dá pistas de grupo pelos arquivos tocados. `--rascunho` grava
  `docs/novidades/<hoje>.md` com o esqueleto por grupo e o material; `--marcar` grava a `main` atual
  como avisada; `--hook`/`--contar` servem ao gancho. `docs(...)` e `chore(...)` ficam de fora.
- **`scripts/hooks/pre-push`** (cópia em `.git/hooks/pre-push`): ao empurrar a `main`, imprime
  quantas mudanças ainda não foram contadas à equipe e lembra a skill. Nunca bloqueia.
- **Skill `manto-novidades`**: o passo a passo (listar → rascunho → ler a entrada do `docs/03` →
  confirmar o nome do botão na tela → escrever por grupo → dono aprova → enviar → `--marcar`), as
  regras de texto (constituição §XV, "mensagem de WhatsApp que a equipe copia"), a tabela grupo ×
  papel e o envio assistido pelo Claude in Chrome (um OK por grupo; não existe envio sem ninguém
  olhando — a API oficial do WhatsApp não cobre grupos de forma aberta e automação por cima do
  WhatsApp Web arrisca o número).
- **Primeira rodada**: `docs/novidades/2026-10-28.md` cobre as 21 mudanças publicadas de 14/10 a
  27/10 (298b → 320), com uma mensagem pronta por grupo. 310, 317 e 318 ficam guardadas (em
  produção, mas desligadas até o dono configurar).
- Ponteiros: `DEVELOPMENT.md` §Publicar (passo 8), skill `manto-deploy` (depois de "está em
  produção"), `CLAUDE.md` §9.

## Decisões

- O marco é um arquivo versionado, não uma tag: aparece no `git log`, sobrevive a clone e se lê sem
  git. Só a última linha vale.
- O script não escreve o texto: junta material. O texto é da skill, lido do `docs/03` (a entrada,
  não a spec inteira) e conferido contra a tela.
- A data de produção vem do `docs/03`, não do `Status` da spec, que fica em "Rascunho" na maioria
  das features (template do Spec Kit).
- O envio é assistido e por grupo. Envio sem supervisão foi descartado: sem API para grupos e com
  risco de banimento do número.

## Verificação

`specs/321-novidades-para-a-equipe/verify_321.py` (não usa o `manto_local`: só git e arquivos).
Roda o script sobre a faixa fixa `0feb4255..6f706fa6` e confere: 21 mudanças, a 320 primeiro com
spec e data de produção, a 317/318/310 com ⚠, `docs`/`chore` fora, `--contar` e `--hook` (sai 0 e
avisa no stderr), `--rascunho` cria o arquivo com as sete seções e o material, `--marcar` grava e
`ler_marco` lê de volta (em arquivo temporário). Resultado na entrega: 9/9.

## Fora de escopo

Envio automático sem supervisão; tela "Novidades" dentro do sistema (sino por papel); aviso por
e-mail; texto por artista. Mudanças anteriores a 14/10/2026 (marco inicial `0feb4255`).
