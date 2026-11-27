# Feature 364 — Gravar no catálogo o que a conferência de personagens aprovou

**Branch**: `364-gravar-conferido-no-catalogo` (da `main`) · **Created**: 2026-11-27 · **Status**: Pronta na branch (verify 10/10; regressão da 360 18/18) ·
**Migration**: `f364a1b2c3d4` (aditiva — duas colunas novas nas tabelas da conferência) · **Nível**: 1
(feature: migration, endpoint novo, escreve no catálogo público) — constituição, Princípio VI

**Input**: pedido do dono: "a Gabriela terminou de fazer lá, só que ela colocou várias coisas nas
observações. […] você vai reorganizar aquilo e vai enfim montar o catálogo da forma como eu quero" e, às
duas perguntas feitas antes do plano: "Pode gravar direto, por favor. Entra sem ficha mesmo. Quando tiver
evento com eles ou quando estivermos com pouco trabalho, peço para o pessoal fazer as fichas."

## O pedido, nas palavras do dono *(obrigatório)*

A feature 360 pôs a conferência de personagens dentro do sistema. A Maria Gabriella conferiu os 352 itens
da fila (terminou em 26/11): 904 personagens a criar em 224 temas e duplas, 199 deles acrescentados à mão,
37 nomes corrigidos, 39 fichas trocadas, 54 tipos corrigidos e 95 avulsos (25 com ficha). Nada disso está
no catálogo: a 360 só registra decisões. Esta feature grava.

Decisões do dono (27/11): **grava direto**, sem prévia nem aprovação por lote; **personagem sem ficha entra
sem ficha** (553 dos 904) e avulso sem ficha fica como está; as fichas serão feitas depois, pelo Figurino.

As observações da Gabriella (35) são instruções para a gravação: 31 dizem qual pessoa da galeria é o
personagem que ficou sem foto; uma diz que a foto proposta está errada (Spider-Gwen); uma pede que
"Árvores de Natal (Pernas de Pau)" vire vários personagens, menos as bolas; as demais são comentário.

## Clarifications

### Session 2026-11-27

- Q: A gravação passa por prévia e aprovação do dono? → A: Não. Grava direto o que foi conferido.
- Q: Personagem sem ficha de figurino entra no catálogo? → A: Entra sem ficha.
- Q: A feature cria fichas de figurino? → A: Não. Ficha é trabalho do Figurino, depois.
- Q: O que acontece com avulso sem ficha e com genérico? → A: Nada muda no catálogo; ficam marcados como
  gravados e continuam pendentes de ficha (decidido por default; o dono pode rever).
- Q: Filtro "Sem foto" e busca por personagem entram agora? → A: Não. O gerenciador já tem a visão
  "Personagens"; o filtro fica como dívida (decidido por default).

## Cenários e Verificação *(obrigatório)*

### História 1 — O conferido vira elenco no catálogo (Prioridade: P1)

O Superadmin abre a fila da conferência e aciona "Gravar no catálogo". Cada tema e cada dupla conferidos
ganham o elenco decidido: um personagem por linha "Criar", com o nome decidido, a ficha decidida (ou
nenhuma) e a foto recortada de verdade da galeria (ou sem foto, quando foi marcado "Criar sem foto").
Cada avulso com ficha passa a usar a ficha. O item gravado sai da fila sozinho, porque passou a ter elenco
ou ficha.

**Por que esta prioridade**: é o que o dono pediu; sem isso o trabalho da conferência não chega à vitrine.

**Verificação**: cenários 1 a 5 do `verify_364.py`.

**Cenários de aceite**:

1. **Dado** um tema conferido com seis personagens "Criar" (um deles "sem foto"), **Quando** a gravação
   roda, **Então** o item passa a ter seis personagens no elenco, na ordem da conferência, cinco com foto
   recortada e um sem foto, e deixa a fila.
2. **Dado** um avulso conferido com ficha, **Quando** a gravação roda, **Então** o item passa a usar a
   ficha e deixa a fila.
3. **Dado** um avulso sem ficha ou um genérico, **Quando** a gravação roda, **Então** nada muda no item,
   e ele fica marcado como gravado.
4. **Dado** um item ainda não conferido, **Quando** a gravação roda, **Então** ele não é tocado.

---

### História 2 — Gravar de novo não duplica (Prioridade: P1)

A gravação anda em lotes e pode ser interrompida e repetida. Personagem já gravado não é criado de novo;
item já gravado é pulado. Um arquivo de foto que não está no disco não derruba o lote: o personagem nasce
sem foto.

**Verificação**: cenários 6 e 7 do `verify_364.py`.

**Cenários de aceite**:

1. **Dado** um item já gravado, **Quando** a gravação roda de novo, **Então** nenhum personagem é criado.
2. **Dado** um personagem cuja foto não existe no disco, **Quando** a gravação roda, **Então** ele é criado
   sem foto e o lote segue.

---

### História 3 — As observações da conferência são aplicadas (Prioridade: P2)

Antes de gravar, o sistema aplica os ajustes que saíram da leitura das observações: a foto e o recorte dos
personagens que a Gabriella apontou, "sem foto" onde ela disse que a foto estava errada, e o elenco de
"Árvores de Natal (Pernas de Pau)".

**Verificação**: cenário 8 do `verify_364.py`.

**Cenários de aceite**:

1. **Dado** um personagem acrescentado à mão com ajuste de foto, **Quando** os ajustes são aplicados,
   **Então** ele passa a ter foto e recorte e é gravado com foto.
