# 03 — Histórico de Mutações (índice)

> **Documento vivo — APPEND ONLY.** Cada feature concluída adiciona uma entrada **no topo** da
> seção "Registro", e uma linha **no topo** da tabela do índice. Nunca reescrever entradas antigas
> (elas são o histórico); correções entram como nova entrada referenciando a anterior.
>
> Última atualização: **2026-08-10** · Estado do repositório: pós-feature **230 (portal segue a
> escala, não o convite)** · Head de migration: `d2e6b94c07f1` (inalterado — 226 e 227 não têm
> migration)
> (confira com `flask db heads` — não versione o head em prosa fora deste cabeçalho).

## Como ler isto sem gastar a janela de contexto

Este arquivo tinha 202 KB (~61k tokens, ~30% de uma janela de 200k) e nenhum índice: era preciso
ler tudo para descobrir onde estava a resposta. Agora ele é **índice + as 12 entradas mais
recentes**; o restante foi movido, **sem perder uma linha sequer**, para `docs/historico/`.

1. Ache a feature na tabela abaixo (arquivo + linha).
2. Leia **só** aquela entrada: `Read(file_path=..., offset=<linha>, limit=~70)`.
3. Nunca leia um arquivo de histórico inteiro — nenhuma pergunta real precisa disso.

Se a sua pergunta é "como o sistema funciona hoje" e não "por que ficou assim", **este documento é
o lugar errado**: comece por `docs/00_MAPA_DO_SISTEMA.md`.

| Preciso de… | Vá para |
|---|---|
| Onde mexer / o que ler primeiro | `docs/00_MAPA_DO_SISTEMA.md` |
| Schema, endpoints, RBAC, deploy | `docs/01_SISTEMA_E_BANCO.md` |
| Fluxo e UX de uma tela | `docs/02_MAPA_DE_PAGINAS_E_UX.md` |
| Fluxos, invariantes e armadilhas por domínio | `docs/04_GUIA_DE_DOMINIOS.md` |
| Dívida técnica priorizada | `docs/05_DIVIDA_TECNICA.md` |
| **Por que** uma decisão foi tomada / o que foi descartado | **este documento** |

## Índice de features

Legenda de arquivo: **(aqui)** = neste documento · **H2** = `docs/historico/200-207.md` ·
**H1** = `docs/historico/184-199.md`.

| Feature | Título | Data | Migration | Arquivo | Linha |
|---|---|---|---|---|---|
| **230** | Portal segue a escala e não o convite: escalação não recusada passa a aparecer (26 futuros e 97 passados invisíveis, R$ 36.910), totais batendo com a planilha | 2026-08-10 | `—` | (aqui) | 150 |
| **229** | Portal: link de avaliar também no histórico da Agenda (`RatingLink`); diagnóstico do "acesso travado" | 2026-08-09 | `—` | (aqui) | 206 |
| **228** | `ConfirmDialog` promovido para o `@manto/ui`; exclusão em lote de pagamentos confirma em diálogo, com a soma e o que a busca escondeu | 2026-08-09 | `—` | (aqui) | 259 |
| **227** | Foto do portal saía por rota de staff (255 talentos com ícone quebrado); coordenador passa a ver o figurino do elenco inteiro | 2026-08-09 | `—` | (aqui) | 295 |
| **226** | Planilha de pagamentos no celular: cartões abaixo de `xl`, caixa de busca de volta e adiantamentos em janela sobreposta | 2026-08-08 | `—` | (aqui) | 365 |
| **225b** | Manutenção de figurino: conserto e ajuste do que já existe, com aviso na ficha e no elenco do evento | 2026-08-07 | `d2e6b94c07f1` | (aqui) | 437 |
| **225** | Produção de Figurinos: o trabalho de produzir ganhou registro, responsável, prazo na agenda e custo real | 2026-08-07 | `c1d5a83b64e7` | (aqui) | 186 |
| **224f** | Conta de recebimento da Loja de Interações Virtuais ganhou tela (estava nula em produção) | 2026-08-07 | `—` | (aqui) | 134 |
| **224e** | Landing da loja: a raiz do `alo.` caía no catálogo de eventos; agora lista as conversas | 2026-08-07 | `—` | (aqui) | 152 |
| **224d** | `alo.mantoproducoes.com.br` como endereço curto da Loja de Interações Virtuais | 2026-08-07 | `—` | (aqui) | 186 |
| **224c** | Estorno de comissão aparecia e descontava em todos os meses; agora só no mês corrente | 2026-08-07 | `—` | (aqui) | 162 |
| **224b** | Loja de Interações Virtuais destravada: upload de capa na gestão, capa servida em rota pública, editor de FAQ | 2026-08-07 | `—` | (aqui) | 205 |
| **224** | Evento com dinheiro vira cancelado (não apagado), com devolução ao cliente; exclusão só para Superadmin | 2026-08-07 | `b8e4d27a91f5` | (aqui) | 186 |
| **223** | Calculadora EducaManto: transporte dobrado no recalcular, Econômico sem adicional por pessoa, NF sem transporte, comissão configurável | 2026-08-07 | `a3f7c19d5e02` | (aqui) | 196 |
| **222** | Exportar elenco perdeu quatro campos (nascimento/CPF/RG/documento) na migração para o React | 2026-08-07 | `—` | (aqui) | 186 |
| **221** | Agente auditor financeiro semanal (endpoints + fix de sobrescrita de upload) | 2026-08-06 | `—` | (aqui) | 161 |
| **220b** | Hotfix: menu "Ferramentas" do evento embaçado no meio | 2026-08-06 | `—` | (aqui) | 133 |
| **220** | Formulários×clientes×eventos: vínculo endurecido, fila de revisão e histórico da cliente | 2026-08-06 | `—` | (aqui) | 156 |
| **219** | Email errado do talento: confirmação no cadastro e fila de devoluções | 2026-08-06 | `b4c81ef07d29`, `c5d92fa16e34` | (aqui) | 217 |
| **218** | Superadmin corrige/exclui faixa de salário; Usuários com filtros; telas desempilhadas | 2026-08-06 | `—` | (aqui) | 292 |
| **217** | Tema escuro com switch na sidebar, e reestruturação da documentação | 2026-08-06 | `—` | (aqui) | 367 |
| **216** | Cachê no portal, prévia de link no WhatsApp, contraste e endurecimento de segurança | 2026-08-05 | `—` | (aqui) | 436 |
| **215** | Tela de evento em abas, com edição inline e buscas visuais | 2026-08-05 | `—` | (aqui) | 494 |
| **214** | Hotfix: Revendedor EducaManto sem acesso a nada (calculadora incluída) | 2026-08-05 | `—` | (aqui) | 571 |
| **213** | Acervo 3D: superadmin exclui peça já usada, desvinculando de todos os eventos | 2026-08-05 | `—` | (aqui) | 606 |
| **212** | Hotfix: diálogos abrindo pela metade, fora da tela | 2026-08-05 | `—` | (aqui) | 638 |
| **211** | Vitrine: quadro da foto com teto e piso | 2026-08-05 | `—` | (aqui) | 671 |
| **210d** | Hotfix: navegador preso no bundle antigo (e vínculo de ficha mais óbvio) | 2026-08-05 | `—` | (aqui) | 706 |
| **210c** | Hotfix: Comercial voltou a enxergar o pagamento do evento | 2026-08-05 | `—` | (aqui) | 738 |
| **210b** | Hotfix: buscador de pré-contrato mudo | 2026-08-05 | `—` | (aqui) | 767 |
| **210** | Hotfix: horário deslocado, anexo do evento e orçamento sem saída | 2026-08-05 | `—` | (aqui) | 802 |
| **209** | Catálogo como espinha organizacional (página própria + fichas + busca) | 2026-08-05 | `e7a1c94f20b3` | (aqui) | 875 |
| **208** | Restauração do papel ENSAIO (dashboard + agendamento + presença) | 2026-08-05 | `—` | (aqui) | 924 |
| **206b** | Hotfix: superfícies públicas por link voltaram a abrir sem login | 2026-08-05 | `—` | H2 | 11 |
| **207** | Pacote de melhorias operacionais (5 frentes) | 2026-08-04 | `d9f2b3a41c07` | H2 | 36 |
| **206** | React como interface primária e proxy reverso em produção | 2026-08-04 | `—` | H2 | 101 |
| **205f** | Loja de Interações Virtuais (resiliência a falha de serviço externo) | 2026-08-04 | `c17b3ea94f52` | H2 | 187 |
| **205e** | Loja de Interações Virtuais (registro financeiro segregado e fechamento) | 2026-08-04 | `—` | H2 | 259 |
| **205d** | Loja de Interações Virtuais (presente 3D, fila de produção e entrega do vídeo) | 2026-07-31 | `—` | H2 | 311 |
| **205c** | Loja de Interações Virtuais (efetivação automática da venda) | 2026-07-31 | `—` | H2 | 357 |
| **205b** | Loja de Interações Virtuais (checkout público e soft lock) | 2026-07-31 | `a5c81e0cd247` | H2 | 406 |
| **205** | Loja de Interações Virtuais (fundação + gestão de campanhas) | 2026-07-31 | `f3a9c72e5d18` | H2 | 458 |
| **204b** | Múltiplos Temas por postagem de marketing | 2026-07-29 | `b7d4f81a6e0c` | H2 | 534 |
| **204** | Módulo de Gestão de Marketing e Frequência | 2026-07-29 | `a3c7e1d59f42` | H2 | 589 |
| **203** | Melhorias na Comunicação e Alertas de E-mail | 2026-07-29 | `—` | H2 | 715 |
| **202** | Fila de Impressão dirigida pelo evento | 2026-07-29 | `e4f7b2c9a350` | H2 | 779 |
| **201** | Acervo 3D: uma peça, vários arquivos | 2026-07-29 | `d9e3a5b7c124` | H2 | 837 |
| **200** | Módulo Core de Impressões 3D | 2026-07-29 | `c8d2f4a6b013` | H2 | 906 |
| **199** | Liberação do status 'No banco' para Comissões e Recorrentes | 2026-07-29 | `—` | H1 | 11 |
| **197** | Refatoração do Dashboard de Avaliações de Clientes | 2026-07-28 | `—` | H1 | 68 |
| **196** | Pivot do Pipeline de Vendas para Dashboard Comercial | 2026-07-28 | `—` | H1 | 146 |
| **195** | Autocomplete de Endereços com Google Places e Comboboxes com Busca Visual | 2026-07-28 | `—` | H1 | 216 |
| **194** | Planilha de Pagamentos: cards-filtro, colorização por faixa e soma da seleção | 2026-07-28 | `—` | H1 | 302 |
| **193** | Importação Histórica do WhatsForm (One-time Migration) | 2026-07-28 | `—` | H1 | 387 |
| **191** | Migração do Portal do Artista (React) e Auditoria de Segurança — **portal** | 2026-07-28 | `—` | H1 | 512 |
| **192** | Detalhe do Evento: layout de duas colunas com paridade total da tela clássica | 2026-07-27 | `—` | H1 | 641 |
| **191** | Calculadora de Orçamento: paridade de layout clássico + cálculo reativo — **orçamento** | 2026-07-27 | `—` | H1 | 717 |
| **190** | Paridade e Unificação do Módulo de Orçamentos e EducaManto (React) | 2026-07-27 | `—` | H1 | 775 |
| **189** | Módulo Financeiro de Alta Fidelidade e Consistência (React) | 2026-07-27 | `—` | H1 | 864 |
| **188** | Refatoração e Paridade do Módulo de Formulários | 2026-07-27 | `—` | H1 | 957 |
| **187** | Reestruturação do Módulo de Comissões | 2026-07-24 | `—` | H1 | 1034 |
| **186** | Gerenciador de Catálogo: UX e fluxo Ficha ↔ Catálogo ↔ Venda | 2026-07-24 | `—` | H1 | 1086 |
| **185** | Catálogo Vitrine Completo: Temas, Personagens e Vídeo | 2026-07-24 | `9f1c3a7b5e2d` | H1 | 1135 |
| **184** | Reconstrução do Formulário de Cadastro/Edição de Eventos | 2026-07-24 | `—` | H1 | 1181 |

> **Colisões e buracos de numeração** (a numeração é a chave primária de fato do histórico e não é
> contínua): existem **duas** entradas `191` — a do Portal do Artista em React e a da Calculadora
> de Orçamento, ambas em H1, desambiguadas na coluna Título. A feature **198 não existe** (número
> pulado, não perdido). `206b` foi mergeada depois de `207`/`208`, por isso aparece fora de ordem
> numérica na ordem cronológica do arquivo.

## Índice por assunto

| Assunto | Features |
|---|---|
| Agenda / evento / formulário de evento | 215, 210, 208, 192, 184 |
| Loja de Interações Virtuais | 205, 205b, 205c, 205d, 205e, 205f |
| Impressões e Acervo 3D | 213, 202, 201, 200 |
| Marketing e frequência | 204, 204b |
| Catálogo e vitrine | 211, 209, 186, 185 |
| Financeiro, comissões e pagamentos | 230, 228, 226, 210c, 199, 194, 189, 187 |
| Orçamento e EducaManto | 214, 191 (orçamento), 190 |
| Portal do Artista | 230, 229, 227, 216, 191 (portal) |
| Design system, tema e acessibilidade | 228, 217, 216, 212 |
| Documentação e economia de token | 217 |
| Formulários e pré-contrato | 210b, 188, 193 |
| Avaliações e dashboards | 197, 196 |
| Infra, deploy, proxy e cache de bundle | 210d, 206, 206b, 212 |
| Segurança / RBAC / endurecimento | 216, 214, 206b |

**Runbooks reexecutáveis embutidos no histórico** (procedimento, não registro): carga histórica do
WhatsForm com backup e import — `docs/historico/184-199.md`, entrada **193**. Não há
`docs/04_RUNBOOKS.md`: os demais procedimentos operacionais (refresh do `manto_local`, backup)
vivem em `scripts/db/README.md`, que **não é versionado** (`.gitignore` cobre `/scripts/db/`).

Formato de cada entrada:

```
### <NNN> — <título>            (branch · data do merge · migration)
Motivação · O que mudou (Backend / Banco / Frontend) · Impacto em RBAC e regras de negócio ·
Rotas e endpoints novos/alterados · Riscos e pegadinhas
```

---

## Registro

*(As 12 entradas mais recentes. As anteriores estão em `docs/historico/` — ver índice acima.)*

### 230 — O portal passa a seguir a escala, não o convite            (main · 2026-08-10 · sem migration)

**Motivação.** Investigando o relato da 229 apareceu um terceiro estado de convite que ninguém
tinha considerado: `invite_status = NULL`, convite **nunca enviado**. Ele não entrava em lista
nenhuma do portal — "Convites" exige `pending`, "Próximos eventos" e "Histórico" exigiam
`accepted`. Resultado: artista escalado que não vê o próprio evento. A reclamação dela, *"não
consigo ver para aceitar os próximos eventos"*, estava **certa**, e o diagnóstico da 229 (que
concluiu não haver nada pendente) estava incompleto.

**O fato que decidiu a regra.** A Planilha de Pagamentos **ignora o convite**: `_pagamentos_query`
(`app/financeiro/routes.py:820`) filtra só talento preenchido + evento não cancelado + mês. Ou
seja, o dinheiro segue a **escala**. A tela de avaliação já concordava com isso (`owned_role` usa
"não recusado"). O portal era o único lugar exigindo aceite — e por isso escondia do artista
evento que ele ia fazer, ou que já tinha feito **e recebido**.

Números do espelho (08/08/2026), antes da correção:

| | cargos | talentos | cachê |
|---|---|---|---|
| passados, não aceitos, invisíveis no histórico | 97 | ~39 | R$ 36.910 |
| futuros com convite nunca enviado, invisíveis em tudo | 26 | 3 | R$ 2.700 |
| avaliáveis que nenhuma lista mostrava (crachá sem destino) | 11 | 7 | — |
| recusados sendo pagos | **0** | — | — |

O caso da relatora em agosto: a planilha tinha **8** cargos dela (R$ 3.000) e o portal mostrava
**2** (R$ 700) — e um dos escondidos já estava marcado como **pago** (R$ 350). Depois da mudança:
histórico 17 → 20 itens, total R$ 6.180 → R$ 7.180, próximos eventos 0 → 4. O caso mais extremo é
um colaborador fixo cujos convites nunca são enviados: histórico 3 → 50 itens, R$ 2.450 → R$ 23.230,
próximos 0 → 23. O portal dele era praticamente vazio.

