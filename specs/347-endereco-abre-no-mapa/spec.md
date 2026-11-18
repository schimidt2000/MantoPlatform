# Feature 347 — Tocar no endereço do evento e escolher o app de mapas

**Branch**: `347-endereco-abre-no-mapa` (da `main`) · **Created**: 2026-11-17 · **Status**: Rascunho ·
**Migration**: nenhuma · **Nível**: 1 (feature) — toca dois domínios (Agenda no app interno e Portal
do Artista), constituição, Princípio VI

**Input**: pedido do dono: "Endereço do evento abre no app de mapas. Na página do evento do app
interno e nos cards de evento do Portal do Artista, o endereço vira um elemento tocável. Ao tocar,
aparece uma escolha de app: Google Maps, Apple Mapas e Waze."

## O pedido, nas palavras do dono *(obrigatório)*

> "Preciso fazer uma melhoria na página do evento. O endereço deve ser clicável e aparecer com qual
> app você quer abrir aquele endereço: Google Maps, Apple Mapas, Waze. […] Tanto na página do app
> quanto do portal."

Hoje o endereço do evento é texto puro nas duas superfícies. Para chegar ao local, a pessoa
seleciona o texto no celular, copia, abre o app de mapas e cola. Com o sistema instalado na Tela de
Início do iPhone, selecionar texto num card é difícil, e é exatamente no caminho para o evento que a
equipe e o artista precisam do endereço.

## Cenários e Verificação *(obrigatório)*

### História 1 — Equipe abre o endereço do evento no app de mapas (Prioridade: P1)

Na página do evento do app interno, quem abre o evento (Comercial, Casting, Figurino, Ensaio,
Superadmin…) toca no endereço, no cabeçalho ou no painel "Dados do evento", e escolhe entre Google
Maps, Apple Mapas e Waze. O app escolhido abre já no local do evento.

**Por que esta prioridade**: é a tela que a equipe usa no dia do evento, no celular, e o pedido
começa por ela.

**Verificação**: conferência de tela 1 e 2 (abaixo) — app interno no Browser pane contra o
`manto_local`, em 390px e em tela larga.

**Cenários de aceite**:

1. **Dado** um evento com endereço, **Quando** a pessoa toca no endereço do cabeçalho, **Então**
   abre a escolha "Abrir endereço" com o endereço escrito e as três opções: Google Maps, Apple
   Mapas e Waze.
2. **Dado** a escolha aberta, **Quando** a pessoa toca em "Waze", **Então** o Waze abre (ou o site
   do Waze, sem o app) mostrando aquele endereço, a escolha se fecha e a página do evento continua
   onde estava.
3. **Dado** o painel "Dados do evento" em modo de leitura, **Quando** a pessoa toca no valor da
   linha "Local", **Então** acontece o mesmo que no cabeçalho.
4. **Dado** a escolha aberta, **Quando** a pessoa toca fora, no "Fechar" ou aperta Esc, **Então**
   a escolha se fecha sem abrir nenhum app.

---

### História 2 — Artista abre o endereço do evento pelo portal (Prioridade: P1)

No Portal do Artista, o artista vê o endereço no card do evento em "Próximos eventos" e no card do
convite em "Convites", toca nele e escolhe o app de mapas.

**Por que esta prioridade**: o artista vai sozinho ao local; o portal é usado quase só no celular
(Princípio X).

**Verificação**: conferência de tela 3 e 4 — portal no Browser pane em 375×812, logado como um
talento do `manto_local` com evento futuro e endereço.

**Cenários de aceite**:

1. **Dado** um evento futuro com endereço em "Próximos eventos", **Quando** o artista toca no
   endereço, **Então** abre a mesma escolha com as três opções.
2. **Dado** um convite pendente com endereço em "Convites", **Quando** o artista toca no endereço,
   **Então** abre a mesma escolha.
3. **Dado** qualquer um desses cards, **Então** o endereço tem alvo de toque de pelo menos 44px de
   altura e o card não ganha rolagem horizontal entre 320 e 430px.

---

### Casos de borda

- **Evento sem endereço**: nada tocável aparece; o cabeçalho continua sem o "• endereço" e o
  "Local" do painel continua "—".
- **Endereço longo** (rua, número, bairro, cidade, CEP): quebra em linhas dentro do card, sem
  rolagem lateral; na escolha, o endereço aparece inteiro.
- **"Endereço" que é nome de lugar** ("Buffet Encantado", "Escola X — unidade Moema"): vai como
  busca para o app de mapas, que mostra o resultado; ninguém valida o texto antes.
- **Caracteres especiais** (acento, "nº", "#", "&", "/"): chegam ao app de mapas exatamente como
  estão no evento.
- **App não instalado**: o link abre o site do mesmo serviço de mapas no navegador.
- **Sistema instalado na Tela de Início** (sem barra de endereço): ao voltar do app de mapas, o
  sistema continua na mesma tela, sem janela presa.
- **Tela larga (computador)**: as três opções abrem o site de mapas em outra aba.
- **Tema escuro**: o endereço tocável e a escolha seguem legíveis, com as cores do tema.

## Requisitos *(obrigatório)*

### Requisitos funcionais

- **FR-001**: Na página do evento do app interno, o endereço do evento DEVE ser tocável no
  cabeçalho e no valor "Local" do painel "Dados do evento" (modo de leitura).
- **FR-002**: No Portal do Artista, o endereço DEVE ser tocável no card de "Próximos eventos" e no
  card de "Convites".
