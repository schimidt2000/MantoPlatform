# Quickstart — Feature 106

## Rodar

```powershell
.\scripts\db\run-local.ps1   # app contra manto_local — sem migration nesta feature
```

## Roteiro de verificação

### US1 — Portal no celular (DevTools, viewports 320 / 360 / 390 / 430)

Logar no portal como um talento com: convite pendente, evento futuro com ensaio+materiais,
histórico com valores e avaliação pendente (usar dados reais da cópia local).

1. **Home**: sem scroll horizontal; header empilhado; convite com botões full-width;
   materiais de ensaio com indent pequeno; valores em padrão BR ("R$ 4.000", nunca "4,000");
   histórico recente sem estourar a largura (badges quebram linha).
2. **Histórico**: 3 cards de resumo legíveis; valores em BR; linhas com valor/badge alinhados.
3. **Perfil**: pares de campos empilhados em ≤480px; medidas em 2 colunas; × de remover
   foto/link com toque confortável; sem cores "cinza soltas" (usar paleta).
4. **Avaliar evento** (`/portal/events/<id>/rate` e `/rate/detail`): estrelas confortáveis
   ao toque; enviar avaliação funciona.
5. **Figurino, Termo, Login, Primeiro acesso, Esqueci/Trocar senha**: renderizam sem scroll
   horizontal; botões ≥44px.
6. **Fluxos sem regressão**: aceitar/recusar convite, salvar perfil, avaliar, abrir figurino.

### US2 — Validação do /cadastro (viewport 390×844)

1. Abrir `/cadastro`, preencher só metade e enviar → a tela **rola até o primeiro campo
   faltante**, campo com **borda vermelha + tremida**, mensagem "Preencha este campo."
   abaixo; **sem alert()**; todos os demais campos faltantes também destacados.
2. Preencher o campo destacado → destaque some na hora.
3. Deixar idiomas OU habilidades sem seleção → grupo destacado com a mensagem própria e
   scroll até ele.
4. Marcar "Sou estrangeiro(a)" (CPF desabilitado) → enviar não reclama do CPF nem rola até
   campo invisível.
5. E-mail malformado → "Informe um e-mail válido." no campo.
6. Sem anexos obrigatórios → mensagem "Anexe o arquivo." nos campos de arquivo.
7. Corrigir tudo e enviar → botão trava em "Enviando…" e o cadastro completa (fluxo atual).
8. Conferir que os dados digitados nunca somem numa tentativa bloqueada.

## Portões

```powershell
ruff check app/           # nada de Python muda, mas confere
```

Verificação automatizada (test client, requests fora de app_context): renderização 200 das
telas do portal e do /cadastro; presença de `novalidate`, `.field-errmsg`/`.field-invalid`
no form; `R$` com padrão BR no HTML da home/histórico (regex proíbe `\d,\d{3}`).