**O que mudou.** `portal_ops.nao_recusada()` virou a fonte única da cláusula (era duplicada em
`portal_ops` e `portal_rating_ops`), e as listas de `get_agenda` (`upcoming`/`past`) e de
`get_historico` passaram a usá-la em vez de `invite_status="accepted"`. Convites continua listando
só `pending` — é o que precisa de resposta. Cargo **recusado** segue fora de tudo: quando alguém
recusa, o casting troca a pessoa, e é por isso que não existe cargo recusado sendo pago.

`_role_summary` passou a expor `invite_status`, porque a lista agora inclui escalação não aceita e o
mesmo evento pode aparecer em "Próximos" **e** em "Convites". Sem explicação isso lê como defeito,
então o card futuro com convite `pending` ganhou a linha "Falta responder este convite ›" apontando
para a aba. Convite `NULL` **não** ganha aviso: não há o que o artista responder — quem tem que agir
é o casting.

**Pegadinha corrigida de carona.** `get_historico` não tinha o filtro de evento cancelado que
`get_agenda` já tinha desde a 224. Com a regra antiga o furo era pequeno (só cancelado já aceito);
ampliar para "não recusada" sem isso passaria a **somar no total de cachê** evento que não
aconteceu — e que a planilha também não paga. O filtro entrou junto.

**Verificação.** `verify_230_portal_segue_escala.py` 10/10: cláusula única nos três lugares; o
evento não aceito aparecendo no histórico; **portal e planilha fechando com o mesmo número de
cargos e a mesma soma** (13 cargos, R$ 8.580 no mês testado); cargo futuro sem convite aparecendo
em "Próximos" e **não** em "Convites", com `invite_status=None`; recusado fora de tudo; e nenhum
talento (de 120 ativos varridos) com evento avaliável fora do histórico. Sem regressão:
`verify_176_portal_artista` 41/41 e `verify_227` 19/19. `tsc --noEmit` limpo em `apps/portal`. Os
três estados do card conferidos na tela (aviso só no `pending`), contraste do aviso 5,88:1 no claro
e 11,21:1 no escuro.

### 229 — "Não consigo avaliar": o botão existia numa aba, e a artista estava olhando a outra            (main · 2026-08-09 · sem migration)

**Motivação.** Relato de uma coordenadora: *"meu acesso ao portal está travado. Não consigo avaliar
nem ver para aceitar os próximos eventos, nada. Fica só nessa tela e travado."* Com o print da tela
e os dados dela, nada estava travado no sentido técnico — mas a leitura dela era justa, porque a
tela não oferecia saída nenhuma onde ela estava olhando.

**O que o print e os dados dizem.** Ela estava na aba **Agenda**, que tem uma seção chamada
"HISTÓRICO" logo abaixo de "PRÓXIMOS EVENTOS". Nos cartões dessa seção aparecia só "Ver ficha de
figurino" — o link de avaliar existia **apenas na aba Histórico**, a terceira do rodapé, com o
crachá vermelho de 3 pendências aceso. Duas listas com o mesmo nome, e a ação só numa delas: não há
por que procurar a segunda quando você está vendo suas apresentações na primeira.

O resto do relato também fecha sem bug de navegação: os convites dela **não estavam pendentes**
(por isso a aba Convites está sem crachá no print — não havia o que aceitar), e **todo e-mail do
portal aponta para a raiz** (`{PORTAL_URL}/`, ver `email_service.py`), nunca para a tela do convite
ou da avaliação. Ou seja, cada link que ela abria do e-mail ou do WhatsApp a devolvia para a mesma
Agenda — literalmente "fica só nessa tela".

**O que mudou.** `rotuloAvaliacao` + o link com a estrela saíram de `PortalHistoricoPage` para
`components/RatingLink.tsx` (fonte única, Princípio I), e a seção histórico da **Agenda** passou a
renderizá-lo. O componente consulta `usePendingRatings()` por conta própria em vez de receber os
conjuntos por prop: é a **mesma** query key que o crachá da aba lê, então vem do cache e o botão
nunca discorda do número em cima do ícone. Evento futuro não recebe link — avaliar só faz sentido
no que já aconteceu.

Os três estados seguem valendo nos dois lugares: "Avaliar este evento" (na janela de 7 dias),
"Editar minha avaliação" (30 dias) e "Ver minha avaliação" (fora de prazo, leitura).

**Achado que NÃO foi corrigido, porque muda regra de negócio.** `rateable_event_ids`
(`portal_rating_ops.py`) conta escalação **não recusada** — aceita, pendente ou sem convite. Já
`get_historico`/`get_agenda` listam **só `accepted`**. Então um evento passado com convite pendente
é avaliável (entra no crachá, e a tela de avaliação o aceita, porque `owned_role` também usa
"não recusado") mas **não aparece em lista nenhuma**: crachá promete, e não há onde clicar. No
espelho local era exatamente o estado dela — 3 avaliáveis (334, 1188, 1204), todos com convite
`pending`, nenhum entre as 17 apresentações do histórico. Alinhar isso tem consequência nos dois
sentidos (incluir não-aceitos no histórico mexe nos **totais de cachê** exibidos; restringir o
crachá a aceitos tira a cobrança de avaliar de quem nunca respondeu ao convite), então fica
registrado para decisão, não resolvido no escuro.

**Não verificado.** A consulta ao banco de **produção** segue bloqueada pelo classificador, então os
dados vêm do espelho local (08/08 17:02). Ele discorda do print em um ponto: lá os quatro convites
dela estão `pending`, e no print os eventos aparecem em "Próximos"/"Histórico", o que só acontece
com `accepted` — o filtro é de 176/191, então produção o tem. Conclusão: foram aceitos depois do
espelho. Isso não muda o diagnóstico do botão, mas a confirmação final de que ela consegue avaliar
depende de ela abrir o portal.

**Verificação.** `tsc --noEmit` limpo em `apps/portal`. Os cinco casos conferidos na tela a 375px
com entry Vite temporária (apagada depois), reproduzindo a agenda dela: avaliável dentro da janela →
"Avaliar este evento"; avaliado e editável → "Editar minha avaliação"; avaliado fora da edição →
"Ver minha avaliação"; passado fora da janela e nunca avaliado → **sem link**; evento futuro →
**sem link**. Alvos de 44px, sem sobreposição com o link do figurino, sem vazamento horizontal.

### 228 — Excluir pagamento em lote pedia confirmação num alerta do navegador            (main · 2026-08-09 · sem migration)

**Motivação.** Dívida que a própria 226 agravou. A exclusão em lote é a única ação irreversível da
Planilha de Pagamentos, e confirmava com `window.confirm("Excluir N item(ns) selecionado(s)?")` —
contra o Princípio V, que pede diálogo. Enquanto o botão era um "Excluir" escrito por extenso no
topo da tabela, passava. Na 226 ele virou **ícone de lixeira de 44px encostado no "limpar
seleção"**, num rodapé fixo de celular: dois ícones vizinhos, um destrutivo e um inofensivo, no
polegar. E o alerta nativo não diz **quanto** vai sumir nem que parte da seleção está escondida
pela busca — justamente o que a 226 introduziu ao deixar a seleção sobreviver ao filtro.

**O componente já existia, trancado numa página.** `ConfirmDialog` estava dentro de
`GastosRecorrentesPage.tsx`, completo: título, descrição em `ReactNode`, botão vermelho opcional,
`pending` com spinner e `error` renderizado **dentro** do diálogo (que fica aberto para nova
tentativa). Promovido para `@manto/ui` sem uma linha de comportamento alterada — conferido com
`diff` do bloco original contra o promovido, ignorando comentários. Mesmo caminho que `CopyButton`
fez na 189.

**O que o diálogo diz agora.** "Excluir 3 itens selecionados, somando R$ 1.370,50?" · quando há
marcado fora da tela, uma linha em vermelho: "2 itens marcados não estão na tela (o filtro ou a
busca escondeu) e serão excluídos também" · "Não dá para desfazer." O erro do lote de exclusão foi
desviado da faixa de status para dentro do diálogo (`bulkAction.variables?.action === "delete"`
distingue das outras três ações, que continuam usando a faixa).

**Escopo contido de propósito.** Sobraram **37** `window.confirm` no repositório (36 no painel
interno, 1 no portal). Trocar todos de uma vez seria uma migração em massa sem pedido, e cada
troca precisa de `pending`/`error` ligados na mutation certa — não é substituição mecânica. Ficam
inventariados em `05_DIVIDA_TECNICA.md` §7.4, com a ordem sugerida (o que apaga dinheiro ou
registro primeiro).

**Verificação.** `tsc --noEmit` limpo e `vite build` verde em `apps/internal`. Diálogo conferido na
tela a 375px com entry Vite temporária (apagada depois): 343×218 inteiro dentro do viewport, botões
de 44px, "Excluir" no vermelho do tema (`rgb(192,57,43)`), soma correta, "Cancelar" fechando sem
excluir e sem perder a seleção, e o aviso de item escondido aparecendo com busca ativa. O
`data-state="closed"` do Radix confirma que o fechamento funciona — o nó que sobra no DOM é o
artefato conhecido do painel não-compositado, não bug.

### 227 — Foto do portal com ícone quebrado, e o coordenador que não via figurino nenhum            (main · 2026-08-09 · sem migration)

**Motivação.** Dois relatos do mesmo artista no mesmo dia: a foto do perfil dele no portal
aparecia como interrogação, e no evento em que ele era **coordenador** as fichas de figurino não
apareciam. Pareciam dois problemas de cadastro; não eram nenhum dos dois.

**1. A foto: rota errada, e não era só ele.** O portal React pedia a imagem em
`/uploads/talent_photos/…`, que é `@login_required` do **Flask-Login** — sessão de *staff*. Quem
está no portal tem `session["talent_id"]` e nenhum usuário logado, então o navegador recebia um
302 para `/auth/login` no lugar da imagem e o `<img>` caía no ícone quebrado. Confirmado contra
produção: `/uploads/talent_photos/<arquivo>` → 302; `/portal/photo/talent_photos/<arquivo>` → 403
(a rota certa, respondendo sem a minha sessão).

A rota irmã `/portal/photo/<caminho>` existe desde a 176 exatamente para isso, e valida sessão de
talento. Os templates Jinja usavam-na, e `get_figurino` também — mas as fotos **do próprio
talento** ficaram devolvendo o caminho cru na migração para React (159/176/191), em quatro
serializadores diferentes. No banco: **255 dos 259 talentos** têm a foto em `/uploads/…` (todos
quebrados) e 4 têm URL absoluta do Drive (esses funcionavam). Ou seja, o portal estava sem foto de
perfil para praticamente todo mundo, e ninguém tinha relatado.

A correção é uma função só, `portal_ops.portal_photo_url()`, aplicada nos cinco pontos que
serializam imagem para o portal: `_talent_to_dict` (avatar do topo), `get_profile` (perfil e fotos
& documentos), `_media_to_dict` (portfólio), a resposta do upload de foto e `_person_entry` (tela
de avaliação). URL absoluta passa intacta. `get_figurino` largou a cópia local da mesma lógica.
**Nenhum arquivo precisou ser reenviado** — a árvore de uploads está intacta em produção
(conferido baixando duas mídias públicas do catálogo, 200).

**`cnh_file_url` ficou de fora de propósito.** `talent_docs` não está em
`PORTAL_PHOTO_SUBFOLDERS` — documento de talento só sai por `/uploads` com papel CASTING.
Nenhuma tela do portal renderiza esse campo hoje; se um dia renderizar, o certo é uma rota que
confira a posse do documento, não afrouxar a lista de fotos.

**2. O figurino: o coordenador não tem personagem.** No evento relatado — 424, (R&I) MOANA + MAUI,
08/08 — o cargo dele é `character_name='Coordenador'`, `role_type='extra'`, convite aceito. E as
fichas do evento estavam **prontas**: Moana (406) e Maui (407), as duas com foto. `get_figurino`
só juntava as fichas dos personagens *daquele* talento; cargo `extra` não tem personagem, então a
lista voltava vazia e a tela imprimia "Ainda não há ficha de figurino para este evento" — que se
lê como "o figurino não subiu". Pior: a agenda oferecia o link "Ver ficha de figurino" em todo
evento, sem checar se havia algo do outro lado.

Não era erro de digitação: ninguém modelou o coordenador, que é justamente quem precisa conferir
o figurino do elenco inteiro em campo. Agora `get_figurino` varre todos os cargos do evento
quando o talento é o coordenador (`is_event_coordinator`, casando o mesmo literal `"Coordenador"`
+ `role_type="extra"` que `event_ops` grava), e devolve junto **quem interpreta** cada personagem.
Os demais continuam vendo só os próprios personagens — decisão do usuário entre as três opções
oferecidas.

**O que a tela diz agora.** `is_coordinator` viaja no payload porque muda o texto, não só a
lista: com fichas, um aviso explica por que apareceu o elenco inteiro; sem fichas, o coordenador
lê "nenhum personagem deste evento tem ficha cadastrada ainda" e o intérprete sem personagem lê
"você não tem personagem neste evento". E o link some da agenda quando não há ficha (`has_figurino`
por item).

**Pegadinha de custo.** `has_figurino` precisa valer para o histórico inteiro, que num talento
antigo tem centenas de linhas — uma consulta por evento seria N+1 clássico.
`events_with_visible_figurino` resolve a agenda toda em **duas** consultas: uma dos cargos dos
eventos listados, outra das fichas pelos nomes normalizados que faltam FK.

**Compatibilidade.** `get_figurino` passou de 2-upla para 3-upla; a view Jinja legada
(`/portal/events/<id>/figurino`, ainda de pé como strangler-fig) e o template
`figurino_viewer.html` foram atualizados junto, e mostram o nome do intérprete na visão do
coordenador.

**Verificação.** `verify_227_portal_fotos_figurino.py` 19/19 (conversão de caminho nos 4 formatos;
zero talentos sobrando em `/uploads`; coordenador vendo as 2 fichas com o nome de quem interpreta;
intérprete vendo exatamente a dele; quem não está no evento seguindo barrado com `None`/403;
`has_figurino` presente em todo item da agenda). `verify_176_portal_artista.py` segue **41/41**,
incluindo o RBAC do figurino e o upload de foto. `tsc --noEmit` limpo em `apps/portal`. As três
mensagens novas conferidas na tela com entry Vite temporária (apagada depois).

### 226 — Planilha de pagamentos no celular, busca de volta e adiantamentos em janela            (main · 2026-08-08 · sem migration)

**Motivação.** Relato direto: "a visualização e navegação da planilha de pagamentos no celular está
horrível". A tela é uma tabela de 7 colunas com `min-w-[1040px]` dentro de um `overflow-x-auto` —
num telefone de 375px isso são 665px de rolagem lateral, com favorecido, chave PIX e situação
sempre fora da tela. Junto veio o resto: a **caixa de busca** que a planilha Jinja tinha
(`#pay-search`, "Buscar por evento, nome, função, valor, PIX, data…") **nunca foi migrada** para o
React nas features 159/160, e os adiantamentos de salário moravam num `<details>` dentro da célula
"Valor" — no desktop era preciso rolar a planilha de lado para achar o formulário; no celular ele
nascia com a largura da coluna.

**O que mudou (só frontend).** Nenhum endpoint criado ou alterado — é tudo apresentação sobre o
payload que `GET /api/financeiro/pagamentos` já devolvia.

- **`lib/pagamentos.ts` (novo)**: rótulos, paleta por faixa, `bucketOf`, `shiftMonth`,
  `monthLabel` e o índice de busca saíram de dentro da página. Existem agora **duas** views do
  mesmo item, e sem fonte única o cartão do telefone e a linha do computador divergiriam na cor e
  na faixa.
- **`components/Pagamentos/PagamentoItemViews.tsx` (novo)**: `PagamentoRow` (a tabela de sempre,
  agora só de `xl` para cima) e `PagamentoCard` (celular/tablet — 1 coluna no telefone, 2 de `md`
  em diante). `StatusSelect`, `TypeBadge` e o resumo de adiantamento são compartilhados pelos dois.