- **FR-003**: Tocar no endereço DEVE abrir uma escolha com título "Abrir endereço", o endereço por
  extenso e três opções nesta ordem: Google Maps, Apple Mapas, Waze, cada uma com pelo menos 44px
  de altura nas duas superfícies.
- **FR-004**: Cada opção DEVE abrir o endereço no serviço escolhido mostrando o local (não a rota
  já iniciada); no celular, o app instalado, e sem o app, o site do serviço.
- **FR-005**: Escolher uma opção DEVE fechar a escolha e deixar a tela do sistema como estava.
- **FR-006**: A escolha DEVE fechar sem abrir nada por toque fora, botão "Fechar" ou Esc, com a
  mesma animação dos outros diálogos do sistema (respeitando "reduzir movimento").
- **FR-007**: O endereço tocável DEVE parecer tocável (ícone de local e cor de link) e ter alvo de
  toque de pelo menos 44px de altura no portal.
- **FR-008**: Evento sem endereço NÃO DEVE mostrar nada tocável.
- **FR-009**: O endereço DEVE chegar ao serviço de mapas sem alteração (acentos e símbolos
  preservados).
- **FR-010**: A escolha DEVE ser uma só, a mesma peça nas duas superfícies, para que o
  comportamento e os textos não divirjam.
- **FR-011**: No computador, o endereço DEVE ser alcançável por Tab e acionável por Enter/Espaço;
  leitores de tela DEVEM ouvir o endereço e que ele abre no app de mapas; ao fechar a escolha, o
  foco DEVE voltar ao endereço.

### Entidades

Nenhuma. O endereço já vem no payload de hoje (`location` do evento, no detalhe do evento e nas
listas do portal); não muda banco, endpoint nem payload.

## Verificação *(obrigatório — Princípio VIII)*

Nada no backend muda (nenhum endpoint, payload, modelo ou regra de negócio). O `verify_347.py`
testa a montagem dos três links, que é onde um erro passa despercebido (um "&" no nome do buffet
cortaria a busca), e confere no `manto_local`, só lendo, que o endereço chega às duas telas.

| # | Cenário do `verify_347.py` | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | endereço com acento, vírgula e número | três opções, na ordem, URLs exatas com o endereço codificado | não |
| 2 | endereço com "&", "#", "/" e espaços nas pontas | símbolos codificados, pontas aparadas (FR-009) | não |
| 3 | vazio, só espaços, ausente | nenhuma opção (FR-008) | não |
| 4 | montador ingênuo, sem codificação, passado pela mesma checagem | a checagem reprova | **sim** |
| 5 | a peça exportada e usada nas quatro telas | nenhuma tela ficou com o texto puro | não |
| 6 | `manto_local`, só leitura: detalhe de um evento com endereço (`GET /api/events/<id>`, login pela API com usuário descartável) e agenda do portal de um talento escalado nele (`portal_ops.get_agenda`) | as duas telas recebem `location` igual ao gravado no evento | não |
| 7 | limpeza | usuário descartável apagado (`roles.clear()` antes) | — |

Conferência de tela, contra o `manto_local`:

| # | Conferência | O que prova |
|---|---|---|
| 1 | App interno, evento com endereço, 390px: tocar no endereço do cabeçalho e do "Local" | a escolha abre com as 3 opções; cada link aponta para o serviço certo com o endereço codificado; abre fora do sistema |
| 2 | App interno, evento **sem** endereço | nada tocável no cabeçalho; "Local" = "—" |
| 3 | Portal 375×812, "Próximos eventos" com endereço | alvo ≥ 44px, sem rolagem lateral a 320/375/430px, escolha abre |
| 4 | Portal 375×812, "Convites" com endereço | idem |
| 5 | Fechar por fora, por "Fechar" e por Esc | nenhum link é seguido |

Mais os portões: `cd frontend && npm run typecheck` limpo nas três SPAs.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Do card ou da página do evento até o app de mapas aberto no local, em 2 toques
  (endereço → app), contra os 5+ passos de hoje (selecionar, copiar, sair, abrir o app, colar).
- **SC-002**: Nas 4 telas tocadas, nenhum caso de endereço longo produz rolagem horizontal entre
  320 e 430px.
- **SC-003**: Nas 3 opções, o local que o app mostra corresponde ao endereço gravado no evento,
  conferido com um endereço com acento e número.

## Fora de escopo

- Endereço do ensaio, da maquiagem e da saída ("Antes do evento" no portal; seção de Ensaio e de
  Logística no app interno).
- Aba "Histórico" do portal (evento que já passou) e as listas da Agenda (Mês/Dia/Lista).
- O botão "Abrir no Maps" da Logística (estimativa de viagem), que continua como está.
- Lembrar o app preferido da pessoa, abrir a rota já iniciada, copiar o endereço.
- Corrigir, geocodificar ou validar o endereço gravado.

## Docs a atualizar

`docs/02` (página do evento no app interno; Agenda e Convites do portal), `docs/03` (entrada no
topo + linha no índice). `docs/01` não muda (sem contrato novo). `docs/00` só ganha a linha do
componente compartilhado se a convenção pedir.

## Premissas

- As três opções aparecem em todo aparelho: no Android ou no computador, "Apple Mapas" abre o site
  da Apple; o pedido nomeou as três sem condicionar ao aparelho.
- "Abrir o endereço" é mostrar o local no mapa; a rota fica a um toque, dentro do app escolhido. Ir
  direto para a navegação escolheria sozinho o primeiro resultado de um texto ambíguo.
- O texto do endereço é o que já está gravado no evento (vindo do Google Agenda ou do formulário);
  a feature não muda de onde ele vem.