2. **Dado** um ajuste que cita personagem ou foto que não existe mais, **Quando** os ajustes são aplicados,
   **Então** ele é ignorado e contado, sem erro.

### Casos de borda

- **Dois cliques ao mesmo tempo**: a gravação é serializada; nenhum personagem nasce em dobro.
- **Nome repetido no mesmo tema** ("Noelani" em dois temas, dois "Guerreiro"): cada um ganha endereço
  próprio; os dois são criados.
- **Item que saiu da fila depois de conferido** (alguém cadastrou o elenco à mão): é pulado, não ganha
  segundo elenco.
- **Recorte inválido ou foto que saiu da galeria**: personagem sem foto.
- **Falha no meio de um item**: o item inteiro é desfeito e aparece na lista de falhas; os outros seguem.

## Requisitos *(obrigatório)*

### Requisitos funcionais

- **FR-001**: A gravação DEVE criar, para cada tema ou dupla conferido que ainda está na fila, um
  personagem do catálogo por personagem com decisão "criar", com o nome decidido, a ficha decidida e na
  ordem da conferência.
- **FR-002**: A foto do personagem DEVE ser o recorte real da foto da galeria (arquivo novo), salvo quando
  marcado "criar sem foto", quando o recorte é inválido ou quando o arquivo não existe: nesses casos o
  personagem nasce sem foto.
- **FR-003**: Para avulso conferido com ficha, a gravação DEVE ligar a ficha ao item. Avulso sem ficha e
  genérico não mudam.
- **FR-004**: A gravação DEVE registrar em cada item quando foi gravado e, em cada personagem, qual
  personagem do catálogo ele gerou. Repetir a gravação não cria nada em dobro.
- **FR-005**: A gravação DEVE andar em lotes pequenos, com o resumo do que foi feito, do que falta e das
  falhas, e a tela DEVE mostrar o andamento até terminar.
- **FR-006**: Item não conferido, item fora da fila e item já gravado NÃO são tocados.
- **FR-007**: Antes de gravar, os ajustes das observações (arquivo versionado) DEVEM ser aplicados, de
  forma idempotente; ajuste sem alvo é ignorado e contado.
- **FR-008**: Só o Superadmin aciona a gravação.
- **FR-009**: A gravação NÃO cria ficha de figurino, não apaga personagem existente e não altera item que
  já tinha elenco ou ficha.

### Entidades

- **Conferência do item** ganha `gravado_em`. **Personagem proposto** ganha o vínculo com o personagem do
  catálogo que gerou. Migration à mão.
- **Ajustes**: arquivo `app/admin/dados/ajustes_conferencia.json`, versionado.

### RBAC

- `GET /api/admin/catalogo/conferencia/gravacao` — papéis: SUPERADMIN (o que falta gravar)
- `POST /api/admin/catalogo/conferencia/gravar` — papéis: SUPERADMIN (um lote)

## Verificação (`verify_364.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/364-gravar-conferido-no-catalogo/verify_364.py`, contra o espelho `manto_364` (dump de
produção de 26/11 02h, com a conferência parcial; exceção ao `manto_local` registrada no plano). As fotos
dos itens de teste são copiadas da pasta local da leitura para a pasta de mídia da worktree.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | Resumo do que falta gravar | bate com a contagem por SQL independente | não |
| 2 | Gravar um tema conferido | personagens criados com nome, ficha e ordem decididos; "não criar" fica de fora | não |
| 3 | Foto recortada | arquivo novo em disco, com a proporção do recorte; "sem foto" nasce sem foto | não |
| 4 | Avulso com ficha, avulso sem ficha e genérico | o primeiro liga a ficha; os outros só ficam marcados | não |
| 5 | Item gravado sai da fila; não conferido fica intacto | regra da fila e FR-006 | não |
| 6 | Gravar de novo | zero personagens novos | não |
| 7 | Foto que não existe no disco | personagem criado sem foto, lote segue | não |
| 8 | Ajustes das observações | foto aplicada, "sem foto" aplicado, elenco novo criado, ajuste sem alvo ignorado | não |
| 9 | Comercial, Figurino e sem login | 403 e 401, nada gravado | **sim** |
| 10 | Limpeza | personagens, arquivos e marcas da gravação desfeitos; catálogo igual ao início | — |

Conferência de tela: `/admin/catalogo/conferencia` com o bloco "Gravar no catálogo", a 390 px.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Depois da gravação em produção, os temas e duplas conferidos aparecem com elenco no
  gerenciador e na vitrine, e a fila fica só com o que não tem o que gravar.
- **SC-002**: Nenhum personagem em dobro, mesmo repetindo a gravação.
- **SC-003**: Nenhuma ficha de figurino criada e nenhum item que já tinha elenco alterado.

## Fora de escopo

- Criar fichas de figurino (inclusive as pedidas em "Árvores de Natal").
- Filtro "Sem foto" para o marketing e mudanças na busca.
- Desfazer a gravação pela tela.
- Página própria e tema de grupo.

## Docs a atualizar

`docs/01` (schema, §3.10, §4.3), `docs/02` (fila), `docs/03` (entrada), `docs/04` (catálogo), `docs/05`
(baixa da 244; dívida do filtro "Sem foto").

## Premissas

- A regra "nada se grava no catálogo sem conferência" está atendida: a conferência foi feita e o dono
  mandou gravar direto.
- Avulso sem ficha e genérico continuam pendentes de ficha; a fila da conferência os mostra como
  conferidos.
- Onde a leitura das observações não achou a pessoa com segurança, o personagem nasce sem foto.