- **`components/Pagamentos/SalaryAdvancesDialog.tsx` (novo)**: janela sobreposta com bruto ·
  adiantado · líquido, lista com link do comprovante e remoção confirmada em dois toques, e
  formulário com `MoneyInput` + `FileUpload`. Reconstrói o que o `#adv-modal` do Jinja fazia.
- **`PagamentosPage.tsx`**: busca com resumo vivo, setas ‹ › de mês, KPI em 2/3/5 colunas conforme
  a largura, e a barra de ações em lote como rodapé fixo abaixo de `xl`.

**Por que `xl` e não `lg` para a tabela.** A partir de `lg` (1024px) a sidebar fixa de 256px entra,
então o conteúdo tem 768px — e a tabela pede 1040px. Cortar em `lg` deixaria justamente a faixa
1024–1279px (iPad deitado, janela pela metade) com a rolagem lateral que motivou a feature. Em
`xl` o conteúdo tem 1024px e a tabela cabe praticamente inteira.

**Busca: índice do dado, não do DOM.** A versão Jinja montava o índice de cada linha lendo o
`textContent` das células (`buildRowIndex`). Isso amarra a busca ao layout — a coluna que sumisse
no responsivo sairia do índice junto, e com duas apresentações diferentes o cartão nunca casaria
por um dado que só a tabela mostra. Agora o índice vem do item serializado, uma vez por resposta da
API (não por tecla digitada). Duas diferenças de comportamento assumidas, ambas para melhor: o
valor entra **formatado e cru** (`1.234,56` e `1234,56`, que é como se digita conferindo o
extrato), e cada palavra é uma restrição que **se soma** — "joao 1500" acha, onde o `indexOf` da
frase inteira do Jinja não achava nada.

**Diálogo lê da query, nunca de um instantâneo.** `SalaryAdvancesDialog` recebe o item derivado de
`items.find(...)`, e a página guarda só o **id**. Um `setState(item)` congelaria o total: gravar
adiantamento muda o próprio item no servidor, o TanStack Query refetch, e a janela seguiria
mostrando o líquido antigo — a mesma armadilha registrada na feature 204 (card de postagem).

**Pegadinhas encontradas.**
- A barra de ações em lote com os rótulos longos quebrava em **três linhas** no telefone: 146px de
  rodapé fixo, mais que um cartão da lista. Rótulo curto (Pago · Banco · Não pago) + ícone para
  excluir/limpar trouxe para 94px, com todos os alvos em 44px.
- `bg-accent-soft` é translúcido de propósito; como rodapé **fixo** ele deixava os cartões
  aparecerem por baixo. No celular a barra usa `bg-panel` opaco e só recupera o `accent-soft` em
  `xl`, onde está no fluxo, sobre o painel.
- Os badges de salário/recorrente e o aviso "adiantado" trocaram `text-gold` por **`text-gold-ink`**
  — o degrau de texto sobre fundo dourado. Sobre `gold-50`/`gold-soft` isso é a diferença entre
  ~3:1 e 4,8–10:1.
- A seleção continua sobrevivendo ao filtro e à busca (comportamento da 194, mantido de propósito),
  mas agora a barra avisa **"(N fora do filtro/busca)"** — sem isso, buscar depois de marcar
  esconde itens que a ação em lote ainda vai atingir.

**Verificação.** `npx tsc --noEmit` limpo e `vite build` verde em `apps/internal`. Conferência
visual feita com um entry Vite temporário (`dev-pagamentos.html` + `src/dev/`, **apagados depois**)
que renderiza a página real com o cache do TanStack Query pré-carregado — assim as medições saíram
sem depender de sessão no `manto_local`. Medido em 375/768/1024/1280px: zero vazamento horizontal
(`scrollWidth == clientWidth == 375`), cartão de 317px com a chave PIX longa contida, tabela oculta
abaixo de `xl` e cartões ocultos acima, rodapé fixo de 94px ancorado em `bottom: 0` com 55px de
folga para o último cartão, e diálogo de 330px (celular) / 492px (desktop) inteiro dentro da tela.
Busca conferida em nome, título de evento, valor cru, dois termos, sem acento/maiúscula e sem
resultado; adiantamento conferido nas três recusas (valor zero, acima do disponível, sem
comprovante), na remoção em dois toques e no caso de salário 100% adiantado; setas de mês
conferidas na virada de ano (2026-08 → 2027-01 → volta).

### 225b — Manutenção de figurino            (main · 2026-08-07 · `d2e6b94c07f1`)

**Motivação.** Boa parte do trabalho da oficina não é produzir peça nova, é mexer no que já
existe. O caso relatado pelo cliente: "recebemos um feedback do evento e a pessoa falou que dentro
do boneco tem uma peça solta" — hoje isso se combina por voz e some. E o segundo: "para esse
evento nesse dia, fazer esse reparo específico" — trabalho manual, **sem compra nenhuma**, que
também precisa ficar escrito.

**O que foi feito.** `FigurinoProducao` ganhou `kind` (`producao`|`manutencao`) e `severity`
(`impede_uso`|`pode_esperar`). Nenhum pedido existente muda: `kind` nasce `producao`.

**Decisões e por quê.**

- **Manutenção não passa por aprovação.** Produção passa porque figurino é 70% do gasto extra;
  manutenção quase nunca tem compra. Exigir um super admin para liberar uma costura mataria o
  registro, que é justamente o que se quer ganhar. As transições saem de `FIGURINO_PROD_FLUXOS` e
  são **derivadas** da ordem do fluxo (`_transicoes_do_fluxo`) — duas tabelas escritas à mão
  divergiriam na primeira mudança.
- **Gravidade é obrigatória na manutenção.** É a única informação que muda uma decisão: a peça
  pode ir para o próximo evento assim, ou não pode? Sem ela o registro seria só um bilhete.
- **O valor não está na tarefa, está no aviso.** Com `impede_uso` aberto, a ficha e o **elenco do
  evento** carregam o alerta. É lá que "tem uma peça solta dentro do boneco" muda alguma coisa —
  na hora de separar o figurino da próxima festa. No card do elenco o bloqueio **vence o
  "Separado"** (borda vermelha ganha da verde): marcar como separada uma peça que não pode ir é
  exatamente o erro que o aviso existe para impedir. Verificado na tela, num evento real.
- **Resolver apaga o aviso.** Alerta que não some vira ruído e deixa de ser lido.
- **Aviso ao setor, não à pessoa.** Pedido sem responsável manda e-mail para a equipe de figurino
  + super admins (molde de `gastos_ops.create_expense`) e entra num painel próprio da home,
  "Oficina — sem responsável". Manutenção nasce órfã quase sempre. Este painel é por **papel** —
  ao contrário de "Minhas peças", que é por identidade.
- **A ordem das validações segue a ordem dos campos na tela.** Quem esquece dois campos recebe
  primeiro o erro do de cima e conserta de cima para baixo. Foi um teste que pegou isso: com ficha
  e gravidade vazias, o erro que voltava era o do título.
- **Na manutenção o dinheiro sai da frente:** quantidade some do formulário e o painel de gastos
  só aparece se houver custo previsto ou gasto lançado. Um "R$ 0,00" grande sugeriria que falta
  lançar alguma coisa.

**Verificação.** `verify_producao_figurinos` **70/70** (era 50/50). Os 20 novos cobrem: ficha e
gravidade obrigatórias, manutenção não oferecendo "aprovado" (nem para super admin), o alerta
chegando na ficha e sumindo quando resolvido, a fila do setor com gate por papel, e os filtros por
tipo e por figurino. Sem regressão: `verify_cancelamento_evento` 44/44,
`verify_151_excluir_sync` 31/31, `tsc --noEmit` limpo. (`verify_145_agenda_read` segue 20/21 e
`verify_154` 57/58 — ambas pré-existentes, confirmadas com `git stash`.)

### 225 — Produção de Figurinos            (main · 2026-08-07 · `c1d5a83b64e7`)

**Motivação.** Figurino é **70% de todo o gasto extra da empresa**: R$ 47.969,81 de R$ 68.149,66,
em 40 lançamentos. E era a única parte da operação sem lugar no sistema. `FigurinoSheet` (616
fichas) descreve o figurino **pronto** de um personagem — a peça é uma string dentro de um JSON,
sem identidade, sem responsável, sem prazo, sem custo. `SpecialExpense` registra o dinheiro
**depois** que saiu. No meio, o trabalho de produzir não tinha registro.

O caso que motivou: o figurino das Cartas (Alice/Cuiabá, evento 395) são **dez** lançamentos
soltos — pedraria, aviamento, bota, lentes, sapato, fitas de gorgurão, a comida de quem virou até
as 23:00 e a "parte final" de R$ 4.800. Ninguém conseguia responder, a partir do sistema, quanto
custou, quem estava fazendo, ou se ficou pronto a tempo. Vinculados ao pedido novo, somam
**R$ 6.310,18** — R$ 1.310,18 acima do previsto.

