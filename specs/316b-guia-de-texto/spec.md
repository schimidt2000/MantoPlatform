# 316b — O guia de texto da 316 entra na constituição (Princípio XV)

**Branch**: `316b-guia-de-texto` · **Created**: 2026-10-23 · **Status**: pronta na branch, aguardando o
merge a pedido do dono · **Migration**: nenhuma

## O pedido

O dono (23/10): "O Claude sempre, quando vai fazer algo, deve olhar a constitution ou algum arquivo do
tipo para escrever os textos, correto? Preciso que altere nesse arquivo as diretrizes para bons textos
escritos, seguindo o padrão do que fizemos."

O guia de tom e o glossário da 316 ficaram só em `specs/316-tom-dos-textos/spec.md`. Nenhuma sessão
abre essa spec por conta própria. O `CLAUDE.md` é lido em toda sessão e aponta para a constituição por
número de princípio, e a constituição é o que o `/speckit-plan` e o `/speckit-checklist` cobram. Sem
isso, o próximo texto novo volta a sair "largado".

## O que muda

- **Constituição 3.0.0 → 3.1.0** (MINOR, Governança §Versionamento):
  - **Princípio XV, "Texto que o usuário lê: tom por superfície e vocabulário único"**. Traz:
    - o alcance: tela, e-mail, PDF, mensagem copiada e erro da API;
    - a regra de ler a tela inteira antes de escrever;
    - o tom de cada superfície: interno operacional, público lúdico e claro, portal cordial,
      WhatsApp copiado em tom de conversa;
    - o glossário da 316 com o que ela decidiu: Inserir/Ver/Excluir comprovante, Situação,
      Excluir × Remover, verbos fixos, estado vazio, grafia, caixa, contagem e vocabulário de
      domínio;
    - o que um ajuste de texto não toca.
  - **Portão novo**: "texto revisado pelo Princípio XV".
  - **Redação do V**: "Salvando…", "excluir, remover" e o ponteiro para o XV.
  - Sync Impact Report e changelog atualizados.
- **`CLAUDE.md` §5**: aponta o §XV e manda lê-lo antes de escrever qualquer texto que o usuário lê.
- **`docs/00` §5**: ponteiro para o XV nas convenções obrigatórias.
- **Templates do Spec Kit**:
  - `plan-template`: linha XV no Constitution Check;
  - `checklist-template`: portão CHK010; os exemplos foram renumerados;
  - `tasks-template`: tarefa de polimento.
- **`specs/316-tom-dos-textos/spec.md`**: ganha uma nota de que o guia vigente agora é o §XV.

## Verificação

Só documentação e harness: não há `verify_316b.py`. O XV foi conferido contra o que a 316 decidiu de
fato: os 505 textos, as 3 propostas rejeitadas (o "Oi" do WhatsApp, o ponto antes do ✓, o cabeçalho do
CSV) e as dívidas 145–147.

## Fora de escopo

- Decidir a caixa do menu lateral e dos títulos de módulo (dívida 146). O XV manda seguir o vizinho até
  a decisão.
- Revisar de novo os textos já entregues.