**Modelo.** Três tabelas: `figurino_producoes` (o pedido), `figurino_producao_anexos` (fotos e
orçamentos, com `kind` discriminando e `supplier_name`/`amount` só para orçamento) e
`figurino_producao_logs` (histórico com autor, papel, texto e **foto** — o "mini histórico de
evolução"). Mais `special_expenses.figurino_producao_id`.

Fluxo: `solicitado → aprovado → em_producao → pronto`, com `cancelado` como saída. Só SUPERADMIN
aprova (é onde se segura o gasto antes de acontecer); Figurino e Superadmin executam; **qualquer**
papel interno abre pedido — quem sabe que falta uma bermuda é quem vendeu o evento, não a oficina.

**Decisões e por quê.**

- **Evento e ficha são vínculos opcionais.** Cinco dos 40 gastos de figurino não têm evento
  ("Mascotes Copa 4/4", "SAPATO GABBY HUMANA"): é produção de acervo, não de show.
- **`ON DELETE SET NULL` em tudo que aponta para fora.** Excluir o evento não pode apagar o
  pedido, e apagar o pedido não pode apagar o gasto — o dinheiro saiu de verdade. É a lição que a
  224 aprendeu apanhando: `special_expenses.event_id` era `NO ACTION` e quebrava a exclusão do
  evento com violação de chave estrangeira.
- **Vincular gasto existente, nunca recriar.** Recriar perderia data de competência, comprovante e
  aprovação. É o que permite organizar os 40 lançamentos que já estão no banco.
- **O total conta só gasto aprovado** — mesmo recorte da DRE. Um pedido não pode exibir um total
  que o financeiro ainda não reconheceu.
- **Painel pessoal na home.** Primeiro do sistema: todos os outros são por **papel**, este é por
  **identidade** (`responsible_id == user.id`). Por isso não passa por `_effective_has_role`, e o
  "Ver como" de um super admin não muda de quem são os pedidos.

**A armadilha do evento fantasma.** O prazo do figurino vira um compromisso de dia inteiro no
Google, com a pessoa responsável **convidada** — e vive no mesmo calendário dos shows, porque
`CALENDAR_ID = "eventos@mantoproducoes.com.br"` é o único que a conta conectada tem. `sync_events`
importa **tudo** que encontra: sem guarda, cada prazo viraria um `CalendarEvent` na plataforma,
inflando agenda, funil e DRE em silêncio.

A marca é `extendedProperties.private.manto_kind` (`_is_manto_task_item`, `calendar/routes.py`),
não prefixo no título: título é editável dentro do Google, e uma renomeação inocente traria o
fantasma de volta. `upsert_task_event` é uma função **nova e separada** de `insert_event` — o par
que serve aos eventos de show não foi tocado, para não arriscar o que já sincroniza.

**Pegadinha nova, e ela mordeu.** Verificando a feature na tela, um compromisso **de verdade** foi
criado na agenda da empresa e um convite chegou à responsável real (Lucimara). Causa: `manto_local`
é espelho fiel da produção, então traz `SiteSetting.google_token`, e o calendário de destino é
fixo — exatamente a armadilha que `_suppress_mail` já documentava para e-mail, por outro caminho.
Criado `config._suppress_calendar_invites` (`CALENDAR_SUPPRESS_INVITES`), com a mesma regra: banco
em localhost não escreve na agenda real, a menos que alguém peça com
`CALENDAR_ALLOW_LOCAL_INVITES=true`. O compromisso foi removido e a agenda varrida.

**Verificação.** `scripts/db/verify_producao_figurinos.py` — 50/50. Cobre o ciclo completo, o RBAC
da aprovação, o total contando só aprovado, a exclusão do evento com o pedido sobrevivendo, o
`sync_events` **não** criando fantasma, a trava de ambiente do Google, e o painel pessoal
aparecendo só para o responsável. Sem regressão: `verify_cancelamento_evento` 44/44,
`verify_151_excluir_sync` 31/31. (`verify_154_talentos_figurino` segue 57/58 — falha pré-existente,
confirmada com `git stash`, não relacionada.)

### 224f — Conta de recebimento da Loja de Interações Virtuais ganhou tela
`main` · **2026-08-07** · sem migration

**Motivação.** `infinitepay_handle` e `infinitepay_webhook_token` estavam **nulos em produção**, e
sem eles toda reserva morre em "O meio de pagamento ainda não está configurado" antes mesmo de
gerar o link. As colunas existiam desde a 205 e o checkout as lia, mas **nenhuma tela as
escrevia** — só SQL direto. Mesma família dos buracos da 224b: backend pronto, sem superfície.

**O que entrou.** Card "Pagamento da Loja de Interações Virtuais" em Configurações. A InfiniteTag
é digitada (o `$` inicial é removido — a operadora espera sem). O **token do webhook não se
digita**: é o segredo que autentica o aviso de pagamento, então a tela só mostra se já existe e
oferece "gerar um segredo novo ao salvar" (`secrets.token_urlsafe(32)`). Gerar de novo invalida o
endereço anterior de propósito — é a ação de quem suspeita de vazamento.

**O token nunca sai pela API de leitura**: o payload devolve só `infinitepay_webhook_configured`
(booleano). Um segredo que trafega para a tela é um segredo no cache do browser.

### 224e — Landing da loja: a raiz do `alo.` caía no catálogo de eventos
`main` · **2026-08-07** · sem migration

**Motivação.** A 224d mandou a raiz de `alo.mantoproducoes.com.br` para `/catalogo/` com o
argumento de que "quem digita só o domínio não tem campanha para ver". Estava errado: quem entra
pelo endereço da loja de conversas recebia a grade de personagens para festa, que é outro produto.

**O que entrou.** `GET /api/virtuais/vitrine` (público) lista as campanhas publicadas, e
`/v` no app público virou a **landing da loja**: chamada, os três passos de como funciona, os
cards das campanhas com preço das duas modalidades, e o FAQ no fim — mesma ordem e mesmo motivo
da landing de campanha (FR-013: quem chega pelo Instagram quer preço primeiro, dúvida depois).
A raiz do host passou a apontar para `/catalogo/v`.

O caminho é `/vitrine`, e não `/campanhas`, porque `GET /api/virtuais/campanhas` já é a listagem
**interna** (gated) e `/campanhas/publicadas` colidiria com o `<slug>` da landing.

**Copy no código, de propósito.** É texto de marca, não configuração de campanha — essa fica na
tela de gestão, por campanha. Mudar exige deploy; se virar rotina, vira campo.

**Uma checagem que mudou a copy:** os avisos ao cliente saem **só por e-mail**
(`_enviadores_de_aviso`), não por WhatsApp. O texto dos passos diz e-mail — prometer WhatsApp
seria mentira na primeira venda.

**Campanha esgotada continua listada**, com aviso: sumir da lista faria quem recebeu o link e
voltou depois achar que errou o endereço.

### 224d — `alo.mantoproducoes.com.br` como endereço da Loja de Interações Virtuais
`main` · **2026-08-07** · sem migration

**Motivação.** A landing só era alcançável em `app.mantoproducoes.com.br/catalogo/v/<slug>` —
endereço longo, com o `/catalogo/` no meio, e apontando para o domínio do ERP. É link de story e
de bio: precisa ser curto e falável.

**O que mudou.** `ALO_HOSTS` no `frontend/server.js` (padrão
`alo.mantoproducoes.com.br`, sobrescrevível por env). No host da loja, `/<slug>` vira
`/catalogo/v/<slug>` e `/pedido/<token>` vira `/catalogo/v/pedido/<token>`; a raiz cai na
vitrine, porque quem digita só o domínio não tem campanha para ver. Espelha o `PORTAL_HOSTS`
que já existia para `portal.mantoproducoes.com.br`.

**Redirect, não reescrita** — mesmo motivo do portal: o bundle público roda com
`base`/`basename` = `/catalogo` e lê a URL do browser; reescrever só `req.url` serviria o bundle
certo com o roteador sem casar rota nenhuma. Consequência assumida: o link compartilhado é
curto, mas depois de carregar a barra de endereço mostra o `/catalogo/v/`. Deixar a raiz
limpa exigiria um segundo build de `apps/public` com `base: "/"` — dist e mount próprios.

**Infra.** Nenhum repositório ou serviço novo: é domínio custom no **serviço de frontend** que
já serve `app.` e `portal.`, mais o CNAME. `ALO_HOSTS` só precisa ser definido se o domínio for
outro.

**Pegadinha.** O bloco fica DEPOIS do `isBackendRequest`, senão `/api`, `/uploads` e
`/catalogo/midia` no host da loja virariam `/catalogo/v/api…`.

### 224c — Estorno de comissão aparecia (e descontava) em todos os meses
`main` · **2026-08-07** · sem migration

**Motivação.** Incidente relatado: as comissões da vendedora foram pagas em 05/08 (37 linhas,
R$ 3.529,85, todas de julho — confirmado no banco de produção); em 07/08 o sync apagou o
`(SHOW) PETER PAN…` porque ele sumiu do Google Agenda, e a exclusão gerou o estorno correto de
−R$ 170,00 sobre a comissão #105, que tinha sido paga justamente no dia 5. Até aí, certo.

O problema era **onde** o estorno aparecia. `_pending_reversals_query` não tem filtro de mês (de
propósito: o estorno herda a `sale_date` da venda, que costuma cair em mês já quitado, e sem
isso ele se perderia). Só que `_seller_payable_rows` o injetava em **todo** mês — então abril,
que não tinha nada com aquilo, mostrava R$ 1.776,97 no lugar dos seus R$ 1.946,97. E a 224
tinha acabado de trazer o estorno para a tabela também, então a mesma linha reaparecia em cada
tela: parecia comissão ressuscitada.

**A regra agora.** Estorno é dívida abatida no **próximo repasse**, então entra na conta do
**mês corrente** (`_estornos_do_mes`). O mês da venda original continua mostrando-o pela via
normal, porque a `sale_date` dele é a da venda estornada. Nenhum outro mês é tocado. Ele não se
perde: fica no mês corrente até ser liquidado.

**Não confundir com o que NÃO era bug.** As 24 comissões pendentes de dez/25 a abr/26
(R$ 3.843,18) foram criadas em junho, quando os eventos antigos entraram no sistema, e nunca
foram pagas — os três repasses existentes (08/06, 07/07, 05/08) cobriram maio, junho e julho.
São dívida real em aberto, não reaparição.

**Achado à parte, não corrigido:** `(R&I) SEREIA BRILHANTE` tem duas comissões de R$ 137,50 —
#28 (paga, evento 287, sem `sale_value`) e #95 (pendente, evento 288, venda de R$ 5.500). Os
dois eventos existem, em 20/06 e 21/06, com o mesmo título: cheiro de evento duplicado na
importação. Decisão de negócio, não de código.

**Verificação.** `scripts/db/verify_estorno_comissao_mes.py` — 17/17, com um estorno em mês
fechado, um mês antigo intocado, a tabela fechando com o total em todo mês, e a liquidação
pagando o líquido (300 − 170) sem arrastar a dívida antiga. `verify_187_comissoes.py` (20/20) e
`verify_199` (16/16) seguem verdes.

### 224b — Loja de Interações Virtuais destravada: capa publicável e visível ao público
`main` · **2026-08-07** · sem migration

**Motivação.** A feature 205 estava construída inteira — landing, reserva, pagamento,
efetivação com evento na agenda + sala do Meet + pré-escala, avisos, fila de produção,
devoluções, 137/137 no `verify_205.py` — e **nunca tinha sido usada**: zero campanhas, zero
pedidos, zero eventos `VIRTUAL` em produção. O motivo eram dois buracos em "fotos", ambos
invisíveis para quem lê o código de um lado só.

**1. Nenhuma campanha conseguia ser publicada.** A tela de gestão mandava sempre JSON, então a
capa nunca chegava — e `cover_url` é pré-requisito de publicação
(`_campos_faltantes_para_publicar`). O backend já aceitava `multipart` com o campo `cover`
desde o início; faltava o formulário usar. Reproduzido pela API: criar 201, gerar horários 201,
publicar **400 "A foto de capa é obrigatória"**.

**2. A capa não apareceria nem depois de enviada.** `save_file` devolve
`/uploads/virtual_covers/…`, e `/uploads/*` é `login_required` — o visitante da landing era
redirecionado para a tela de login do staff (302 comprovado). Produção guarda mídia em disco
local, não em S3 (255 de 259 fotos de talento são `/uploads/…`), então valia lá também.

**O que mudou.** `_cover_url` (`app/api/virtuais_write.py`) reescreve a URL salva para a rota
pública nova `GET /catalogo/midia/campanhas/<arquivo>`
(`catalogo.midia_campanha`), que serve **só** de `virtual_covers` — mesma forma do
`/catalogo/midia` que já servia as fotos do catálogo, e mesma reescrita que o importador já
fazia. Mora sob `/catalogo/midia/` de propósito: esse prefixo já é repassado pelo
`frontend/server.js` e proxiado pelos vite configs dos três apps; um prefixo novo exigiria
mexer nos três (o gap de proxy por app da feature 182). Em S3 a URL já volta pública e nada é
reescrito. A rota é declarada **antes** da genérica — `<path:filename>` engoliria
`campanhas/arquivo.jpg`.

No frontend, `campaignBody` (`lib/virtuais.ts`) monta `FormData` quando há capa e JSON quando
não há, serializando o FAQ como o `_payload` do servidor já o lê. A tela ganhou o campo de capa
com prévia e o **editor de FAQ** — que também faltava: o FAQ era carregado e reenviado no
salvamento, mas sem editor saía sempre vazio, com a landing tendo a seção pronta para exibi-lo.

**Pegadinhas.** O `File` sai do estado depois de salvar, senão cada salvamento seguinte
reenviaria o arquivo. SVG é recusado na capa (`COVER_EXTENSIONS`) — imagem que executa script
no origin da landing. E a rota pública não aceita travessia de diretório: `send_from_directory`
barra, e o teste cobre.

**Verificação.** `scripts/db/verify_loja_virtual_publicacao.py` — 18/18 contra `manto_local`,
subindo um PNG de verdade, publicando e abrindo a landing **sem sessão** para provar que a foto
responde 200 e não é redirect. `verify_205.py` segue 137/137. Conferido também na tela: capa
enviada pela gestão, campanha publicada e landing exibindo a foto (`naturalWidth > 0`) e o FAQ.

### 224 — Evento com dinheiro não é mais apagado: vira cancelado, com devolução ao cliente
`main` · **2026-08-07** · migration `b8e4d27a91f5`

**Motivação.** Em 07/08 o sync apagou o `(SHOW) PETER PAN…` de novembro depois que ele sumiu do
Google Agenda — e a cliente já tinha pago R$ 2.500. A comissão foi tratada certo (a paga virou
estorno de −R$ 170, que desconta no repasse seguinte), mas o **pagamento recebido evaporou**:
`_clear_event_side_tables` apaga os `EventPayment` junto com o evento, e depois disso não existe
registro de que o dinheiro entrou nem a que a devolução se refere. Não havia como excluir pela
tela sem causar o mesmo estrago: o botão existia, escondido no kebab, e só perguntava "tem certeza?".

**A regra nova.** Evento **vazio** (sem venda, sem pagamento, sem contrato, sem elenco escalado)
continua sendo excluído de verdade — é o criado por engano. Evento com qualquer dessas coisas
presa é **cancelado**: `cancelled_at` o tira da agenda e de toda métrica, mas o registro fica,
porque é a ele que a devolução se refere. Quem decide qual das duas acontece é o servidor
(`cancel_ops.pode_excluir`); a tela mostra o porquê antes de confirmar
(`cancel_ops.resumo_impacto`).

**RBAC.** `_CAN_DELETE` virou **só Superadmin**. O Comercial ganhou "Solicitar exclusão" com
motivo obrigatório (`_CAN_REQUEST_DELETE`), e o Superadmin decide pela fila em
`/events/cancelamentos` ou pelo banner no próprio evento.

**A devolução reusa Gasto Extra**, com `disbursement_type="cliente"` e categoria "Devolução a
cliente" — sem entidade nova. Nasce aprovada (quem cancela já é Superadmin) e por isso entra
sozinha na Planilha de Pagamentos e na DRE do mês, que já somam `SpecialExpense` do período.
Nome e PIX de quem recebe moram nos mesmos campos do fornecedor: a forma do dado é idêntica.

**Onde o cancelado some.** Agenda (`_query_month_events`), vendas (`list_closed_sales`), DRE
(as duas queries gêmeas), planilha de pagamentos (`_pagamentos_query`), comissão
(`_sync_commission_payment`), disponibilidade do casting (`talent_availability`), aviso de
personagem no dia (`personagens_no_dia`), dashboard (`_base_filters`) e portal do talento. No
sync ele é intocável: nem `_cleanup_stale_events` o apaga (ele saiu do Google de propósito) nem
`sync_events` o reescreve.

**Dois bugs de exclusão corrigidos no caminho**, ambos da mesma família — FK `NO ACTION` que
`_clear_event_side_tables` não limpava, fazendo a exclusão estourar 500:
1. **gasto extra vinculado** (`special_expenses.event_id`) — agora é **desvinculado**, não
   apagado: o gasto é dinheiro que saiu de verdade e precisa continuar na DRE. Há 57 gastos
   vinculados a evento na base;
2. **sub-avaliações** (`event_sub_ratings.rating_id`) — descoberto pelo próprio script de
   verificação, que tentou apagar um evento com avaliação detalhada.

`_delete_event` também deixou de usar `flash` para o erro do Google: agora devolve o aviso, que
o adaptador Jinja mostra e a API entrega no corpo. Excluir **continua removendo do Google
Agenda**; cancelar também.

**Estorno de comissão visível.** `get_month_entries` passou a unir os estornos pendentes, como o
resumo por vendedor já fazia. Sem isso, a tabela de agosto listava R$ 868,40 em linhas enquanto
o topo dizia R$ 698,40 — o estorno descontava sem aparecer em lugar nenhum.

**Pegadinhas.** `/events/cancelamentos` precisa ser declarada **antes** de `/events/:id` no
React Router. O teto da comissão e a devolução são coisas distintas: a devolução não vira custo
do evento cancelado nas métricas, porque o evento saiu delas — ela entra pela soma de gastos do
período. E o cancelamento fica **imune ao sync**, senão o primeiro ciclo depois dele apagaria o
registro que sustenta a devolução.

**Verificação.** `scripts/db/verify_cancelamento_evento.py` — 44/44 contra `manto_local`,
montando um evento com venda, pagamento recebido, elenco e comissão paga, cancelando e exigindo
que ele tenha sumido de cada superfície. `verify_151_excluir_sync.py` atualizado para o contrato
novo (31/31).

### 223 — Calculadora EducaManto: transporte dobrado, transporte não cobrado e comissão muda
`main` · **2026-08-07** · migration `a3f7c19d5e02`

**Motivação.** Revisão operacional da calculadora EducaManto. Seis defeitos, dois deles cobrando
errado em produção.

**1. "Recalcular" dobrava o transporte.** O snapshot guardava só `kmT` (ida **e volta**, que é o
que o PDF mostra) e a tela repopulava com ele o campo de **ida** — o cálculo dobrava de novo.
Medido nos 18 orçamentos do histórico que têm transporte: **2,00× em todos**. Agora o snapshot
grava `km_ida` junto, e `load_quote_snapshot` deriva `kmT/2` para os snapshots antigos (os valores
congelados do PDF seguem intactos; só a entrada do recálculo é normalizada).

**2. Pacote Econômico não cobrava o adicional por pessoa do transporte.** O headcount saía do item
"Catering apresentação", que os 7 pacotes Econômicos não têm (a escola fornece a alimentação) —
o transporte caía para só a rodagem, com a equipe inteira viajando. Num evento de 200 km × 2 dias
eram **R$ 2.933 a menos**. Agora o headcount é o **maior qty entre as linhas que crescem com o
ensemble** (`ensemble_add > 0`), que são exatamente as cobradas por cabeça. Conferido nos 22
pacotes: idêntico nos 15 que já funcionavam, corrige os 7 Econômicos.

**3. A comissão do vendedor era capada em silêncio.** O teto (valor do pacote) cortava o valor
digitado e a tela seguia exibindo o que ele digitou — R$ 20.000, R$ 50.000 e R$ 100.000 produziam
o mesmo orçamento. `calcular_pacote` agora devolve `acrescimo_efetivo`/`acrescimo_maximo`/
`acrescimo_capado`, e a tela avisa.

**4. A Nota Fiscal não alcançava o transporte.** Ele era somado depois do `÷ 0,84`, então a Manto
absorvia o imposto dessa parcela (R$ 813 numa viagem de R$ 3.986) — e era **inconsistente com a
Calculadora de Orçamento**, onde o transporte entra antes. Agora o transporte entra na base, antes
do bruteamento e do arredondamento. Pacote sem transporte não muda de valor.

**5. A % da comissão EducaManto saiu do código.** Era a constante `EDUCAMANTO_COMMISSION_RATE = 5`;
virou `SiteSetting.educamanto_commission_rate`, editável em Configurações → Financeiro. NULL
mantém 5%, então a migração não altera nenhum cálculo existente. O override por evento
(`event.commission_rate`) continua ganhando de tudo.

**6. UX.** Campo **Km (ida)** visível e editável (antes não havia como conferir nem corrigir o que
o Maps trouxe); mensagem de recuperação mostrava o veículo no lugar da distância; "Gerar orçamento"
desabilitado enquanto o cálculo debounced não volta (dava para congelar no PDF o valor anterior).

**Extra pedido junto.** Campo **Data da apresentação** com o mesmo alerta de personagens já
escalados no dia da Calculadora de Orçamento. `/api/orcamento/personagens-no-dia` é restrito a
Comercial/Superadmin, então o endpoint novo `/api/educamanto/personagens-no-dia` reusa
`orcamento.quote_ops.personagens_no_dia` atrás do gate do EducaManto — Ensaio e Revendedor também
precisam do aviso. A data não entra no preço.

**Pegadinhas.** O teto da comissão é o valor do pacote **sem** transporte: transporte é repasse de
custo, ampliar o teto com ele não faz sentido. O PDF (`educamanto/pdf.py`) só imprime os totais e
a nota "valores já incluem logística/transporte", então a mudança 4 não duplica nada lá. Amarrar
headcount a uma linha de comida foi a origem do defeito 2 — alguém removeu o catering do Econômico
e zerou o transporte sem perceber; os orçamentos de julho ainda gravaram 11 pessoas nesses pacotes.

**Verificação.** `scripts/db/verify_educamanto_calculadora.py` — 24/24 contra `manto_local`,
cobrindo os seis pontos e o RBAC do endpoint novo (Revendedor 200, Figurino 403).

### 222 — Exportar elenco perdeu quatro campos na migração para o React
`main` · **2026-08-07** · sem migration

**Motivação.** Reclamação direta: "no antigo sistema Flask essa telinha de exportar elenco tinha
mais informações". O modal Jinja (`app/templates/event_detail.html`) oferecia **dez** campos —
Personagem, Nome completo, Data de nascimento, CPF, RG, Link documento, Top, Bottom, Calçado e
Altura. O React ficou com **seis**: a porta esqueceu os quatro de documento/nascimento, porque
`_serialize_talent` (`app/api/agenda_read.py`) nunca chegou a serializá-los.

**O que mudou.** *Backend*: `_serialize_talent` ganhou `birth_date` (ISO), `cpf`, `rg` e
`doc_photo_path`, atrás de um novo parâmetro `show_pii`. *Frontend*: `RoleTalent` (`lib/agenda.ts`)
declara os quatro como **opcionais** — para os outros papéis a chave nem existe no JSON — e o
`ExportElencoDialog` voltou a ter as dez caixas de seleção, na ordem da tela antiga.

**Impacto em RBAC.** `show_pii = show_casting or can_confirm` — exatamente o público que via o
botão na tela antiga (`CASTING`, `COMERCIAL`, `SUPERADMIN`). Sem esse gate a mudança seria um
vazamento: Figurino, Ensaio e Artista 3D leem o **mesmo** `/api/events/<id>` e passariam a receber
CPF e RG de todo mundo escalado. Verificado em `scripts/db/verify_export_elenco_documentos.py`
(21/21 contra `manto_local`), que testa os dois lados — quem recebe e quem não recebe.

**Pegadinhas.** (1) `birth_date` é data pura: `new Date("1998-03-12")` vira meia-noite **UTC** e
em São Paulo volta um dia — o modal formata quebrando a string, sem `Date` (a mesma armadilha da
210, agora em data sem hora). `TalentDetailPage.formatDate` ainda tem esse bug, não tocado aqui.
(2) O link do documento tem que sair **absoluto**: `assetUrl()` devolve path puro em dev, e o
texto exportado é colado no WhatsApp. (3) `doc_photo_path` pode já ser uma URL do Drive (legado da
154) — daí o teste de `^https?://` antes de prefixar a origem.

### 221 — Agente auditor financeiro semanal
`221-agente-auditor-financeiro` · **2026-08-06** · sem migration

**Motivação.** O dono não revisa todas as movimentações; comprovante falso, duplicado ou
divergente passava sem verificação nenhuma. Pedido direto: rotina de segunda ~06h que lê os
comprovantes e cruza com o registrado, usando a assinatura do Claude (zero API paga).

**O que entrou.** (1) **Fix crítico**: `_save_bounded_upload` salvava com `secure_filename`
puro — uploads homônimos ("Comprovante.pdf") sobrescreviam o binário anterior em silêncio;
a base de produção tem **11 casos reais** de `file_path` repetido em `event_payments` por
causa disso. Agora prefixo timestamp+uuid. (2) Endpoints `audit_agent.py` (ver
`docs/01_SISTEMA_E_BANCO.md` §3.6). (3) Pipeline `scripts/auditor/` (coleta read-only →
leitura dos comprovantes por visão → batimento → relatório por e-mail), com memória SQLite
idempotente por (entidade, SHA-256). (4) Skills locais `financeiro-auditor` (rodada) e
`financeiro` (analista sob demanda) — `.claude/` é gitignored, vivem na máquina do auditor.

**Decisões.** Cachê/comissão/recorrente/BV não têm campo de anexo — ficam listados como
"não auditáveis" (decisão de produto; reavaliar depois). Job roda na máquina local via
scheduled task do Claude Code, não como cron do Railway (visão pela API teria custo). Store
local em vez de tabela nova: ERP intocado.

**Pegadinhas.** `recurring_expense_entries.paid_at` é **DATE**, não timestamp.
"Recebido > venda" precisa comparar contra venda + `transport_value` + `acrescimo_value`
(cobrados nos mesmos comprovantes, fora de `sale_value`) e tolerar ~1% (juros de
parcelamento) — sem isso, 3 falsos positivos e casos reais escondidos no meio (ex.: evento
186 com R$ 160.550,00 digitado no lugar de R$ 1.605,50). Anomalias de varredura all-time
precisam de supressão por `entity_uid` no store, senão repetem todo relatório.

### 220b — Hotfix: menu "Ferramentas" do evento embaçado no meio
`main` · **2026-08-06** · sem migration

**Sintoma.** No detalhe do evento, o menu "⋯ Ferramentas" abria com uma faixa horizontal no meio
embaçada/apagada, como se o menu estivesse partido em dois pedaços.

**Causa.** Empate de `z-index`. O painel do `KebabMenu` era `z-20` — o mesmo degrau da régua de
abas (`sticky top-14 z-20` em `EventDetailPage`). Empate de z-index se decide por **ordem no
DOM**, e a régua vem depois do cabeçalho, então ela ganhava. Como a régua tem
`backdrop-blur(8px)` + `bg-surface/95`, os 62px do menu que caíam atrás dela apareciam
embaçados — não era um menu quebrado, era um menu **coberto**.

**Medição (antes/depois).** `elementFromPoint` no centro da faixa devolvia a régua; depois do
ajuste devolve o próprio item de menu, e nenhum dos 10 itens fica coberto por outro elemento.

**Correção.** Painel do `KebabMenu` sobe para `z-30` — a camada de popover que o `Combobox` de
`@manto/ui` já usava. Vocabulário de camadas do app, para não regredir: conteúdo `auto` <
cromo fixo de página `z-20` < **popover `z-30`** < topbar/sidebar do app `z-30/z-40` < diálogo
`z-40` (véu) / `z-50` (conteúdo).

**Pegadinha.** Comentário `//` solto entre atributos de JSX é erro de sintaxe; por isso a classe
virou constante nomeada com o comentário acima dela — que é onde a regra de camada é procurada.

### 220 — Formulários×clientes×eventos: vínculo endurecido, fila de revisão e histórico da cliente
`main` · **2026-08-06** · sem migration (correção de dados direto na produção, com dump prévio)

**Motivação.** Um formulário apareceu vinculado ao evento errado, e a auditoria completa da base
(1.495 respostas) explicou o porquê. A heurística nível 3 da feature 126 — "sem evento na data
informada, mas o telefone tem exatamente 1 evento futuro → vincula" — ignorava a data que a
cliente escreveu: **25 formulários históricos de 2023–2025 (importados na 193) foram grudados em
eventos de 2026 das mesmas clientes recorrentes**. Além disso, 88% das respostas não tinham evento
(a agenda só existe desde 02/01/2026), e mesmo respostas com cliente E evento não apareciam na
ficha da cliente, porque **nenhum caminho de vínculo criava a linha em `event_clients`**.

**Correção de dados (produção, 06/08 ~15h).** Script SQL transacional, ensaiado na cópia local:
(A) desfez os 25 vínculos `auto_client`/`auto_date` com divergência resposta×evento > 30 dias,
marcando `event_link_locked` (a automação nunca religa) e `event_link_ambiguous` (aparece na fila
de revisão); datas com ano < 2000 ficaram de fora do critério (lixo de digitação, ex. `0006-08-22`
com vínculo correto). (B) criou 20 associações `event_clients` em 18 eventos que tinham resposta
com cliente mas nenhum cliente associado — mais recente vira `Contratante`, demais `Outros`.
(C) restaurou o denormalizado `calendar_events.client_id` nesses 18. Rollback disponível:
`backups/manto_2026-08-06_1449.dump`.

**Backend.**
- `_attempt_auto_link` (formularios/routes.py) reescrito: vincula **só com data+telefone
  confirmados** — evento real na data informada cujo cliente associado tem o telefone da resposta.
  Evento na data sem confirmação → `ambiguous` (fila de revisão). Sem evento na data → nada.
  A heurística de "evento futuro" morreu; `auto_client` não é mais gerado (linhas antigas seguem
  válidas para leitura).
- `formularios_ops.ensure_event_client` (novo): todo vínculo com cliente conhecido garante a linha
  em `event_clients` (primeiro = Contratante + denormalizado; demais = Outros). Chamado por
  `link_event`, `associate_client` (quando a resposta já tem evento) e implícito no fluxo de criar
  evento a partir da resposta (que agora também marca `manual` + `locked` — antes deixava o
  vínculo "anônimo" e religável).
- `formularios_ops.count_status`/`STATUS_FILTERS` + `list_responses(filtro=)`: contadores e filtro
  server-side (`sem_evento`, `sem_cliente`, `ambiguos`, `futuros_sem_evento` — este ordenado por
  urgência).
- `client_ops.list_client_form_history` (novo): festas registradas em formulário por cliente —
  decisão de produto: **histórico pré-2026 vem dos formulários; eventos passados NÃO são
  materializados na agenda**.
- `client_ops.client_metrics` (novo): novos clientes por mês (12m, origem agregada; Kommo usa
  `kommo_created_at`, senão a carga viraria pico falso) + recorrentes (2+ eventos).

**Endpoints.** `GET /api/formularios/respostas` ganhou `?filtro=` e devolve `counts` junto (uma
chamada só); `GET /api/clientes/<id>` ganhou `form_history`; novo `GET /api/clientes/metricas`.

**Frontend (apps/internal).** FormulariosAdminPage: 5 cartões-filtro clicáveis no topo, linha
vermelha (`bg-red-50`) e badge `⚠ Sem evento — festa dd/mm/aaaa` para festa futura sem evento,
badge de origem `auto`/`manual`, badge `Revisar vínculo` nos ambíguos. ClientDetailPage: card
"Festas anteriores (formulários)" com marcação "na agenda"/"só formulário". ClientsListPage: KPIs
(novos este mês, com evento, recorrentes) + barras de novos por mês.

**Riscos e pegadinhas.**
- O primeiro ciclo do `retry_auto_link_pending` pós-deploy vai reprocessar ~1.300 respostas sem
  evento e marcar `event_link_ambiguous` nas ~130 que têm evento na data sem telefone confirmado —
  é o comportamento desejado (fila de revisão), não um bug.
- `formatDate` do ClientDetailPage formatava com `new Date(iso)`: data-só (`event_date`) desloca
  um dia no fuso de São Paulo. Agora fatia a string. Mesma armadilha da 210/`relatorio_horarios`.
- Kommo trouxe milhares de clientes de nome genérico ("Fernanda" ×34, "." ×41) — duplicata de
  verdade se detecta por CPF/e-mail (8 pares por CPF, 18 por e-mail na auditoria), não por nome.
  Ferramenta de mesclagem ficou para uma próxima feature.
- Verificação: `scripts/db/verify_220_vinculos_formularios.py` (15 checagens, roda contra
  `manto_local`).

### 219 — Email errado do talento: confirmação no cadastro e fila de devoluções
`main` · **2026-08-06** · migrations `b4c81ef07d29` (email_bounces) e `c5d92fa16e34` (confirmação)

**Motivação.** Gente se cadastra com o email errado (ou com a caixa lotada) e **o sistema nunca
fica sabendo**: a falha existe apenas como um aviso do Mail Delivery Subsystem na caixa de quem
enviou. O talento some do radar sem ninguém perceber, e a descoberta só acontece quando um convite
volta — se alguém reparar.

**Achado que desenhou a solução.** Uma varredura das devoluções reais da conta encontrou 48
mensagens e 13 endereços distintos. Os códigos estendidos (RFC 3463) separam dois problemas que
pedem ações opostas: **`4.2.2`/`5.2.2` caixa cheia** (23) — "avisa no WhatsApp para liberar
espaço" — contra **`5.1.1` usuário inexistente** (8) e **`5.1.2` domínio inexistente** (5) — "o
cadastro está furado, pega o email certo". Um dos endereços é `gabriella.baleeiro@hotmail.con`:
`.con`, não `.com`. Nenhum validador de formato pega isso, porque é um email sintaticamente
perfeito.

**Parte 1 — fila de devoluções (`EmailBounce`).**

`app/integracoes/imap_client.py` lê a caixa por IMAP com a **mesma App Password que o envio já
usa** — sem credencial nova e sem escopo OAuth novo, o que foi decisivo para a viabilidade. A
leitura é estritamente passiva: `EXAMINE` (não `SELECT`) e `BODY.PEEK[]`, então nada é marcado como
lido, movido ou apagado.

`app/talents/bounce_ops.py` interpreta o bloco `message/delivery-status`, classifica pelo código e
casa o destinatário com `Talent`/`User`. **Devolução de endereço desconhecido é descartada de
propósito**: a caixa é a pessoal de quem opera a conta, e guardar contato alheio seria coleta que
ninguém pediu. O total ignorado volta no resultado da varredura para a decisão não ficar invisível
(17 na primeira execução).

Idempotência pelo `Message-Id` único — reler a caixa não duplica (confirmado: 2ª varredura,
`novas=0`). Uma mensagem que reporta N destinatários vira N linhas com sufixo `#índice`, sem perder
a trava. A fila é **agrupada por endereço** na leitura: caixa cheia gera um aviso por tentativa, e
o casting precisa de uma linha por pessoa com o contador de falhas.

A varredura roda em thread (30 min) com **claim atômico** em `import_state` — obrigatório, não
opcional: o Railway roda vários workers gunicorn e cada um abriria a própria conexão IMAP.
Desligada por padrão em ambiente local (`EMAIL_BOUNCE_SWEEP_ENABLED` segue `_suppress_mail`), senão
um processo de desenvolvimento apontado para o espelho leria a caixa real.

**Parte 2 — confirmação do email no cadastro público.**

A confirmação acontece **depois do envio**, com o `Talent` já gravado. Isso não é detalhe: o
formulário tem dados, medidas, PIX, duas fotos e um documento — condicionar a gravação a uma caixa
que talvez nem exista trocaria um problema por outro pior. Na tela de sucesso a pessoa relê o
endereço, corrige **só ele** e reenvia; nada mais é reenviado nem revalidado.

O `email_verify_token` faz dois papéis de propósito: é o link que confirma **e** a credencial da
tela de sucesso para corrigir/reenviar. Confirmar zera o token, o que fecha os dois caminhos de uma
vez — verificado: depois de confirmado, a correção pelo token devolve 404.

As duas partes se reforçam: antes, o primeiro email para um talento novo só saía no convite de um
evento, semanas depois. Agora todo cadastro dispara um email na hora, e quando ele volta a fila
avisa em minutos.

Corrigir o email na ficha (ou pela tela de sucesso) **tira o endereço antigo da fila sozinho** —
`bounce_ops.clear_for_email` roda dentro de `update_talent_fields`, sem commit próprio, para não
gravar estado parcial no meio da edição.

**Riscos e pegadinhas.**
- `useMutation` disparada por `useEffect` no carregamento da página **trava em "pending"** com o
  double-mount do StrictMode: a chamada da primeira montagem resolve contra um observer já
  descartado, e o `useRef` de trava não salva. A confirmação virou `useQuery` (`enabled`, `retry:
  false`, `staleTime: Infinity`), que desduplica pela chave e sobrevive ao remonte. O verbo segue
  POST — confirmar consome o token, não é leitura idempotente. **Regra geral: efeito no load é
  query, não mutation.**
- `_salary_for_month` do 218 tem um irmão aqui: `pending_queue` ordena por definitivo-primeiro e
  recente-primeiro, direções opostas que **não cabem numa chave composta**. São dois `sorted`
  encadeados, apoiados na estabilidade do sort do Python.
- O palpite de domínio (`Você quis dizer gmail.com?`) existe nos **dois lados** — `verify_ops` e
  `lib/cadastro.ts`. É duplicação consciente: o backend precisa dela para o log/diagnóstico e o
  frontend para avisar antes do envio, e um import cruzado entre Python e TS não existe.
- Nunca bloquear envio por formato de email: `hotmail.con` passa em qualquer regex, e regex
  apertada rejeita endereço válido de gente real. Quem separa certo de errado é a confirmação — e,
  quando ela falha, a fila.

### 218 — Superadmin corrige/exclui faixa de salário; Usuários com filtros; telas desempilhadas
`main` · **2026-08-06** · sem migration

**Motivação.** Um salário foi digitado errado e registrado. O caminho existente — registrar um
salário novo por cima — corrige dali para a frente, mas **deixa a faixa errada no histórico e o
valor errado na planilha de pagamentos**: `_ensure_salary_payments` só recria os lançamentos
`nao_pago` **sem adiantamento**, então qualquer lançamento já pago ou com adiantamento fica
congelado no valor errado, para sempre, sem tela que o conserte. Junto vieram dois pedidos de UX:
a tela de Usuários "bagunçada, sem organização nem filtro", e várias telas empilhando tudo numa
coluna estreita num monitor largo.

**O que mudou — salário.**

`user_ops` ganhou três funções e uma passou a ser fonte única: **`_rechain_salary_history`**
recalcula os `end_date` de toda a cadeia (cada faixa termina onde a seguinte começa; a última fica
vigente), desempatando por `id` quando duas faixas compartilham a mesma `start_date` — que é
exatamente o caso de "errei e regravei no mesmo dia". `add_salary`, `update_salary` e
`delete_salary` chamam a mesma função, então nenhuma delas pode deixar duas faixas vigentes.

**`_resync_salary_payments`** realinha a planilha. Regra: lançamento `nao_pago` tem `amount` e
`salary_history_id` recalculados; lançamento **já pago / "no banco" só tem a FK reatada** — o valor
é registro do que saiu do caixa e não se reescreve. Os registros são atualizados **no lugar**,
nunca recriados, e é isso que preserva os adiantamentos (`SalaryAdvance`) — a regeneração do
`_ensure_salary_payments` os preservava se abstendo de tocar no registro, o que era justamente a
causa do valor congelado.

**Decisão não óbvia:** `_salary_for_month` resolve a faixa **por mês** (a de maior `start_date`
ativa no mês), espelhando `app/financeiro/routes.py::_ensure_salary_payments` em vez de resolver
por data de vencimento — que seria mais preciso. Se as duas regras divergissem, o próximo
carregamento da tela de Pagamentos desfaria o realinhamento.

Antes de excluir uma faixa, as referências em `salary_payments.salary_history_id` são zeradas: os
lançamentos já pagos apontam para ela e a FK barraria o `DELETE`. O `_resync` reata cada uma logo
em seguida.

**Endpoints novos (SUPERADMIN, não FINANCEIRO).** `PATCH` e `DELETE` em
`/api/admin/users/<uid>/salary/<sid>`, ambos devolvendo `payments_resynced` — a UI usa esse número
para dizer quantos lançamentos em aberto mudaram. Registrar salário continua SUPERADMIN **ou**
FINANCEIRO; **corrigir o passado** é só SUPERADMIN.

**O que mudou — telas.**

`/admin/usuarios` foi reescrita: busca por nome/email, três filtros combináveis (papel, situação,
frequência de pagamento) via `FilterDropdown`/`CheckboxList`, ordenação, quatro contadores e uma
**tabela** em vez de cards empilhados, com colunas caindo por breakpoint (papéis em `md`,
frequência em `lg`, PIX em `xl`). Os filtros de situação se somam como **E** ("ativo + sem PIX"
funciona como se lê); os de papel e frequência somam como **OU** dentro da própria categoria.

A "Folha do mês" replica a cadência do gerador de pagamentos (semanal × segundas-feiras do mês,
quinzenal × 2) e diz isso na própria legenda — não é uma média inventada.

Onze telas saíram de `max-w-lg/xl/2xl/3xl` em coluna única para largura de desktop com blocos lado
a lado (ficha e criação de usuário, configurações, logs — que viraram tabela —, desempenho,
clientes e ficha do cliente, revisão e espaço de revisão, catálogo admin e seu formulário, ficha de
figurino, configuração de preços). Formulário de evento **não** foi mexido: os blocos já usam
`sm:grid-cols-2` internamente e 3xl é largura correta para formulário longo.

**Riscos e pegadinhas.**
- Item de grid nasce com `min-width: auto`. Ao colocar as tabelas de preço dentro de um grid, o
  `overflow-x-auto` do `Table` parou de agir e a página estourou 14px no celular. Todo grid novo
  leva `[&>*]:min-w-0` — se aparecer rolagem horizontal numa tela nova, é esse o suspeito.
- `add_salary` agora também roda o `_resync`: registrar um salário novo passa a **corrigir** os
  lançamentos em aberto do mês, inclusive os que têm adiantamento. É mudança de comportamento
  silenciosa em relação ao que existia, e é a metade da correção que o usuário percebe primeiro.

**Achado de brinde — a planilha mostrava toda data um dia antes.** Investigando "o valor está
errado" apareceu que o vencimento também estava: a tela exibia **04/08** para um quinzenal que vence
em **05/08**, e segunda-feira de salário semanal caía num domingo. Causa: `new Date("2026-08-05")`
— data **pura**, sem hora — é interpretada como **UTC** pela especificação, e em São Paulo (UTC−3)
volta 21h do dia anterior. O comentário de `packages/ui/src/lib/date.ts` afirmava o contrário, o que
é verdade só para `"2026-08-05T20:00:00"`. `parse` passou a montar a data pura campo a campo em
horário local, e `PagamentosPage` (que tinha cópia própria de `formatDate`) passou a usar
`formatShortDate` da fonte única. **Qualquer tela que formate campo `date` puro estava errada pelo
mesmo motivo** — corrigir na fonte única conserta todas de uma vez. Ver também feature 210.

### 217 — Tema escuro com switch na sidebar, e reestruturação da documentação
`main` · **2026-08-06** · sem migration

**Motivação.** Duas frentes pedidas juntas. (1) Tema escuro "com as cores bem vivas" — fundo quase
preto com os acentos **saturados** por cima, não um cinza lavado. (2) Uma varredura de documentação
e clean code com objetivo declarado de **economia de token**: que a próxima pessoa (ou agente) leia
pouco e entenda rápido.

**O que mudou — tema.**

Os 35 tokens eram **hex fixo** em `tailwind-preset.ts`. Viraram **variável CSS** em
`frontend/packages/ui/src/theme.css`, com dois conjuntos de valores e `darkMode: "class"`. Os nomes
dos tokens não mudaram, então **nenhuma tela precisou trocar de classe** — é isso que tornou a
conversão viável em 189 arquivos.

Princípio que guia a paleta escura: sobre fundo escuro a mesma matiz precisa ficar **mais clara e
mais saturada** para continuar legível e parecer viva, e os fundos `soft` deixam de ser pastel claro
e viram **tinta escura da própria matiz**. Daí `accent` sair de `#544596` (claro) para `#a78bfa`
(escuro), e `green-soft` sair de `#d4edda` para `#10331f`.

Dois tokens novos nasceram da conversão: **`on-color`** (tinta sobre preenchimento saturado — no
escuro o acento clareia e o branco reprovaria AA) e **`gold-ink`**. Eles precisam existir também em
`apps/public/tailwind.config.ts`, que **não consome o preset**: o `content` do Tailwind inclui
`packages/ui/src`, então o `Button` do design system referencia o token mesmo no catálogo.

**Decisão da sidebar (não óbvia).** A sidebar é escura nos dois temas. No tema escuro ela
**clareia** (`#1f1a30` → `#2a2438`) em vez de escurecer: o fundo da página é `#121016`, e manter a
sidebar mais escura que a página a faria desaparecer. É o inverso da intuição.

**Animação.** `document.startViewTransition` com revelar **circular a partir do próprio botão** — a
origem sai do retângulo do botão, não do ponteiro, para que a troca por teclado nasça do mesmo
lugar. Sol e lua se cruzam girando, sobrepostos, para não empurrar o rótulo ao lado. 240ms, dentro
da faixa de 150–350ms do Princípio IX. Fallback de crossfade onde não há suporte, e troca
instantânea com `useReducedMotion()`.

**Preferência.** `localStorage` (chave `manto-tema`), com padrão vindo de `prefers-color-scheme` na
primeira visita. Um script **inline no `index.html`** carimba a classe no `<html>` antes do primeiro
paint — sem ele há flash do tema errado a cada carregamento. Escolhido em vez de gravar no `User`
justamente por isso: preferência vinda do servidor implica flash ou fetch bloqueante.

**Riscos e pegadinhas.**
- O Portal do Artista adotou o tema junto (compartilha o preset), e na primeira passada ganhou o
  tema escuro **sem interruptor** — quem tem o sistema no escuro ficaria preso nele. `ThemeSwitch`
  ganhou `tom="claro"` e `compacto` para caber no header claro do portal.
- `MemoriaDeCalculo.tsx` já usava `dark:` sem nenhum config declarar `darkMode`: com o padrão
  `media` do Tailwind essas linhas **já reagiam sozinhas** ao tema do sistema enquanto o resto da
  tela ficava claro. Adotar `darkMode: "class"` neutralizou o bug de brinde.
- `text-white` sobre preenchimento saturado **não** vira token automaticamente: sobre a sidebar,
  sobre foto e sobre o player continua correto nos dois temas. Só vira `on-color` onde o
  preenchimento clareia no escuro.

**O que mudou — documentação.**

`03_HISTORICO_MUTACOES.md` tinha **202 KB (~61k tokens, ~30% de uma janela de 200k)** e nenhum
índice: era preciso ler tudo para achar qualquer coisa. Virou **índice + as 12 entradas mais
recentes** (47 KB); o restante foi para `docs/historico/184-199.md` e `200-207.md`. **Nenhuma
entrada foi perdida** — 43 antes, 43 depois, conjuntos idênticos (o documento é append-only por
contrato).

Três documentos novos: **`00_MAPA_DO_SISTEMA.md`** (a porta de entrada que não existia — onde cada
domínio mora, tabela de papéis, e "qual arquivo ler para cada tipo de tarefa"),
**`04_GUIA_DE_DOMINIOS.md`** (fluxos, invariantes e armadilhas) e **`05_DIVIDA_TECNICA.md`**
(achados priorizados com arquivo:linha).

O achado estrutural mais grave da auditoria está no 05: **o núcleo do domínio de agenda não está em
nenhum `*_ops.py`** — 39 símbolos privados de `app/calendar/routes.py` (3.910 linhas) são importados
por 10 módulos, inclusive pelo próprio `event_ops.py`. Isso inverte a regra do CLAUDE.md e obriga a
carregar ~49k tokens para qualquer tarefa que toque evento.

### 216 — Cachê no portal, prévia de link no WhatsApp, contraste e endurecimento de segurança
`main` · **2026-08-05** · sem migration

**Motivação.** Cinco frentes pedidas de uma vez: (1) um artista relatou que o **valor do cachê não
aparecia** no portal; (2) link de catálogo compartilhado no WhatsApp saía **sem miniatura**; (3) ao
abrir uma avaliação já enviada, não dava para **ver o que tinha sido escrito**; (4) contraste da
agenda difícil de ler; (5) auditoria de segurança (vazamento, ataque, RBAC).

**O que mudou.**

*Cachê (backend + portal).* `_role_summary` (`app/talent_portal/portal_ops.py`) passou a serializar
`cache_value`, `travel_cache`, `cache_total`, `cache_defined` e `payment_status`. Antes o cachê era
enxertado **só** no laço de `history`, então `pending_invites` e `upcoming` saíam da API sem o campo
e a tela os omitia em silêncio — regressão em relação ao portal Jinja, que exibia o valor no convite
(`app/templates/portal/home.html:170`). Novo componente `CacheLine` é a fonte única das três telas;
`PortalConvitesPage`, que não tinha **nenhuma** referência a cachê, ganhou o valor em destaque.

*Prévia de link.* `frontend/server.js` injeta Open Graph no `index.html` da vitrine para página de
produto **e de tema** (`/catalogo/categoria/<slug>`), com miniatura reencodada por
`app/catalogo/og_ops.py` (teto de bytes — arquivo grande faz o WhatsApp entregar o link sem imagem).
A injeção só roda para **crawler de prévia**: visitante humano não ganha nada com meta tag e pagaria
a latência de uma ida ao Flask em cache frio.

*Avaliação.* O Histórico só linkava a avaliação enquanto a janela de edição de 30 dias estivesse
aberta. Depois disso a avaliação continuava existindo, o backend continuava servindo e a tela sabia
se apresentar em modo leitura — mas **nada apontava para lá**. Passou a usar `rated_event_ids` e
mostrar "Ver minha avaliação".

*Contraste e UX mobile.* Correções de razão WCAG nos chips de categoria da agenda e em textos
pequenos (`tailwind-preset.ts` e `apps/portal/tailwind.config.ts`); `text-xs` virou `text-sm` onde
carregava dado operacional. `/fotos-documentos` e `/termos` **não tinham link em lugar nenhum** —
o artista não conseguia enviar foto nem CNH pelo celular; agora saem do Perfil.

**Impacto em RBAC e segurança.**
- `/uploads/<path>` servia a árvore inteira só com `@login_required`: contrato, comprovante, nota
  fiscal e RG/CNH eram baixáveis por qualquer papel. Passou a despachar por subpasta com papel
  próprio; `expenses` é checado por **dono**, porque qualquer colaborador registra gasto.
- `/portal/photo/<path>` dava a qualquer talento logado alcance a todo o `UPLOAD_FOLDER`. Restrito
  às subpastas que o portal realmente usa.
- `GET /api/talents/<id>` devolvia CPF, RG, PIX e CNH a qualquer autenticado. Campos sensíveis
  passaram a ser redigidos por padrão (`include_sensitive=False`), preservando o shape do payload.
- Upload sem allowlist de extensão (XSS armazenado no mesmo origin): allowlists por finalidade em
  `app/storage.py`; o que não é seguro inline sai como anexo com `nosniff`.
- **Trava de e-mail por ambiente** (`MAIL_SUPPRESS_SEND`): a única trava era uma `SiteSetting`, que
  mora no banco — o espelho local herda ela ligada da produção e um processo de desenvolvimento
  conseguia escrever para o endereço real dos artistas. Confirmado na prática nesta rodada.

**Riscos e pegadinhas.**
- `.xml` de nota fiscal quase foi recusado: a allowlist inicial era imagem + PDF, mas quatro telas
  oferecem `.xml`. Existe `ALLOWED_INVOICE_EXTENSIONS` separada — e `.xml` **nunca** é inline.
- `.svg` saiu do logo: com `nosniff` + `Content-Disposition: attachment` o navegador se recusa a
  desenhá-lo; aceitá-lo produziria um logo invisível.
- A `og:image` **não pôde ser verificada localmente**: nenhuma das 458 capas ativas existe em
  `instance/uploads/catalog_photos` (o espelho do banco referencia arquivos que não foram baixados).
  O encoder foi verificado isolado (JPEG de 193 KB, dentro do teto). **Conferir em produção.**
- Ao criar fixture de teste local, não invente `character_name`: o sync do Google Calendar reconcilia
  o casting e **apaga** escalação com personagem inexistente — disparando e-mail de cancelamento.

### 215 — Tela de evento em abas, com edição inline e buscas visuais
`main` · **2026-08-05** · sem migration

**Motivação.** A tela `/events/:id` da feature 190 entrega **todos** os blocos de uma vez. Para o
`SUPERADMIN`, que recebe o payload inteiro, isso são **16 painéis** empilhados em duas colunas sem
hierarquia — e no mobile uma coluna só, interminável. Três defeitos concretos: (1) o mesmo
personagem aparece **duas vezes** (uma no *Casting*, outra no *Figurino*), dobrando a altura;
(2) nada na tela responde "o que falta neste evento?"; (3) para mudar título, data ou valor era
preciso **sair** para `/events/:id/edit` — uma tela que nem existia antes da migração React e que
edita exatamente o que a tela de detalhe já mostra.

**O que mudou.**

*Frontend.* `EventDetailPage` virou um **shell de abas** — Resumo · Produção · Comercial ·
Histórico — com a aba ativa na querystring (`?aba=`), régua sticky e rolagem horizontal no mobile.
A aba só é montada se o payload trouxe algum bloco dela, então o RBAC continua sendo do servidor.
Novos: `ResumoSection` (painel *Dados do evento* editável + `PendenciasStrip`), `TalentPicker` e
`FigurinoPicker`. `ComercialSection` ganhou os painéis *Clientes* e *Pré-contrato* e edição inline
dos valores. `CastingSection` trocou o `<select>` de talentos pelo `TalentPicker`;
`FigurinoSection` trocou o `<datalist>` pelo `FigurinoPicker`. O botão "Editar" saiu da barra do
cabeçalho e virou o item **"Editar tudo (formulário completo)"** no menu Ferramentas.
`ComboboxOption` (design system) ganhou o campo opcional `badge`, renderizado à direita da opção.

*Backend.* Cinco endpoints novos em `agenda.py`/`agenda_write.py`, com núcleo em `event_ops.py`
(`update_event_basics`, `update_event_comercial`, `set_event_clients`, `set_event_form_response`,
`assignable_talents_for_event`). `_serialize_talent` passou a incluir `photo_url`.

**Regras de negócio e RBAC.** Os quatro endpoints de escrita usam `_can_create_event()` — o mesmo
gate do `PATCH /api/events/<id>` (`COMERCIAL`/`SUPERADMIN`), porque cobrem os mesmos campos
sensíveis; mudar a data de um evento tem o peso de criá-lo. Nenhum gate foi afrouxado: quem já não
podia editar em bloco continua sem editar inline, com os painéis em leitura. `casting-options` é
leitura para qualquer autenticado, igual a `/api/talents`. `update_event_basics` mantém a
sincronização best-effort com o Google Agenda de `update_event_core` (falha vira aviso, não
bloqueio). Cortesia/permuta continua zerando a venda no servidor.

**Rotas e endpoints novos.**
- `GET /api/events/<id>/casting-options` — talentos ativos com `photo_url` e `availability`
  calculada contra a janela **deste** evento (uma consulta para todos, via `talent_availability`).
- `PATCH /api/events/<id>/basico` — título, tipo, data/horário, local, descrição.
- `PATCH /api/events/<id>/comercial` — valores, pagamento, vendedor, comissão.
- `PUT /api/events/<id>/clients` — substitui a lista (corpo é a lista inteira; `[]` desvincula).
- `PATCH /api/events/<id>/form-response` — vincula/desvincula o pré-contrato (409 se preso a
  outro evento — nunca roubamos o pré-contrato de outra venda).

**Riscos e pegadinhas.**
1. **Isolamento é a razão de existirem endpoints estreitos.** O `PATCH /api/events/<id>` da 184
   reescreve elenco e clientes junto: usá-lo para salvar só o horário destruiria escalas. Por isso
   cada função nova toca apenas o seu recorte — e o `verify_215` testa exatamente isso (elenco e
   clientes intactos depois de salvar cabeçalho e valores).
2. **Descrição é HTML do Google Agenda.** O textarea do Resumo mostra a versão em texto puro
   (`descriptionToText`), mas enviar essa conversão de volta achataria `<br>` e âncoras — e o
   achatamento iria para o Google no próximo sync. O formulário só manda o texto digitado se o
   usuário **realmente tocou** no campo; e `PATCH /basico` trata `description` **ausente** como
   "não mexa". Mesma armadilha que o hotfix 210 já tinha documentado para `/events/:id/edit`.
3. **Data/hora continuam sendo horário de parede.** O formulário inline usa `dataDeIsoLocal` /
   `horaDeIsoLocal` (recorte de string), nunca `Date` — o caminho que na 210 gravava +3h.
4. `?aba=` inexistente (link antigo, ou papel sem aquele bloco) cai no Resumo em vez de renderizar
   tela vazia. A troca de aba usa `replace` e **preserva os demais parâmetros** da URL.
5. `casting-options` tem chave por evento e sem `staleTime`: escalar alguém muda a agenda dos
   outros, e salvar data/hora invalida a lista (a disponibilidade é relativa à janela).

**Aviso de teto de cachê (mesma feature).** `EventRole.cache_cap` é gravado na criação quando o
evento vem da calculadora (`routes.py::_create_roles_from_input`, `cache_cap=cache_val if
from_orc`), e `assign_casting_role` **rebaixa** ao teto qualquer cachê maior salvo por não-
superadmin. O campo era serializado desde a 190 mas **nenhuma tela React o usava**: quem digitava
acima via "✓ Salvo" e o número voltava sozinho, sem explicação (a tela Jinja avisava; a migração
perdeu isso). Agora o card mostra o aviso — **sem nunca exibir o valor do teto**, por decisão de
produto — e reespelha o `cache_value` da resposta, para a tela não continuar exibindo o número
recusado. Só ~20% dos cargos têm cap (266/1353 no banco local): evento criado à mão não tem teto,
e aí nada muda.

**Verificação.** `scripts/db/verify_215_evento_abas_edicao_inline.py` contra `manto_local` —
49/49, incluindo o isolamento dos recortes, o 403 do casting no cabeçalho, o 409 do pré-contrato
alheio, a hora de parede preservada, o `conflict` aparecendo na busca de talento e o contrato do
teto (casting salvando 500 sobre cap 200 recebe 200 de volta na resposta e no banco; superadmin
ultrapassa).

### 214 — Hotfix: Revendedor EducaManto sem acesso a nada (calculadora incluída)
`main` · **2026-08-05** · sem migration

**Motivação.** Os dois usuários com o papel `REVENDEDOR_EDUCAMANTO` não conseguiam usar a
calculadora para vender. Na verdade **nada** funcionava para eles: até `/api/auth/me` falhava.

**Causa.** O `_revendedor_guard` (feature 078) roda em `before_request` e redireciona para
`/agenda` tudo que não estiver na allowlist de páginas — e `/api` nunca esteve nela, porque na
época o perfil só usava telas Jinja. Com a 206 tornando o React a interface primária, **toda**
chamada da SPA passou a levar 302. E o sintoma é mudo: o navegador segue o redirect, o servidor do
frontend responde `/agenda` com o `index.html` (status 200), e o `apiFetch` morre no `JSON.parse`
sem mensagem. Reproduzido com usuário real: 302 → `/agenda` em `auth/me`, `educamanto/packages`,
`educamanto/historico`, `agenda` e `educamanto/calcular`.

**O que mudou.** O guard passou a tratar `/api/*` separado: libera `/api/auth`, `/api/agenda`,
`/api/events` e `/api/educamanto` — o **espelho exato** das páginas que o perfil já podia abrir,
sem ampliar nada — e devolve **403 JSON** no resto, em vez de redirect. A allowlist de páginas
continua igual para as superfícies Jinja restantes.

No React, o revendedor passou a **entrar direto na Agenda**: a Home não é do perfil dele e o
servidor recusa os dados dela. Vale no login e em quem chega a `/` por favorito (`rotaInicial()` e
o componente de rota `HomeOuAgenda`, ambos apoiados em `isRevendedorOnly` no `useAuth`).

**Pegadinha.** Guard de navegação que responde **redirect** não serve para API: o cliente JSON
recebe HTML com 200 e falha em silêncio. Sempre que um `before_request` puder alcançar `/api/*`,
a resposta tem de ser status de erro com corpo JSON. Mesma família dos gaps de proxy da 206 —
o denominador comum é "HTML com 200 chegando onde se esperava JSON".

**Verificação.** `verify_214` 14/14 contra `manto_local`: as quatro rotas do perfil respondem 200
em JSON; a calculadora calcula de verdade (pacote real, 2 dias, transporte de 120 km); quatro
rotas fora do perfil devolvem 403 JSON (não 302); multi-perfil (revendedor + comercial) segue sem
restrição; e página Jinja fora do perfil continua redirecionando. Na tela, login do revendedor
cai em `/agenda`, o menu mostra só Agenda/EducaManto/Histórico e a calculadora devolve os valores
com a comissão.

### 213 — Acervo 3D: superadmin exclui peça já usada, desvinculando de todos os eventos
`main` · **2026-08-05** · sem migration

**Motivação.** Peça do Acervo já usada em evento não podia ser excluída de jeito nenhum — a
única saída era inativar. O dono do sistema precisa poder apagar de vez (peça duplicada,
cadastrada errada, arquivo trocado), assumindo que o presente some dos eventos.

**O que mudou.** `DELETE /api/3d/acervo/<id>` aceita `?force=true`: apaga os `Event3DGift`
daquela peça antes de removê-la. O padrão **não mudou** — sem `force`, peça em uso continua
recusada com a orientação de inativar, para o Artista 3D não apagar histórico sem querer. O
`force` exige **SUPERADMIN** (o gate normal do módulo, `require_3d_access`, também aceita
`ARTISTA_3D`, então há uma checagem extra no endpoint).

`delete_acervo_item(item, *, force=False)` faz a cascata explicitamente: nada no banco apagaria
os presentes sozinho (`Event3DGift.item_id` não tem `ondelete`), e é justamente por isso que a
exclusão era barrada. O `AuditLog` grava **de quantos eventos a peça foi desvinculada** — depois
não há como reconstruir.

**UX.** A confirmação virou uma caixa de seleção própria ("Excluir mesmo assim, removendo o
presente de todos os N evento(s) e da Fila de Impressão. Não dá para desfazer"), e o botão fica
**desabilitado** até ela ser marcada; o rótulo muda para "Excluir e desvincular". Não é um segundo
clique no mesmo botão de propósito — exclusão em cascata não pode acontecer por engano. Quem não
é superadmin continua vendo só a orientação de inativar.

**Riscos e pegadinhas.** O presente some da tela do evento **e** da Fila de Impressão, então o
hook invalida as duas caches. Nada mais no banco referencia `Event3DGift`, então não sobra órfão.
Verificação: `verify_213` 17/17 contra `manto_local` (peça sem uso segue simples; peça em uso
recusada sem `force` para os dois papéis; `force` do Artista 3D → 403 sem apagar nada; `force` do
superadmin → 204 com presentes removidos e auditoria contando os vínculos) e o fluxo completo
exercitado no navegador (checkbox habilita o botão, requisição sai com `?force=true`, peça some da
lista e o presente some do evento).

### 212 — Hotfix: diálogos abrindo pela metade, fora da tela
`main` · **2026-08-05** · sem migration

**Motivação.** "Em diversas páginas o pop-up fica pela metade e não consigo mexer": o diálogo
abria com o topo no meio da tela e a metade de baixo para fora, sem rolagem que alcançasse o
resto. Atingia **11 telas** — todas as que usam o `Dialog` do design system (Novo post de
marketing, detalhe de resposta de formulário, memória de cálculo do orçamento, gastos
recorrentes, fila e acervo 3D, comissões, histórico EducaManto, cabeçalho do evento…).

**Causa.** O painel do `DialogContent` era centralizado por `left-1/2 top-1/2` +
`-translate-x-1/2 -translate-y-1/2` (Tailwind) **e** era um `motion.div` animando `scale`/`y`. O
Framer Motion escreve `transform` no **estilo inline**, que vence as classes utilitárias — a
centralização evaporava e sobrava só `left: 50%; top: 50%`, ou seja, o **canto superior esquerdo**
do diálogo no centro da tela. Confirmado no DOM: `transform: translateY(8px) scale(0.96)`.

**O que mudou.** Centralização por **flex**, não por transform: o `Content` do Radix passou a
viver dentro de `fixed inset-0 overflow-y-auto` > `flex min-h-full items-center justify-center
p-4`. Diálogo curto centraliza; diálogo mais alto que a janela faz o **container rolar** em vez de
vazar pelo rodapé. O Framer Motion continua animando `opacity`/`scale`/`y` — agora o `transform`
serve só à animação, não ao layout. Fechar clicando fora segue funcionando: quem cuida disso é o
`onPointerDownOutside` do `Content` do Radix, não o overlay.

**Pegadinha (vale para todo componente animado).** Não centralize com `translate` de utilitário um
elemento cujo `transform` é animado — a biblioteca de animação sobrescreve. Use flex/grid no
container. O `Modal` de `apps/internal/src/components/Modal.tsx` já fazia certo (flex + `max-h`),
o que explica por que só os `Dialog` quebravam.

**Verificação.** No navegador, contra a cópia de produção: "Nova postagem" (1280×720) topo 57 /
base 679, dentro da tela e centralizado; detalhe de resposta do formulário topo 74 / base 662;
mobile 375×812 dentro das margens; e o caso estrutural — painel de 1099px numa janela de 420px:
o container rola (1177px) com topo **e** rodapé alcançáveis. Typecheck e build limpos nos três
apps.

### 211 — Vitrine: quadro da foto com teto e piso
`main` · **2026-08-05** · sem migration

**Motivação.** Na página do produto, o tamanho da foto mandava no layout inteiro. "Às de Copas"
(retrato alto e de arquivo grande) tomava a tela e **espremia a coluna do texto até virar uma
tira**: título quebrado em duas linhas, tags empilhadas uma por linha e botões virando bolinhas.
"80's Neon", com foto menor, ficava correto. Cada produto abria de um jeito.

**Duas causas, não uma.**

1. **Coluna espremida** — a culpa não era da altura, era da largura. O `grid-cols-[1.1fr_1fr]`
   parece garantir a proporção, mas item de grid nasce com `min-width: auto`: a coluna **não
   encolhe abaixo da largura natural do conteúdo**. Uma foto de arquivo grande empurrava a
   coluna da direita para fora da sua fração. `min-w-0` nas duas colunas devolve o controle ao
   `1.1fr/1fr` (medido depois: 568px / 516px, como esperado).
2. **Quadro sem limites** — a galeria só tinha teto (70vh) e nenhum piso, então retrato alto
   virava parede e paisagem larga virava tira. O palco agora vive numa faixa: piso de 380px,
   teto de `min(62vh, 620px)`. A foto continua inteira (`object-contain`), o que sobra é o fundo
   do quadro.

**Onde a garantia mora.** Teto e piso são **CSS** (`min-height`/`max-height`) no elemento do
palco, não só conta em JavaScript. Assim valem antes de a foto carregar, quando ela falha, e
depois de o usuário redimensionar a janela — a altura calculada no `onLoad` é um pixel fixo que
envelhece, e não havia listener de resize. O cálculo em JS continua, para o quadro já nascer no
tamanho certo em vez de crescer na frente do cliente.

**Pegadinha.** A altura do palco saiu do `animate` do Framer Motion e virou `style` + transição
CSS. Tamanho de quadro precisa valer no primeiro quadro renderizado; entregá-lo à biblioteca de
animação deixava o palco com 24px quando a imagem falhava.

**Verificação.** Typecheck e build limpos nos três apps; proporção das colunas e a faixa aplicada
(`min-height: 380px`, `max-height: 446.4px` numa janela de 720px) conferidas no DOM. A cópia
local não tem os arquivos de mídia (só o banco vem de produção), então a conferência visual com
fotos reais foi feita na página publicada.

### 210d — Hotfix: navegador preso no bundle antigo (e vínculo de ficha mais óbvio)
`main` · **2026-08-05** · sem migration

**Motivação.** Chegou o relato "não dá para vincular ficha depois de criado o personagem", com
print do painel de Personagens sem o botão. O botão **já estava em produção desde a 209** — o
print mostrava a versão da 207 (dava para saber pelo rótulo "sem vídeo", que a 209 removeu).

**Causa raiz — deploy que não chega no usuário.** O `serve-handler` não manda `Cache-Control`
nenhum. Sem esse cabeçalho, o navegador aplica **cache heurístico** em cima do `Last-Modified` e
guarda o `index.html` — que é justamente quem aponta para o bundle com hash. Resultado: o deploy
sobe, a sondagem em produção passa (o servidor entrega o arquivo novo para quem pede), e mesmo
assim o usuário continua rodando o JavaScript velho até dar refresh forçado. Isso vale para
**todo** deploy do frontend, não só este caso.

`frontend/server.js` passou a declarar o contrato padrão de SPA com assets versionados:
`Cache-Control: no-cache` para HTML (pode guardar, mas **revalida sempre**; o arquivo tem menos
de 1 KB e vira 304 quando nada mudou) e `public, max-age=31536000, immutable` para `assets/*`
(o hash está no nome, então conteúdo novo = URL nova). A regra de `assets` vem depois de
propósito: o `serve-handler` percorre a lista inteira e a última que casar vence.

**UX.** O selo "⚠ Sem ficha vinculada" virou botão — "⚠ Sem ficha vinculada — vincular" — e abre
o mesmo painel do botão "Ficha & página". É onde o olho bate ao procurar o que falta; deixar a
ação só atrás do outro botão dava a impressão de que não dava para vincular depois de criar.

**Riscos e pegadinhas.** "Verifiquei em produção" ≠ "o usuário está com isso": a sondagem busca o
bundle direto, o navegador dele não. Quando um relato descrever uma tela que não bate com o
código, procure um texto que só existe na versão antiga antes de sair caçando bug — foi o "sem
vídeo" que resolveu este. Verificação: `frontend/scripts/verify-proxy.mjs` ganhou a seção "Cache
do navegador" (HTML das 3 SPAs com `no-cache`, asset com `immutable`) — todos os checks OK; e o
vínculo de ficha foi exercitado de ponta a ponta no navegador (vincular pelo selo, gravar,
desvincular pelo ✕).

### 210c — Hotfix: Comercial voltou a enxergar o pagamento do evento
`main` · **2026-08-05** · sem migration

**Motivação.** O Comercial criava o evento e subia o comprovante, mas não via se a cliente já
havia pagado — sumiram o painel "Comprovantes de pagamento" (com o "Recebido X de Y" e o selo
"Quitado ✓") e o de "Reembolsos".

**Causa.** Na API, `data["pagamentos"]` e `data["reembolsos"]` foram colocados no bloco
`show_financeiro` (FINANCEIRO/SUPERADMIN). No Jinja os dois painéis ficavam dentro de
`{% if show_comercial %}` (`event_detail.html` 1982-2196) — quem vende sempre viu. Incoerência
visível: `reembolsos_pendentes_total` já ia para o Comercial, então ele lia "há R$ X pendente"
sem poder ver do que se tratava.

**O que mudou.** As duas chaves passaram para o bloco `show_comercial`. Nada mudou no React: os
painéis já apareciam por presença de chave (o servidor decide), e o `PagamentosPanel` já trazia o
"Recebido/Quitado", a lista e o formulário de novo comprovante.

**RBAC — o que NÃO mudou.** Subir comprovante e registrar/cobrar reembolso sempre foram
`_CAN_EDIT_EVENT` (inclui Comercial) nos endpoints; editar valor e excluir comprovante/reembolso
seguem restritos a SUPERADMIN, checados no endpoint e escondidos no React por
`flags.is_superadmin`. `kpi` e `gastos` (lucro, cachês, despesas) continuam só no bloco
financeiro — foi só isso que sobrou lá.

**Pegadinha.** Ao migrar um bloco do Jinja para a API, o gate tem de ser o do **template**, não o
do "parece financeiro". Verificação: seção 6 do verify_210 (43/43) com usuários de papel puro
(Comercial vê pagamentos e não vê KPI; Comercial sobe comprovante → 201, mas edita/exclui → 403;
Financeiro segue com tudo; Casting segue sem ver venda nem pagamentos) e conferência na tela com
"Ver o sistema como COMERCIAL".

### 210b — Hotfix: buscador de pré-contrato mudo
`main` · **2026-08-05** · sem migration

**Motivação.** O campo "Pré-contrato (formulário recebido)" de `/events/new` e
`/events/:id/edit` não devolvia nada para nenhum termo.

**Causa.** `FormResponsePicker` chamava `${API_BASE}/formularios/respostas/search` — a rota
**Jinja**, fora de `/api`. `frontend/server.js` só repassa ao Flask os prefixos de
`BACKEND_PREFIXES`, e `/formularios` não pode entrar lá: é rota do React Router (a tela de
Formulários). Resultado: a chamada caía no fallback da SPA e recebia o `index.html` **com status
200** — `r.ok` era verdadeiro, o `JSON.parse` estourava e o `.catch(() => setResults([]))`
transformava a falha em lista vazia. Ninguém via erro nenhum.

Antes da 206 isso funcionava porque `VITE_API_BASE_URL` apontava para o domínio do Flask e a
chamada não passava por proxy nenhum. Mesma família dos gaps de proxy da migração — e o único
caso restante: `/figurinos/<id>/print` e `/figurinos/print-event/<id>` já estavam cobertos por
`BACKEND_PATTERNS`, e uma varredura em `apps/*/src` não achou outra chamada fora de `/api`.

**O que mudou.** O componente passou a usar `apiFetch("/api/formularios/respostas/search")` — o
endpoint equivalente já existia em `app/api/formularios_admin_read.py`, sem tela que o usasse. A
lista agora mostra tipo · telefone · data do evento. Estados de **buscando**, **nenhuma resposta
encontrada** e **erro** substituíram o silêncio: a lição do bug é que "lista vazia" e "a chamada
falhou" não podem se parecer.

`formularios_ops.search_responses` ganhou **busca por data do evento** (`dd/mm/aaaa`, `dd/mm/aa`,
`dd-mm-aaaa`, ISO) — o campo prometia "nome, telefone ou data" e só fazia nome e telefone. O
casamento por telefone passou a exigir 4+ dígitos: com data no jogo, um "12" digitado no meio de
`12/08/2026` casava com meio banco de telefones.

**Riscos e pegadinhas.** Ao consumir rota do Flask a partir do React, use **sempre** `/api/*`.
Fora de `/api`, só com entrada explícita no proxy (`server.js` **e** os `vite.config.ts`), e por
regex restrito quando o prefixo colide com rota do React Router. Verificação: seção 5 do
verify_210 (30/30) e os quatro caminhos conferidos no navegador (nome, telefone, data e termo sem
resultado).

### 210 — Hotfix: horário deslocado, anexo do evento e orçamento sem saída
`main` · **2026-08-05** · sem migration

**Motivação.** Três regressões críticas apareceram junto quando a 206 tornou o React a interface
primária — todas em código que já existia, mas que só virou o caminho real dos usuários agora:
horários de eventos "mudando sozinhos", comprovante falhando sempre depois de criar o evento, e a
calculadora de orçamento sem a memória de cálculo nem a tela de apresentação da proposta.

**1. Horário deslocado +3h a cada edição (o mais grave).**
`start_at`/`end_at` são **horário de parede de São Paulo** — o banco guarda naive (ver
`service.py::parse_event_datetime`) e a API serializa com `.isoformat()`, sem fuso. O
`EventEditPage` hidratava o formulário com `new Date(iso).toISOString().slice(...)`: o `Date`
interpretava a string como horário local do navegador e o `toISOString` convertia para UTC,
abrindo todo evento com **+3h**. Salvar gravava o horário deslocado no banco **e empurrava para o
Google Agenda** — por isso os dois "concordavam" no valor errado e não havia divergência para
comparar. Em evento noturno (≥ 21h) a **data** também pulava um dia, e o fim virava madrugada do
dia seguinte pela regra da meia-noite do `_build_start_end`.

Correção em `lib/horaLocal.ts` (`dataDeIsoLocal`, `horaDeIsoLocal`, `hojeYmd`): para preencher
formulário e comparar datas, **recorta a string, nunca passa por `Date`**. `GastosExtrasPage` e
`GastosRecorrentesPage` usavam `new Date().toISOString().slice(0,10)` como "hoje" — depois das 21h
isso já dava o dia seguinte; passaram a usar `hojeYmd()`.

No mesmo `reset()`, `description` era hidratada com `""` enquanto o PATCH manda a descrição
inteira: **toda edição apagava a descrição do evento** (e a do Google Agenda), inclusive os blocos
com dados da contratante. Passou a hidratar `data.event.description`.

**2. Comprovante "sempre falhou" ao criar evento.** A fase 2 do `EventCreatePage` (anexos) usava
`useAddPayment(createdEventId ?? 0)`. `setCreatedEventId` só tem efeito no render seguinte e a fase
2 dispara ainda dentro do `onSuccess` da criação — o hook continuava preso em `0` e o upload ia
para `POST /api/events/0/payments` → 404. Determinístico: o evento nascia certo e **todo** anexo
falhava. "Tentar novamente" funcionava, porque aí o estado já tinha atualizado — o que fazia
parecer instabilidade de rede. Os uploads viraram funções soltas
(`enviarComprovante`/`enviarContrato`/`enviarReembolso`/`enviarObservacaoComFoto`), que recebem o
`eventId` por argumento; os hooks passaram a ser casca fina em volta delas.

**3. Memória de cálculo virou a mensagem de WhatsApp.** O diálogo "Ver memória de cálculo" mostrava
`quote.message`. O painel do Jinja (`orcamento/index.html` + `static/js/orcamento.js`) montava a
memória **no cliente**, duplicando a conta — motivo de ela ter se perdido na migração.
`quote_ops.calculate_quote` agora emite a memória junto com o cálculo (chave `memoria`), linha a
linha e na ordem em que cada parcela entra: cachê por profissional, coordenador, subtotal, markup,
brinde, adicional noturno, técnico, maquiador, transportes, acréscimos, NF e total. A verify prova
que a soma das parcelas fecha com os totais — a memória não pode "explicar" um número diferente do
cobrado. No orçamento personalizado a memória mostra só cachê-base × multiplicador (ou o valor
digitado), porque transporte/NF/acréscimo realmente não entram ali.

**4. "Gerar Orçamento" não levava a lugar nenhum.** Só salvava e o botão virava "Orçamento salvo".
Nova rota `/orcamento/:id` (`OrcamentoResultadoPage`), sucessora de
`app/templates/orcamento/resultado.html`: mensagem de WhatsApp copiável, resumo por duração,
detalhamento do transporte, memória de cálculo, baixar PDF e enviar por e-mail. O histórico ganhou
"Abrir orçamento" apontando para ela. Nenhum endpoint novo — `historico/<id>`, `/pdf` e
`/enviar-email` já existiam sem tela que os usasse.

**Rotas.** React: `/orcamento/:id` (declarada **depois** de `/orcamento/historico` e
`/orcamento/configuracoes`, senão `:id` casaria com elas). Backend: nenhuma nova; `quote.memoria`
é chave nova em `POST /api/orcamento/calcular` e no detalhe do histórico (orçamentos salvos antes
disso não têm a chave — o React trata como "memória não registrada").

**Riscos e pegadinhas.**
- Nenhum `Date` deve tocar em `start_at`/`end_at` para produzir valor de formulário. O bug
  sobreviveu meses porque `new Date(iso)` **exibe** certo para quem está em São Paulo — só quebra
  ao voltar para string via `toISOString()`.
- Os eventos editados enquanto o bug existiu ficaram com o horário deslocado nos dois lados (banco
  e Google), então não há como detectá-los por divergência. `scripts/db/relatorio_horarios_
  deslocados.py` lista os candidatos pelo log "Editou os dados do evento" e sugere o horário
  original, para conferência humana — não corrige nada sozinho.
- Ferramenta nova de desenvolvimento: `scripts/db/run-local-sem-google.py` sobe o Flask contra
  `manto_local` com `insert/update/delete_event` do Google dublados. Sem isso, reproduzir criação
  de evento no navegador cria lixo no calendário de produção.
- Verificação: `verify_210_horario_anexo_orcamento.py` 23/23 contra `manto_local` (round-trip do
  PATCH sem deslocar em evento noturno, descrição preservada, anexo com id real ✕ id 0, memória
  fechando com os totais, PDF e e-mail). Typecheck e build limpos nos três apps.

### 209 — Catálogo como espinha organizacional (página própria + fichas + busca)
`main` · **2026-08-05** · migration `e7a1c94f20b3` (*own_item_id em catalog_characters*)

**Motivação.** O catálogo deixa de ser só vitrine e vira o início da organização: tema com
elenco embaixo (Abba), personagem com ficha de figurino vinculada (métrica de cobertura),
personagem que TAMBÉM tem página própria e buscável (Coelho Branco dentro do tema Alice), e
variação de figurino como personagem separado (Gabby Boneco ✕ Humanizada — decisão do dono:
a Humanizada mantém página vendável na busca).

**Modelo.** `catalog_characters.own_item_id` (FK catalog_items, UNIQUE, SET NULL): o
personagem aponta para o item que É a página dele. Hierarquia de UM nível, de propósito —
tema com elenco não pode virar personagem de outro tema (validação em `set_own_item`/
`adopt_item_as_character`). O relacionamento `CatalogItem.characters` precisou de
`foreign_keys` explícito (dois FKs para a mesma tabela = AmbiguousForeignKeysError no boot).

**O que mudou.**

*Ops/API* — `catalog_character_ops`: `set_own_item`, `toggle_own_page` (checkbox "Página
única" = `is_active` do item vinculado; reversível, nunca apaga), `adopt_item_as_character`
(foto COPIADA da capa via `storage.copy_file`). Endpoints SUPERADMIN:
`POST /api/admin/catalogo/personagens/<id>/pagina-propria`, `.../pagina-unica`,
`POST /api/admin/catalogo/<tema_id>/adotar-item`.

*Vitrine* — `_character_summary` público ganhou `own_item_slug` (só quando a página está
ATIVA): o tile do elenco vira link para a página própria. Detalhe do item ganhou
`parte_de_tema` → selo "✦ Parte do tema Alice" com volta ao elenco. `_item_summary` da
grade ganhou `tags` e a busca client-side passou a incluí-las — "alice" acha o Coelho pela
tag, sem personagens poluindo os resultados.

*Admin* — `FigurinoSheetPicker` novo (busca realtime sem acento + thumb da ficha; fichas
com nome batendo com o personagem sobem ao topo) substitui os DOIS `<select>` cegos (painel
de personagens e vínculo rápido da árvore). Cada personagem ganhou o bloco "Ficha & página"
(picker + controles de página própria). Painel ganhou "Adotar item existente como
personagem". Listagem ganhou o termômetro `characters_com_ficha/characters_total` por tema
+ soma no topo, e o rótulo "página única — elenco de X" nos itens adotados.

**Riscos e pegadinhas.**

1. **Adoção COPIA a foto da capa** — nunca referencia (`delete_file` é chamado em 5 pontos
   sem saber de compartilhamento; mesmo racional do drag de foto da 207).
2. **Desligar a "página única" usa `is_active` do item** — o mesmo flag do gerenciador.
   Reativar o item pelo gerenciador religa a página do personagem (comportamento desejado:
   um flag só, sem estado paralelo).
3. **manto_local está atrás da produção** (o Abba da assistente não existe na cópia local).
   Rodar `refresh-local-db.ps1` antes do mutirão de organização.
4. Regra de modelagem registrada: versão de TEMA inteiro = temas separados (Alice Desenho ✕
   Live Action); variação de FIGURINO = personagens separados no mesmo tema (Gabby Boneco ✕
   Humanizada), cada um com sua ficha — a métrica de cobertura conta certo sozinha.

### 208 — Restauração do papel ENSAIO (dashboard + agendamento + presença)
`main` · **2026-08-05** · sem migration

**Motivação.** Incidente relatado pela equipe: a home do papel ENSAIO ficou vazia
("Tudo em dia!") após a 206. A auditoria mostrou que o papel perdeu TRÊS capacidades — o
dashboard inteiro (ensaios a agendar/agendados/órfãos + presença pendente), o
**agendamento de ensaios** (create/edit/delete/link eram rotas Jinja sem equivalente
`/api`) e a **atribuição do Técnico de Som (Presença)** (no React a vaga só era editável
por casting; no Jinja era tarefa do ensaio).

**O que mudou.**

*Backend* — `event_ops.py` ganhou o núcleo extraído das rotas Jinja: `create_ensaio`,
`update_ensaio`, `delete_ensaio`, `link_ensaio_to_show`, `assign_tech_presence`,
`build_ensaio_times` (regra da meia-noite preservada) e `resolve_ensaio_location`
(dependências de `routes` importadas só em runtime — sem ciclo de boot). Endpoints novos:
`POST /api/events/<id>/ensaios`, `PATCH/DELETE /api/ensaios/<id>`,
`POST /api/ensaios/<id>/vincular`, `POST /api/events/<id>/presenca` — todos gated por
`_CAN_ENSAIO` (Ensaio/Casting/Superadmin). `dashboard_service.compute_ensaio_tasks` +
seção `ensaio` no `/api/dashboard` (gate: ENSAIO ou superadmin, paridade com a home
Jinja). `serialize_event_detail` expõe `ensaios`, `presenca` e (em eventos ENSAIO)
`ensaio_pai`.

*Frontend* — `EnsaioSection` no detalhe do evento: no SHOW lista/agenda/cancela ensaios e
define a presença (select de talentos); no próprio ENSAIO mostra o pai (ou o estado órfão
com busca de show para vincular — reusa `useAgendaSearch`), edita horário e cancela.
Dashboard ganhou o painel "🎭 Ensaio" com as quatro listas.

**Riscos e pegadinhas.**

1. **A resposta do PATCH/DELETE de ensaio é o detalhe do SHOW pai** (a tela que o painel
   refaz). Na página do próprio ensaio isso corromperia o cache se fosse para
   `setQueryData(["event", ensaioId])` — os hooks da página do ensaio usam
   `invalidateQueries` em vez do write-through padrão.
2. **`verify_208` contra manto_local toca o Google Calendar REAL** (o token vive no banco
   copiado): o ensaio de teste é criado e excluído de verdade. Transitório, mas visível
   por segundos na agenda.
3. **Excluir um show cascateia para os ensaios filhos** — a limpeza de teste precisa
   limpar as tabelas satélite de TODOS os eventos antes de deletar qualquer um.
4. O gate do dashboard é ENSAIO/superadmin (como a home antiga); o gate de ESCRITA é
   `_CAN_ENSAIO` (inclui CASTING). São padrões diferentes de propósito — casting agenda
   ensaio pelo evento, mas não carrega o painel de pendências.
