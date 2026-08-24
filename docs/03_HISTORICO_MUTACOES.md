# 03 — Histórico de Mutações (índice)

> **Documento vivo — APPEND ONLY.** Cada feature concluída adiciona uma entrada **no topo** da
> seção "Registro", e uma linha **no topo** da tabela do índice. Nunca reescrever entradas antigas
> (elas são o histórico); correções entram como nova entrada referenciando a anterior.
>
> Última atualização: **2026-08-24** · Estado do repositório: pós-feature
> **260-etapa-pronto-marketing (em produção, sem migration)** — antes dela
> **259-portal-reset-sem-senha (em produção, sem migration)** — antes dela
> **258-cliente-manual (sem migration)** — antes dela
> **257-hotfix-anexos-persistencia (em produção, sem migration)** — antes dele
> **256-auditor-marketing (em produção, migration `c4d1e7b2a9f3` — head)** — antes dela
> **255-tags-nfc (branch, migrations `a7e2f94c1d58` + `b3f8d27a9e14`)** — antes dela
> **254-melhorias-video-catalogo (em produção, migration `f3a9c15d8b42`)**, antes dela a
> sequência da remoção do Jinja **240–252 (pausada, ver `docs/PARADA_REMOCAO_JINJA.md`)**,
> antes dela **239-backlog-agosto (11 itens)**, catalogo-fase-1, **235-educamanto 4ª rodada**,
> 238, 237, 236 · Head de migration: **`b3f8d27a9e14`** (*cliente direta na tag NFC, feature 255*)
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
| **260-etapa-pronto-marketing** | Nova etapa "Pronto" no funil de marketing: status intermediário entre "Revisão" (material aprovado) e "Agendado", material pronto para ir ao ar e aguardando dia/hora de publicação | 2026-08-24 | `—` | (aqui) | — |
| **259-portal-reset-sem-senha** | "Esqueci minha senha" do Portal do Artista silenciava para quem nunca criou senha (`password_hash` NULL) — `request_password_reset` exigia senha prévia na condição de match; talento clicava, a tela dizia "enviamos o link", e nada era enviado (caso real: talent 139, Iara, e mais 118 talentos ativos no mesmo buraco). Removida a exigência de senha prévia; o link de reset já define a primeira senha | 2026-08-24 | `—` | (aqui) | — |
| **258-cliente-manual** | Botão "Nova cliente" na tela de Clientes: cadastro manual com nome, telefone, e-mail, empresa, CPF, CNPJ e endereço, reusando o endpoint de cadastro rápido (telefone único; repetido avisa e não duplica nem sobrescreve) | 2026-08-21 | `—` | (aqui) | — |
| **257-hotfix-anexos-persistencia** | Anexos do evento sumiam no refresh: os cinco POSTs de anexo (comprovante, contrato, reembolso, nota fiscal, marcar reembolso cobrado) faziam `db.session.add` sem `commit` — quem commitava era o dispatcher do Jinja. Endpoint novo de listagem de arquivos órfãos no volume + script de recuperação | 2026-08-21 | `—` | (aqui) | — |
| **256-auditor-marketing** | Auditor de marketing semanal (Claude Code local, zero API): lê exports CSV da Meta/Google numa pasta, grava histórico no ERP por endpoints do agente, mantém o Gasto Extra de reembolso de anúncios por plataforma × mês civil (pendente, sem comprovante, congela ao aprovar), relatório por e-mail com barras HTML/CSS, tela `/marketing/desempenho` com SVG próprio, link do post no card, utms do Kommo no cliente | 2026-08-21 | `c4d1e7b2a9f3` | (aqui) | — |
| **255-tags-nfc** | Tags NFC nas peças 3D (luminárias): URL pública imutável por unidade física (`/nfc/<code>`, código aleatório + Nº sequencial humano por produto), geração automática pelo presente 3D, vínculo direto a cliente (campanha sem show), página da estrela "Magia de Sonhar" acendendo, tela de gestão sem exclusão | 2026-08-20 | `a7e2f94c1d58`, `b3f8d27a9e14` | (aqui) | — |
| **254-melhorias-video-catalogo** | Anexar vídeo na Revisão para de falhar em silêncio (pré-validação, barra de progresso XHR, 413/500 de `/api` com envelope); sync ganha janela de graça de 5 min (corrida com o criar evento); busca de personagem mostra o produto e não rouba vínculo; criar produto do catálogo aterrissa na edição | 2026-08-20 | `—` | (aqui) | — |
| **250 / 251 / 252** | Régua de comissão extraída para `comissoes_ops` (450 eventos, zero divergência); acréscimos, parcelas e CRUD de nota fiscal na API | 2026-08-20 | `—` | (aqui) | — |
| **248 / 249** | Comissão volta a sincronizar ao editar venda pela API; núcleo das coleções comerciais sai do formulário Jinja (`comercial_ops`) | 2026-08-20 | `—` | (aqui) | — |
| **246 / 247** | Agrupar/desagrupar eventos na plataforma nova (núcleo `group_ops` + endpoints + tela); satélite rejeita venda com 409 + `leader_id` | 2026-08-19 | `—` | (aqui) | — |
| **244 / 245-remocao-jinja-fases-3-e-5** | Onze blueprints Jinja removidos: oito inteiros (rh, clientes, gastos, revisão, orçamento, formulários, admin, talents) e três parciais (catálogo, figurino, feedback), guardando só as rotas de arquivo, as duas de impressão e o redirect do `/avaliar`. −14.364 linhas. Ferramenta nova: detector de `url_for` órfão | 2026-08-19 | `—` | (aqui) | — |
| **242 / 243-remocao-jinja-fase2-e-extracao** | Portal do Artista Jinja removido (−3.230 linhas) e a lógica que a API viva importava de dentro dos `routes.py` tirada para os `*_ops.py` — cinco módulos dependiam disso | 2026-08-19 | `—` | (aqui) | — |
| **241-avaliar-aponta-para-react** | O link de avaliação da cliente para de cair no Jinja: `/avaliar/<token>` vira 302 para a página React (feature 164, ociosa até aqui) e os geradores emitem o endereço novo. A rota antiga fica para sempre — o token não expira | 2026-08-19 | `—` | (aqui) | — |
| **240-remocao-jinja-fase1** | Remoção do Jinja legado, fase 1: 3 templates órfãos, 1 gif órfão, `travel_estimate` (já sem decorator) e `_is_outside_sp`, rotas `/impersonate/*`. −1.043 linhas, zero mudança de comportamento. Plano completo em `docs/PLANO_REMOCAO_JINJA.md` | 2026-08-19 | `—` | (aqui) | — |
| **239-backlog-agosto** | Carrinho de transporte fora de SP com teto efetivo p/ superadmin; "Técnico de Som (Presença)" sem valor e fora de todos os somatórios; troca de tipo do evento reage sozinha (push do título antes da parte destrutiva); nomes de equipe nunca no título; link do orçamento na aba Comercial; badge de maquiador; Catálogo no topo do menu; link do portal na cobrança WhatsApp; EducaManto (InfoTip, contratação Manto) — 11 itens do backlog | 2026-08-18 | `d1c7b93a2f60`, `e2d8ca4b3071` | (aqui) | — |
| **catalogo-fase-1** | Ficha de figurino direto no item AVULSO; 12 auto-temas achatados; selo Tema×Avulso no gerenciador; ação "virar avulso"; avulsos entram na visão de personagens | 2026-08-18 | `c8f4d92e17ab` | (aqui) | — |
| **vincular-na-criacao (hotfix)** | "Vincular a um Personagem do Catálogo" também na CRIAÇÃO da ficha (deferido pós-criação, padrão da foto); só personagens sem ficha; nome preenchido de brinde | 2026-08-17 | `—` | (aqui) | — |
| **fichas-por-escalacao + adotar-item-honesto (hotfixes)** | Imprimir fichas do evento: 1 folha por escalação (dois "Soldado" saíam como um); busca de adotar item mostra tema/já-adotado bloqueado com o motivo em vez de sumir | 2026-08-17 | `—` | (aqui) | — |
| **cadastro-raiz (hotfix)** | `/cadastro` na raiz do domínio vira o endereço do formulário React; Jinja do cadastro apagado; `FileUpload` copia o arquivo para memória (mata `ERR_UPLOAD_FILE_CHANGED`) | 2026-08-17 | `—` | (aqui) | — |
| **235-educamanto (4ª rodada)** | Gate FECHADO: cenário sai das responsabilidades (sem custo, colunas removidas); personagens×produção derivados dos itens (Cara Limpa+Bonecos+Papai Noel / item Produção); textos aprovados. Aguarda só o "push 235" | 2026-08-17 | `b7e3a91d5c24` reescrita | (aqui) | — |
| **238-teto-autorizado** | Valor salvo por superadmin vira teto efetivo do papel (`max(cache_cap, valor salvo)`) — casting consegue usar o valor autorizado | 2026-08-14 | `—` | (aqui) | — |
| **237-solicitar-ficha** | Botão "Solicitar ficha" no FigurinoPicker → pedido kind `ficha` na fila de Produção e Compras; concluir exige vincular a ficha criada | 2026-08-14 | `—` | (aqui) | — |
| **236-cache-por-duracao** | Cachê por duração real (>4h: base÷4×horas + adicionais); cachê nasce vazio, régua vira só teto invisível | 2026-08-14 | `—` | (aqui) | — |
| **235-educamanto (3ª rodada)** | Som/iluminação viram tabela única por combinação (4.200/2.900/2.900/750, técnicos inclusos) em `pricing_config`; riders reais no PDF | 2026-08-14 | `b7e3a91d5c24` reescrita | (aqui) | — |
| **235-educamanto** | EducaManto por responsabilidades: musicais no lugar de pacotes por nível; snapshot v2 recalculado no servidor; Jinja do EducaManto desligado (gate fechado na 4ª rodada — ver entrada de 2026-08-17) | 2026-08-13 | `b7e3a91d5c24` | (aqui) | — |
| **225g** | Fotos já na abertura do pedido (opcionais, várias, nos três tipos); criação virou `multipart`. **Furo conhecido: `.heic` não é comprimido** | 2026-08-12 | `—` | (aqui) | 163 |
| **225f** | Um menu só ("Produção e Compras") para os três tipos de pedido; a aba virou `?tipo=` na URL e `/compras` passou a redirecionar | 2026-08-12 | `—` | (aqui) | 216 |
| **225e** | Hotfix: menu "Ferramentas" cortado atrás da barra lateral — o painel abria para a esquerda e sumia sob a sidebar `z-40`; lado da abertura passou a ser medido | 2026-08-12 | `—` | (aqui) | 248 |
| **225d** | Padding padrão nas 6 telas coladas na sidebar + busca de figurino unificada no `FigurinoPicker` (`FigurinoSheetPicker` apagado) | 2026-08-11 | `—` | (aqui) | 290 |
| **225c** | Pedido de Compra (3º `kind` de `figurino_producoes`, fluxo `comprado → recebido`, sem migration) + "Revisão" movida de Produção para Marketing no menu | 2026-08-11 | `—` | (aqui) | 323 |
| **235** | O mesmo personagem em vários temas (identidade = ficha de figurino), aba Personagens com termômetro de progresso, e quantos figurinos iguais existem por ficha | 2026-08-11 | `f4a8d61c9e27` | (aqui) | 394 |
| **234** | Fotos do catálogo: reordenar e salvar não gravava posição nenhuma; grade refeita (capa = 1ª foto, arraste por ponteiro, `photo_order` com tokens `new:<i>`) | 2026-08-11 | `—` | (aqui) | 454 |
| **233** | Coordenadora sem ver figurino (a 230 deixou o link levando a 403) e convite automático de quem é escalado na criação/edição do evento | 2026-08-11 | `—` | (aqui) | 513 |
| **232** | Avaliação do portal: detalhar por partes volta a ser o caminho padrão (era cartão opcional abaixo da dobra) e `texto` recupera o sentido de "Show no geral" | 2026-08-10 | `—` | (aqui) | 576 |
| **231** | Confirmações pendentes: painel na home do casting (com cobrança no WhatsApp) e lembrete automático por e-mail com teto de 2 por convite e 1 por pessoa/dia | 2026-08-10 | `e3f7c25a8b90` | (aqui) | 632 |
| **230** | Portal segue a escala e não o convite: escalação não recusada passa a aparecer (26 futuros e 97 passados invisíveis, R$ 36.910), totais batendo com a planilha | 2026-08-10 | `—` | (aqui) | 710 |
| **229** | Portal: link de avaliar também no histórico da Agenda (`RatingLink`); diagnóstico do "acesso travado" | 2026-08-09 | `—` | (aqui) | 766 |
| **228** | `ConfirmDialog` promovido para o `@manto/ui`; exclusão em lote de pagamentos confirma em diálogo, com a soma e o que a busca escondeu | 2026-08-09 | `—` | (aqui) | 819 |
| **227** | Foto do portal saía por rota de staff (255 talentos com ícone quebrado); coordenador passa a ver o figurino do elenco inteiro | 2026-08-09 | `—` | (aqui) | 855 |
| **226** | Planilha de pagamentos no celular: cartões abaixo de `xl`, caixa de busca de volta e adiantamentos em janela sobreposta | 2026-08-08 | `—` | (aqui) | 925 |
| **225b** | Manutenção de figurino: conserto e ajuste do que já existe, com aviso na ficha e no elenco do evento | 2026-08-07 | `d2e6b94c07f1` | (aqui) | 997 |
| **225** | Produção de Figurinos: o trabalho de produzir ganhou registro, responsável, prazo na agenda e custo real | 2026-08-07 | `c1d5a83b64e7` | (aqui) | 1041 |
| **224f** | Conta de recebimento da Loja de Interações Virtuais ganhou tela (estava nula em produção) | 2026-08-07 | `—` | (aqui) | 1106 |
| **224e** | Landing da loja: a raiz do `alo.` caía no catálogo de eventos; agora lista as conversas | 2026-08-07 | `—` | (aqui) | 1123 |
| **224d** | `alo.mantoproducoes.com.br` como endereço curto da Loja de Interações Virtuais | 2026-08-07 | `—` | (aqui) | 1149 |
| **224c** | Estorno de comissão aparecia e descontava em todos os meses; agora só no mês corrente | 2026-08-07 | `—` | (aqui) | 1175 |
| **224b** | Loja de Interações Virtuais destravada: upload de capa na gestão, capa servida em rota pública, editor de FAQ | 2026-08-07 | `—` | (aqui) | 1210 |
| **224** | Evento com dinheiro vira cancelado (não apagado), com devolução ao cliente; exclusão só para Superadmin | 2026-08-07 | `b8e4d27a91f5` | (aqui) | 1255 |
| **223** | Calculadora EducaManto: transporte dobrado no recalcular, Econômico sem adicional por pessoa, NF sem transporte, comissão configurável | 2026-08-07 | `a3f7c19d5e02` | (aqui) | 1315 |
| **222** | Exportar elenco perdeu quatro campos (nascimento/CPF/RG/documento) na migração para o React | 2026-08-07 | `—` | (aqui) | 1368 |
| **221** | Agente auditor financeiro semanal (endpoints + fix de sobrescrita de upload) | 2026-08-06 | `—` | (aqui) | 1395 |
| **220b** | Hotfix: menu "Ferramentas" do evento embaçado no meio | 2026-08-06 | `—` | (aqui) | 1423 |
| **220** | Formulários×clientes×eventos: vínculo endurecido, fila de revisão e histórico da cliente | 2026-08-06 | `—` | (aqui) | 1446 |
| **219** | Email errado do talento: confirmação no cadastro e fila de devoluções | 2026-08-06 | `b4c81ef07d29`, `c5d92fa16e34` | (aqui) | 1507 |
| **218** | Superadmin corrige/exclui faixa de salário; Usuários com filtros; telas desempilhadas | 2026-08-06 | `—` | (aqui) | 1582 |
| **217** | Tema escuro com switch na sidebar, e reestruturação da documentação | 2026-08-06 | `—` | (aqui) | 1657 |
| **216** | Cachê no portal, prévia de link no WhatsApp, contraste e endurecimento de segurança | 2026-08-05 | `—` | (aqui) | 1726 |
| **215** | Tela de evento em abas, com edição inline e buscas visuais | 2026-08-05 | `—` | (aqui) | 1784 |
| **214** | Hotfix: Revendedor EducaManto sem acesso a nada (calculadora incluída) | 2026-08-05 | `—` | (aqui) | 1861 |
| **213** | Acervo 3D: superadmin exclui peça já usada, desvinculando de todos os eventos | 2026-08-05 | `—` | (aqui) | 1896 |
| **212** | Hotfix: diálogos abrindo pela metade, fora da tela | 2026-08-05 | `—` | (aqui) | 1928 |
| **211** | Vitrine: quadro da foto com teto e piso | 2026-08-05 | `—` | (aqui) | 1961 |
| **210d** | Hotfix: navegador preso no bundle antigo (e vínculo de ficha mais óbvio) | 2026-08-05 | `—` | (aqui) | 1996 |
| **210c** | Hotfix: Comercial voltou a enxergar o pagamento do evento | 2026-08-05 | `—` | (aqui) | 2028 |
| **210b** | Hotfix: buscador de pré-contrato mudo | 2026-08-05 | `—` | (aqui) | 2057 |
| **210** | Hotfix: horário deslocado, anexo do evento e orçamento sem saída | 2026-08-05 | `—` | (aqui) | 2092 |
| **209** | Catálogo como espinha organizacional (página própria + fichas + busca) | 2026-08-05 | `e7a1c94f20b3` | (aqui) | 2165 |
| **208** | Restauração do papel ENSAIO (dashboard + agendamento + presença) | 2026-08-05 | `—` | (aqui) | 2214 |
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
| Agenda / evento / formulário de evento | 233, 231, 215, 210, 208, 192, 184 |
| Loja de Interações Virtuais | 205, 205b, 205c, 205d, 205e, 205f |
| Impressões e Acervo 3D | 213, 202, 201, 200 |
| Marketing e frequência | 204, 204b |
| Catálogo e vitrine | 211, 209, 186, 185 |
| Financeiro, comissões e pagamentos | 230, 228, 226, 210c, 199, 194, 189, 187 |
| Orçamento e EducaManto | 214, 191 (orçamento), 190 |
| Portal do Artista | 233, 232, 231, 230, 229, 227, 216, 191 (portal) |
| Design system, tema e acessibilidade | 228, 217, 216, 212 |
| Documentação e economia de token | 217 |
| Formulários e pré-contrato | 210b, 188, 193 |
| Avaliações e dashboards | 232, 197, 196 |
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

### 260 — Nova etapa "Pronto" no painel de marketing                                                (em produção · 2026-08-24 · sem migration)

**Contexto.** O funil do Kanban de marketing era: Ideia → Produção → Revisão → Agendado →
Publicado. Revisão marca "material aprovado pela equipe de conteúdo"; Agendado era "vai ao ar no
dia/hora X". A lacuna: entre "tá tudo pronto" e "vai sair" precisa de um status intermediário,
porque o material chega pronto DIAS antes de sair (conforme a semana de conteúdo planejada).

**Solução.** Novo status "Pronto" (label "Pronto", emoji ✅, tom green no badge) entre Revisão e
Agendado. Material aprovado sai de Revisão para Pronto (propósito: está tudo bem, pronto pra ir
ao ar assim que vier a hora); depois vai para Agendado (propósito: foi agendado, esperando a data).
O Kanban ganha uma sexta coluna; não precisa de migration (coluna `status` é `VARCHAR(20)` sem
constraint de enum).

**Superfícies.**
- Backend `app/constants.py`: nova constante `MARKETING_STATUS_PRONTO = "pronto"` e entrada na lista
  `MARKETING_STATUSES` (ordem: ideia, producao, revisao, **pronto**, agendado, publicado).
  `app/models.py`: docstring do modelo atualizada. Validação em `marketing_ops.py` já aplica via
  lista — não precisa tocar na lógica.
- Frontend `frontend/apps/internal/src/lib/marketing.ts` — fonte única: type `MarketingStatus`
  (union), array `MARKETING_STATUSES`, records de labels, tones (green para contrastar) e icons.
  Kanban itera sobre `MARKETING_STATUSES` — coluna entra automaticamente.
- Tela `/marketing/painel` exibe novo status no Dialog de edição (`<select>` nativo, 6 options).
- API: `GET /api/marketing/posts` devolve a lista atualizada no campo `statuses`.

**Verificação.** `tsc --noEmit` limpo em `frontend/apps/internal`; `verify_204_marketing.py` lista
atualizada (ordem dos status conferida); backend valida novo status automaticamente (nenhuma
validação hardcoded).

**Pegadinhas.** Nenhuma — é um status novo no meio de uma lista flexível, sem constraint no banco.

### 259-portal-reset-sem-senha — "Esqueci minha senha" também para quem nunca criou senha (2026-08-24)

**Migration**: nenhuma. **Achado real, com dados de produção**: a maquiadora Iara (talent 139,
`password_hash` NULL) clica "Esqueci minha senha" no Portal do Artista, a tela responde "se os
dados conferem, enviamos o link", e nenhum e-mail sai. Há **119 talentos ativos** sem senha no
mesmo buraco.

**Causa**: `request_password_reset` (`app/talent_portal/portal_account_ops.py`) exigia
`talent.password_hash` truthy na condição de "matches" — quem nunca passou pelo fluxo de
Primeiro Acesso (ou nunca precisou, por ser talento antigo importado sem senha) caía num
`return` silencioso antes de gerar o token, sem log nem erro visível.

**Decisão**: remover a exigência de senha prévia da condição de match, mantendo todo o resto
igual — talento encontrado por `find_talent_by_login`, `email_contact` presente, e-mail digitado
batendo (`strip().lower()`) e a resposta HTTP idêntica em todos os casos (anti-enumeração, por
design). Isso funciona porque `reset_password_with_token` já define a senha e zera
`must_change_password` — na prática, o link de reset também serve como "definir a primeira
senha". **Primeiro Acesso continua existindo** como caminho paralelo (mensagem de erro em
`start_first_access` não mudou: "Este CPF já possui senha. Use a opção 'Esqueci minha senha'"
segue certa, pois só dispara quando `password_hash` já existe).

**Verificação**: `scripts/db/verify_259_portal_reset_sem_senha.py` (gitignored, não versionado)
contra `manto_local` — 15/15 checks: (a) sem senha + e-mail certo grava token (conferido por
conexão SQL separada da sessão do ORM, para não ser enganado por autoflush), (b) sem senha +
e-mail errado não grava nada, (c) com senha + e-mail certo continua funcionando (regressão), (d)
CPF inexistente devolve a mesma resposta 200 genérica dos demais casos, e o reset ponta-a-ponta
(token → definir senha → login → `must_change_password=False` → token invalidado).

### 258-cliente-manual — cadastrar cliente pela tela de Clientes (2026-08-21)

**Migration**: nenhuma. **Pedido**: "na tela do comercial das clientes preciso que seja possível
adicionar uma cliente manualmente".

A base só crescia por caminhos automáticos (Kommo, formulários) e pelo cadastro rápido de dentro
do formulário de evento — quem estava na tela de Clientes precisava abrir um evento para criar
uma ficha. Agora há o botão **"Nova cliente"** no cabeçalho e no estado vazio da busca.

**Decisões**:
- Reusa `POST /api/clientes/quick-create` (feature 165) em vez de endpoint novo: mesmo gate
  (`COMERCIAL`/`FINANCEIRO`/`SUPERADMIN`) e mesma regra de **telefone único**.
- Telefone repetido **não duplica**: o servidor devolve a ficha existente (`reused: true`) e o
  diálogo avisa com atalho para abri-la. E **não sobrescreve** o que já estava lá — cadastro
  rápido não pode apagar CPF/nome já conferidos por alguém.
- `quick_create_client` ganhou `cpf`/`cnpj`/`address` opcionais (só valem na criação): quem
  cadastra pela tela de Clientes costuma estar com o contrato ou a nota na mão.
- `useQuickCreateClient` passou a invalidar `clientes-list`/`clientes-metricas`/`clientes-search`
  — cadastro que não aparece na lista parece que não salvou. Reaproveitamento não invalida nada.

**Pegadinha encontrada**: o primeiro verify falhou por expectativa **minha** errada — o telefone
é normalizado com DDI (`11988880001` → `5511988880001`, regra do `normalize_phone`), o código
estava certo.

**Verificação**: `specs/258-cliente-manual/verify_258.py` — 7/7 no `manto_local`; e o fluxo
conferido na tela (validação, cadastro aparecendo na lista sem F5, aviso de telefone repetido).

### 257-hotfix-anexos-persistencia — o comprovante aparecia e sumia no refresh (2026-08-21)

**Migration**: nenhuma. **Relato do dono**: "ao anexar comprovantes na página do evento, na parte
comercial, quando dá refresh o comprovante some."

**Causa raiz**: `POST /api/events/<id>/payments` (e mais quatro da mesma família, feature 153)
chamavam os helpers `_add_*_record` de `app/calendar/routes.py`, que só fazem `db.session.add`.
Quem commitava era o **dispatcher do Jinja** (`_handle_add_payment` termina em
`db.session.commit()`); ao extrair a lógica para a API, o commit ficou para trás. O `PATCH` e o
`DELETE` dos mesmos recursos sempre commitaram — por isso editar e excluir funcionavam e ninguém
suspeitou do POST.

**Por que enganava**: o serializador da resposta consulta `EventPayment` na **mesma sessão**. O
autoflush do SQLAlchemy grava o INSERT pendente antes da consulta, então o JSON de resposta traz
o comprovante e a tela o desenha. No fim do request a sessão é descartada e o INSERT é desfeito.
Aparece e some — exatamente o relato.

**Escopo confirmado por HTTP real** (todos 2xx, nada gravado): comprovante de pagamento,
contrato, reembolso, nota fiscal e `POST /reimbursements/<id>/collect`.

**Correção**: `db.session.commit()` nos cinco endpoints (`app/api/agenda_write.py`).

**Recuperação**: o arquivo é salvo no volume **antes** do INSERT, então os anexos do período
ficaram órfãos (bytes intactos, sem linha). Endpoint novo — somente leitura, token do auditor —
`GET /api/audit-agent/<token>/orphan-attachments` lista os arquivos sem dono com data de envio
(carimbo do nome), tamanho e eventos candidatos (mexidos na mesma hora / com saldo em aberto por
perto); `specs/257-hotfix-anexos-persistencia/recuperar_anexos_orfaos.py` monta o relatório para
conferência humana. Nada é re-vinculado automaticamente.

**Pegadinhas encontradas**:
- **Um verify que confere pela sessão do Flask passa mesmo com o bug** (autoflush). A checagem
  tem de ser por conexão separada — foi o que quase escondeu o defeito no diagnóstico: a primeira
  varredura com `test_client` deu "tudo ok" porque um request posterior que commitava arrastava
  junto os INSERTs pendentes dos anteriores (mesma sessão compartilhada com o script).
- `secure_filename` come os `__` do prefixo de teste ao salvar (`__v257_c.png` → `v257_c.png`);
  limpeza de arquivos de verify precisa procurar pelo miolo.

**Pendência conhecida**: o handler Jinja gravava um `EventLog` por anexo ("Adicionou pagamento
recebido de R$ X") e a API não grava — o histórico do evento perde esse rastro. Item separado.

### 256-auditor-marketing — auditor de marketing semanal + mensuração no ERP (2026-08-21)

**Migration**: `c4d1e7b2a9f3` (aditiva): tabelas `marketing_agent_runs`, `marketing_import_files`
(`sha256` único), `marketing_post_metrics` (única por plataforma+post+`snapshot_date` — post é
FOTOGRAFIA, o export traz acumulados), `marketing_campaign_metrics` (única por
plataforma+campanha+período; `is_daily`), `marketing_account_metrics` (plataforma+dia),
`marketing_ad_spend_batches` (única por plataforma+`month_ref`; 1:1 com `special_expenses`) e
`marketing_ad_spend_lines`; colunas `marketing_posts.permalink` e
`clients.lead_origin/utm_source/utm_medium/utm_campaign`.

**Motivação**: Instagram, Meta Ads e Google Ads rodavam sem ninguém medir; o dono queria uma
auditoria semanal sem gastar API. Molde operacional do auditor financeiro (221): scheduled task
`auditoria-marketing-semanal` (segunda 06:30) → `scripts/marketing/` (collect → publish → checks
→ report) → e-mail. Decisões do dono (20/08): entrada = pasta local; canais Google Ads + Meta
Ads + Instagram orgânico; e-mail **e** tela; gasto de anúncios do cartão pessoal vai
**automaticamente** para reembolso com detalhe por campanha; gasto nasce **pendente**; reembolso
**dia 10**; manchete = **leads para o comercial**.

**Regras de negócio**:
- A rotina fala com o ERP **só por HTTP** (`/api/marketing-agent/<token>/{context,run,report}`,
  env `MARKETING_AGENT_TOKEN`, 404 sem env/token errado); diferente da 221, não lê banco nenhum.
- Única escrita além do histórico: Gasto Extra categoria Marketing, `disbursement_type=reembolso`
  ao titular (`card_holder_email` do `config.py`, validado como usuário interno ativo), status
  pendente, **sem comprovante** (`create_expense(..., require_receipt=False)` — parâmetro novo;
  a fatura do cartão é anexada depois). **Um por plataforma × mês civil**: atualiza valor e
  linhas enquanto pendente; aprovado/rejeitado ⇒ `frozen_at` e a diferença vira achado
  `gasto_divergente` (tolerância R$ 0,01). Gasto manual no mês com a plataforma no nome ⇒ não
  cria (`skipped_manual`). Moeda ≠ BRL ⇒ métricas gravadas, reembolso não.
- Sobreposição diário × agregado na mesma campanha: só as diárias contam; achado
  `periodo_sobreposto`.
- Vínculo post ↔ card: permalink normalizado > data+plataforma (só quando há **um** card e **um**
  post naquele dia) > nenhum (com candidatos); preencher o link depois revincula na rodada
  seguinte; o vínculo nunca piora.
- `POST /run` idempotente por `run_id` (replay devolve `result_json`); arquivo por `sha256`;
  `mode=local` só com `FLASK_ENV=development`.
- Importador do Kommo passa a guardar origem e utms ("mais recente sobrescreve"); atribuição
  casa `utm_campaign` normalizado com o nome da campanha.
- Gráficos do e-mail em HTML/CSS (Gmail não renderiza SVG embutido); na tela, SVG próprio em
  `components/charts/` (um eixo por gráfico; funil de unidades mistas vira tiles com a taxa).

**Pegadinhas encontradas**:
- `flask db downgrade -1` não existe no Flask-Migrate daqui — use a revisão explícita.
- Console do Windows em cp1252 quebra `print` com "↔"/acentos nos scripts de verificação:
  `sys.stdout.reconfigure(encoding="utf-8")`.
- O upsert das métricas "adota" a linha para a rodada que a regravou (`run_id`); a limpeza do
  verify por `run_id` de teste apaga métricas que uma rodada local anterior tinha gravado com as
  mesmas chaves — inofensivo no `manto_local`, mas explica "tela zerada depois do verify".
- Arquivo já lido (sha256) é `skipped_duplicate` no agente **e** no servidor; para repetir uma
  rodada local, apague `scripts/marketing/data/marketing_store_local.sqlite`.

**Ativação em produção**: deploy + env `MARKETING_AGENT_TOKEN` no Railway com o valor de
`.marketing-agent-token` (raiz, gitignored). Sem o env os endpoints respondem 404. Verificação:
`specs/256-auditor-marketing/verify_256.py` — 12/12 no `manto_local`.

### 255 — Tags NFC nas luminárias: a URL eterna e o Nº que a equipe anota na tagzinha            (branch · 2026-08-20 · migrations `a7e2f94c1d58` + `b3f8d27a9e14`)

*(2ª rodada, mesmo dia, antes do merge: (a) `nfc_tags.client_id` — a luminária também vai para
**cliente em potencial** via campanha de marketing, sem show nenhum; a equipe cadastra a pessoa
em Clientes e vincula direto na tag; precedência: cliente direta → contratante do evento;
(b) página pública redesenhada como retrato da peça física — céu noturno, nuvens e a estrela
"Magia de Sonhar" **acendendo** como a lâmpada real, com as cores da peça como tokens `lamp.*`
no tema do app público.)*

**Contexto.** Todo show entrega um presente 3D; o produto virou uma luminária de marca própria
com tag NFC embutida. A cliente encosta o celular e abre uma página da Manto — hoje um "portal
fechado" (boas-vindas + Instagram), amanhã campanhas segmentadas, descontos e as fotos do evento
dela. Feature desenhada em conversa com o dono do produto; decisões registradas na spec
(`specs/255-tags-nfc/`).

**A decisão que rege tudo**: a URL gravada na tag física é **imutável e eterna** — grava uma
vez, trava a tag, e TODO o conteúdo é decidido pelo servidor a cada acesso. Por isso:
- `nfc_tags.code` nunca muda; linha nunca é apagada (não existe DELETE em camada nenhuma; só
  `is_active`). Evento apagado → `event_id` vira NULL (`ondelete=SET NULL`), a página nunca quebra.
- O payload público já traz `campaign: null` — o gancho para o sistema futuro de campanhas sem
  regravar nenhuma tag entregue.
- Até o link do Instagram viaja no payload (`MANTO_INSTAGRAM_URL`), não no bundle.

**Regras de negócio principais.**
- **Uma tag = uma unidade física.** Código `<prefixo>-<sufixo>`: prefixo por produto
  (`acervo_3d_items.nfc_prefix`, ex. `01` = luminária v1 — decisão do usuário para organização
  humana), sufixo de 6 chars via `secrets` de alfabeto sem ambiguidade (31⁶ ≈ 887M por prefixo).
  **Nunca sequencial na URL**: a página terá conteúdo pessoal; código adivinhável era o risco
  nº 1 (uma cliente abriria a página da outra trocando o final).
- **`sequence` (pedido do usuário no meio do plan)**: numeração humana POR ITEM (nº 1, 2, 3…),
  única em `(item_id, sequence)` — é o rótulo que a equipe anota fisicamente na tagzinha ao
  gravar em lote, para depois alocar "nº X → cliente Y" sem depender do código aleatório.
- **Geração automática**: `add_event_gift`/`update_event_gift` chamam
  `nfc_ops.sync_event_gift_tags(event, item)` NA MESMA transação. Alvo = soma das `quantity`
  dos presentes do par `(evento, item)` — por par, e não por linha de presente, para sobreviver
  a presente deletado/recriado e a dois presentes do mesmo item. Cria só a diferença positiva;
  **reduzir/remover nunca apaga** (a tag física pode já existir no mundo).
- **Privacidade por indistinguibilidade**: `GET /api/nfc/<code>` responde **sempre 200 com o
  mesmo shape** — código inexistente e tag desativada são idênticos (`product: null`). Nada de
  404. Contadores de acesso são melhor-esforço (falha loga e não derruba a página).

**Superfícies.** Pública `/nfc/<code>` na raiz do domínio pelo mecanismo do `/cadastro`
(`NFC_PREFIX` no `frontend/server.js`, `isRootSurface` no `App.tsx` da vitrine) — portal
dourado sobre roxo profundo, Framer Motion com `useReducedMotion`, CTA só renderiza com a URL
na mão. ERP `/3d/tags` — Nº em destaque, lote, vínculo de evento via busca da agenda
(`useAgendaSearch`), copiar link, desativar/reativar; **sem excluir**. Campo "Prefixo NFC" no
formulário do Acervo.

**Pegadinhas encontradas.**
- O espelho `manto_local` estava um migration atrás do repo (`e2d8ca4b3071` × `f3a9c15d8b42`):
  o `db upgrade` local aplicou a da 254 junto — reforça a rotina de conferir `db current` antes
  de validar migration nova.
- Seed de teste de `CalendarEvent` exige `google_event_id` (NOT NULL/UNIQUE) e o de peça do
  Acervo exige ≥1 `Acervo3DFile` — sem o arquivo, o PATCH do Acervo devolve 400 por regra de
  negócio antiga e parece bug da feature nova.
- Verificação de UI com o Browser pane oculto: transições de saída congelam (dropdown do
  `Combobox` "fica aberto" cobrindo o rodapé do Dialog e engole cliques por coordenada) e a
  árvore de acessibilidade trunca — parecia bug da tela, era artefato já documentado na memória
  do projeto. O caminho de dados foi provado por `specs/255-tags-nfc/verify_255.py` (34/34).
- A foto do item vem do banco espelhado mas o ARQUIVO não existe em `instance/uploads/` local →
  a página pública ganhou fallback de `onError` na imagem (brilho genérico no lugar do ícone de
  imagem quebrada) — resiliência que vale também em produção.

*(As 12 entradas mais recentes. As anteriores estão em `docs/historico/` — ver índice acima.)*

### 254 — Vídeo da Revisão sem sumiço, catálogo↔ficha nas duas mãos, e a corrida do sync            (branch · 2026-08-20 · sem migration)

**Motivação.** Três melhorias pedidas pelo dono no mesmo dia, mais um incidente real: (a) "não
está sendo possível anexar o vídeo para revisão"; (b/c) o vínculo ficha↔catálogo precisava
funcionar nas duas direções e a busca "parecia bem errada"; e (d) a vendedora recebeu "Ocorreu um
erro inesperado" criando um evento CORP às 12:08 — DEPOIS do fim da tempestade de deploys da
remoção do Jinja, o que derrubou a explicação de janela de deploy para o caso.

**a) Revisão de mídia.** O vídeo nunca "falhava": ele era rejeitado (extensão fora da lista dos
formatos que o navegador reproduz, ou >512 MB) e a rejeição morria em silêncio em três lugares —
a página de criação navegava descartando `errors`; a página do espaço não tinha `onError` nem
indicador de envio (minutos de upload sem nenhum sinal); e o 413 do teto global respondia HTML
cru, que o cliente traduz para a mensagem genérica. Correções: validação no cliente ANTES do
envio (espelho de `review_ops._MEDIA_EXTS` + 512 MB), upload por `XMLHttpRequest` com barra de
progresso real (fetch não expõe progresso de envio) nas três superfícies, rejeições da criação
viajam via `state` da navegação e viram aviso persistente no espaço, `accept=` com extensões
explícitas, e handlers globais 403/404/500/413 respondendo o envelope JSON em `/api/*` — a
lacuna que transformava qualquer 500 num "inesperado" sem rastro.

**b) Busca de personagem do catálogo.** A lista mostrava só o nome — cinco "Homem-Aranha"
idênticos, um por produto — e, na edição da ficha, personagens já vinculados a OUTRA ficha eram
selecionáveis: escolher um roubava o vínculo em silêncio. Agora toda linha mostra
"Personagem — Produto", a busca casa também com o produto, e personagem com ficha aparece
apagado com "já tem ficha" (`disabledCharacterIds` no `CharacterAutocomplete`) em vez de sumir
ou ser roubável. O casting de eventos herda o contexto do produto sem mudar de comportamento.

**c) Criar produto do catálogo.** O painel de Personagens (elenco, vínculo personagem→ficha,
ficha própria do avulso) só existe na edição — toda mutação dele precisa do id. Criar mandava
para a LISTA; agora aterrissa em `/admin/catalogo/<id>/editar` com aviso apontando o painel.
Pegadinha de Router: `/novo` e `/:id/editar` usam o mesmo elemento — o componente NÃO remonta,
então o aviso é derivado de `location.state` a cada render (um `useState` inicial congelava).

**d) O erro das 12:08 — RESOLVIDO pelo log do Railway (e uma corrida de brinde).** O log cravou
as duas causas reais, nenhuma reproduzível com payload "bem-comportado":

1. **Criar evento**: `StringDataRightTruncation` — o título da casa lista o elenco inteiro
   ("(CORP) SOLDADO 1 BONECO + SOLDADO 2 BONECO + PINGUINO + …") e passa de 200 chars;
   `calendar_events.title` era `VARCHAR(200)`. O estouro acontecia DEPOIS do insert no Google:
   cada tentativa deixou um órfão no Google Calendar (4 tentativas 12:04–12:19). Migration
   `f3a9c15d8b42` alarga título/location/`audit_logs.entity_name`/`commission_payments.event_title`
   para 500 (as cópias vão juntas, senão o estouro só muda de endereço), e `_validate_event_core`
   barra título >480 com erro de campo ANTES do Google — sem órfão nunca mais.
2. **Calculadora** (o "não pode ser calculado" de dias): `IndexError` em `quote_ops:202` —
   `get_especial_prices` devolvia default de **3 itens** para personagem ausente da tabela;
   recalcular orçamento antigo cujo personagem foi removido derrubava o cálculo inteiro. Agora
   os defaults têm 4 itens com `_ensure4` (normaliza tabela legada também) e o `calculate_quote`
   responde 400 amigável: "o personagem X não está mais na tabela — remova-o ou recadastre".

A corrida com o auto-sync (importa evento do Google sem linha local ANTES do commit de quem está
criando → unicidade de `google_event_id` estoura) é real mas não foi o que mordeu — ficou
corrigida mesmo assim (evento do Google com <5 min e sem linha local espera o ciclo seguinte).
Os handlers novos de (a) garantem que qualquer próximo 500 venha com mensagem e rastro.

**Verificação.** `tsc` limpo; `ruff F821` limpo; diagnóstico in-process da Revisão (rejeição,
413 JSON, upload válido listado); e2e no navegador contra `manto_local` (mkv barrado na hora,
mp4/mov criados; busca "aranha" com produto e badge; criar produto aterrissa na edição com
painel); janela de graça do sync testada contra cópia de produção (1 min não importa, 10 min
importa). Ferramenta nova em `scripts/db/`: `diag_20260820_restore.py` restaura o dump noturno
de produção num banco descartável — foi o que permitiu testar o fluxo da vendedora com os dados
reais dela.

### 250, 251 e 252 — A régua de comissão sai do Jinja e as coleções comerciais ganham API            (branch · 2026-08-20 · sem migration)

**250 — o pré-requisito mais perigoso da fase 6.** `app/api/financeiro_read.py`, que alimenta o
DRE, o pipeline de vendas e a planilha de pagamentos do React, importava `_event_commission`,
`_event_cost`, `_group_cost`, `_get_commission_rate` e `_resync_pending_commissions` de dentro do
blueprint Jinja. Apagar aquele arquivo derrubaria o financeiro inteiro da plataforma nova.

230 linhas foram para `app/financeiro/comissoes_ops.py` — nove ramos de decisão até o valor final:
Loja Virtual não comissiona; o beneficiário pode ser o responsável EducaManto em vez do vendedor;
EducaManto calcula sobre o **lucro** (venda − BV − cachês) e o resto sobre a venda; BV sempre sai
da base; evento cancelado não comissiona; líder de grupo agrega o custo dos satélites; e comissão
já paga nunca é reescrita.

**O recorte por intervalo levou junto 4 coisas de camada de rota** (`_has_role`,
`require_financeiro`, `_is_educamanto_responsavel` sem argumento, `require_vendas`) — todas
dependem de `current_user`. Foram devolvidas. Quem apontou foi o `ruff --select F821`.

> **Verificação à altura do que o código decide:** comissão, custo, custo de grupo e taxa
> calculados para os **450 eventos** do espelho antes (worktree do `main`) e depois, comparados
> item a item — **zero divergências**. Nenhum vendedor recebe um centavo diferente.

**251 e 252 — as coleções comerciais ganham API.** O levantamento das rotas mostrou que existia
`POST` para contrato, nota e pagamento, mas **nada** para acréscimo e parcela — elas só podiam ser
escritas pelo formulário Jinja. Agora: `PUT /acrescimos`, `PUT /parcelas` (corpo é a lista inteira;
`{"items": []}` apaga, corpo sem `items` é 400 para requisição malformada nunca virar "apague
tudo") e `PATCH`/`DELETE` de nota fiscal por id. Todas herdam as regras já testadas de
`comercial_ops` e recusam satélite com 409 + `leader_id`.

Duas decisões que ficaram no código: `PATCH` de nota sem `file` **preserva** o anexo (é edição de
valor/data), e `DELETE` **não apaga o arquivo do disco** — nota fiscal é documento contábil.

**O teste pegou um erro dele mesmo:** mandar `"1500,00"` faz o valor virar `None` em silêncio. Não
é defeito — `_decimal_from_form` recebe número puro de propósito (BRL formatado é só exibição, e
`"1.234,56"` é convenção do Jinja). Ficou comentado no teste.

**Medição que corrige o plano:** depois de limpar o financeiro, `calendar/routes.py` ainda exporta
**47 símbolos distintos em 86 pontos de import** para 13 módulos vivos. A maioria não é view — é
criação e validação de evento, consulta de mês, parsing de título, registros de pagamento e
contrato. Aquele arquivo virou uma **biblioteca com views penduradas**: apagar as views não o
apaga. O item 5 da fase 6 é uma sequência de extrações, não um lote de deleção.

**Verificação.** `verify_251` 18/18 (novo), `verify_249` 17/17, `verify_246` 22/22, `verify_206`
20/20, `check_url_for_orfaos` limpo, ruff 60 → 60. `financeiro/routes.py`: 1.736 → 1.507 linhas.

### 248 e 249 — Comissão sincroniza pela API, e o núcleo comercial sai do formulário            (branch · 2026-08-20 · sem migration)

**248 — a comissão não acompanhava a edição pela tela nova.**
`event_ops.update_event_comercial` grava `sale_value`, `seller_id` e `commission_rate` — os três
insumos da comissão — e **nunca tocava em `CommissionPayment`**. O gêmeo Jinja sincronizava, então
a mesma edição dava resultado diferente conforme a tela usada, e a nova era a errada. Provado antes
do conserto: venda de R$ 5.000 com vendedor comissionado gerava zero linhas.

**O estrago real era pequeno, e isto importa registrar** para ninguém procurar um rombo que não
existe: `_resync_pending_commissions()` roda a cada abertura da tela de comissões ou de pagamentos
(`api/financeiro_read.py:566` e `:670`) e recalcula **toda** linha *a pagar*. A auditoria do espelho
achou **zero** linhas `a_pagar` divergentes. As 6 divergências existentes são todas `pago` ou
`cancelado` — congeladas de propósito, porque histórico do que foi pago não acompanha recálculo.

**O buraco que sobrava:** o resync só percorre linhas que já existem. Venda que nunca gerou linha
nunca ganhava uma — são 3 eventos no espelho (`69`, `62`, `203`, R$ 12.355 somados, todos sem
`sale_date`). **Não foram tocados:** comissão retroativa é decisão do dono. Ver §7.3b do plano.

A correção injeta `sincronizar_comissao` em `update_event_comercial`, mesmo arranjo do `group_ops` —
o domínio da agenda não deve puxar a régua de comissão de 9 ramos do financeiro, e
`financeiro/routes.py` morre na fase 6.

**249 — as três coleções comerciais saem do formulário.** Acréscimos, notas fiscais e parcelas
eram escritos **só** em `_handle_update_comercial`, lidos linha a linha
(`request.form.getlist("acrescimo_bv_recipient[]")`, arquivo por linha em `nf_file__<key>`). Não
existiam para a plataforma React. Agora vivem em `app/calendar/comercial_ops.py`, com contrato de
lista de dicionários; o Jinja traduz e delega.

**Quatro regras que a tradução podia perder em silêncio — todas com teste:**

1. **Lista ausente ≠ lista vazia.** `None` é "não mexa", `[]` é "apague tudo". No formulário era
   `if _acr_tipos:` — sem a distinção, salvar outra parte da aba apagaria todos os acréscimos.
2. **BV já pago continua pago.** A gravação apaga e recria, então o status é resgatado por
   `(recebedor, pix)`. Sem isso, salvar a aba "despaga" alguém que já recebeu dinheiro.
3. **Acréscimo percentual congela em reais** sobre a venda do momento do save.
4. *(achada escrevendo o teste)* **Anexar arquivo emite a nota, mas `issued_at` só é carimbado na
   transição** — salvar de novo com o mesmo arquivo não reescreve a data de emissão.

**Verificação.** `verify_249_comercial_ops.py` 17/17 e o probe da comissão (R$ 5.000 → R$ 500;
editar para R$ 2.500 → R$ 250), ambos contra o espelho. `verify_206` 20/20, `verify_246` 22/22,
`check_url_for_orfaos` limpo, ruff 60 → 60. `calendar/routes.py`: 3.720 → 3.662 linhas.

### 246 e 247 — Agrupar e desagrupar eventos na plataforma nova            (branch · 2026-08-19 · sem migration)

**Motivação.** Agrupar evento só existia na tela Jinja, que a fase 6 vai apagar. O dono confirmou
que é "importantíssimo". E a ausência dela na plataforma nova já causava **dois defeitos em
produção**, encontrados na apuração: era impossível cancelar um evento principal pela interface
nova (a mensagem mandava desagrupar antes, e desagrupar não existia — beco sem saída), e
`PATCH /api/events/<id>/comercial` **aceitava gravar venda num satélite**, valor que entrava no
banco e sumia de todos os relatórios, porque o financeiro pula satélites de propósito.

**Núcleo.** `app/calendar/group_ops.py`, extraído de `calendar/routes.py`. Funções puras; os
handlers Jinja passaram a delegar, então as duas superfícies não divergem enquanto o Jinja existir.

**Duas travas que o Jinja não tinha**, decididas pelo dono:

1. **Cópia antes de apagar.** Agrupar zera os 14 campos comerciais do satélite e desagrupar **não
   devolve**. Agora os valores vão para o histórico do evento antes de sumirem — não restaura
   sozinho, mas dá para consultar e redigitar. `Decimal` vai como string, não float: este snapshot
   existe justamente para alguém redigitar um valor de venda.
2. **Comissão órfã.** Agrupar zerava a venda e não mexia na comissão (no espelho, o evento 287 é
   satélite com venda zerada e R$ 137,50 marcados como *pagos*). `agrupar` recebe
   `sincronizar_comissao` injetada e cancela a linha **a pagar**; a já paga sobrevive. A injeção
   evita a agenda importar a régua de comissão de 9 ramos do financeiro.

**Endpoints.** `GET .../grupo/candidatos?q=` (busca no **servidor** — o Jinja despejava os 354
eventos no HTML), `POST/DELETE/PATCH .../grupo`, e `DELETE .../grupo/satelites/<id>`, que o Jinja
não tinha: sem ele, dissolver o grupo de 13 satélites exigia abrir os 13.

**Tela.** `GrupoPanel` com os três estados e `AgruparEventosDialog` com confirmação em duas etapas
— o 409 devolve **quais** eventos perdem venda e **quanto**, e o diálogo lista nome e valor antes
de perguntar (a tela antiga tinha um checkbox genérico). Se o principal escolhido não for o evento
aberto, navega para ele: a página em que a pessoa está pode ter acabado de virar satélite.

**Pegadinhas — três, e duas só apareceram testando:**

- `json_error` e `ApiRequestError` **descartavam** qualquer chave além de `message`/`fields`. Sem
  os dois lados, `events_with_sale` e `leader_id` chegavam e eram jogados fora.
- `datetime` não estava importado em `agenda_write.py` nem em `agenda_read.py` (só `date`). O
  segundo passou no teste contra dado real **por sorte** — todos os satélites do espelho têm
  horário — e quebraria no primeiro sem. Foi o `ruff --select F821` que pegou.
- **O `GrupoPanel` derrubava a página inteira** quando o bloco `group` não vinha: tela branca, não
  um painel a menos. O typecheck não pega isso. Apareceu na verificação visual, com o backend de
  dev rodando código anterior — que é exatamente o descompasso backend/bundle que este projeto já
  registrou antes. O campo virou opcional.

**Verificação.** `verify_246_grupos_api.py` 22/22 contra o espelho (inclui: o aviso mostra o valor
exato antes de apagar; a cópia chegou ao histórico; a porta do satélite fechou; **os 5 grupos reais
continuam intactos**). `npx tsc --noEmit` limpo nos dois apps. E na tela, contra o espelho: o
evento 319 lista seus 13 satélites com "Remover" em cada um, o 329 mostra o caminho de volta ao
principal, e o painel de venda do satélite ficou com **zero botões**.

### 244 e 245 — Fases 3 e 5 da remoção do Jinja: onze blueprints            (branch · 2026-08-19 · sem migration)

**244 — os oito que saem inteiros.** `rh` (1 rota), `clientes` (7), `gastos` (18), `revisao` (14),
`orcamento` (14), `formularios` (17), `admin` (24) e `talents` (13), com os templates. **47
arquivos, −11.864 linhas.** Os `*_ops.py` de cada pacote **ficaram** — são eles que a API consome.

**245 — os três parciais.** Cada um perdeu a superfície Jinja e manteve o que a plataforma nova
depende: `catalogo` fica só com as rotas de arquivo (`/midia/*`, `/og/*`); `figurino` fica com as
**duas rotas de impressão**, que não são legado — são o único Jinja que a interface nova abre de
propósito (`window.open` em `FigurinoListPage.tsx` e `FigurinoSection.tsx`); `feedback` fica só com
o `GET /avaliar/<token>` que virou 302 na 241 e **não some nunca**, porque o token não expira.
**−2.500 linhas.** Fecha também a fase 5.

Saiu junto o importador de fichas do Google Drive (`/figurinos/sync-drive`) — o dono confirmou que
rodou uma vez só, na migração — levando as ~160 linhas do parser de Google Docs que só ele chamava.
`drive_service.normalize_name` **continua em uso**: é o que casa dois cargos escritos diferente
como o mesmo personagem na impressão do evento.

**Ferramenta nova: `scripts/db/check_url_for_orfaos.py`.** O Flask só descobre `BuildError` em
tempo de execução, quando alguém abre a página — numa remoção em lote o estrago apareceria dias
depois, numa tela que ninguém tocou. O script varre todos os templates, extrai o primeiro argumento
de cada `url_for` e confere contra o `url_map` real. Rodar depois de cada lote. (Vive em
`scripts/db/`, que é gitignorada, então é local.)

**Pegadinha que se repetiu:** `scripts/db/verify_220_vinculos_formularios.py` importava dois
símbolos de `app.formularios.routes` — mesma classe do `verify_166` do `rh`. A pasta é gitignorada,
então **só o grep encontra**; o `git grep` não. Por isso a regra agora é varrer o repo inteiro,
`scripts/` incluído.

**Verificação.** `create_app()` sobe com 382 rotas; `check_url_for_orfaos` zero órfãos; as APIs
equivalentes seguem registradas (`/api/rh/dashboard`, `/api/admin/users`, `/api/clientes/`,
`/api/gastos`, `/api/revisao`, `/api/formularios`, `/api/talents`, `/api/catalogo`); as quatro
superfícies vivas de pé (`/uploads/`, `/figurinos/<id>/print`, `/portal/photo`, `/avaliar/<token>`);
`verify_206` 20/20; `verify_241` 11/11; ruff medido com worktree de `main`: 98 → 60 erros, nenhum
novo. Templates: 84 → 17.

**Estado:** o Jinja que resta é exatamente `calendar`, `financeiro` (+`/vendas/`) e `auth`.

### 242 e 243 — Portal Jinja removido, e a lógica que a API importava sai do Jinja            (branch · 2026-08-19 · sem migration)

**242 — fase 2: Portal do Artista.** As 20 rotas Jinja de `talent_portal/routes.py` e os 12
templates de `app/templates/portal/` saíram. **−3.230 linhas.** Não era só limpeza: essas rotas
seguiam respondendo pelo domínio direto do backend com validação **mais fraca** que a da API — o
upload de foto do perfil conferia só a extensão, sem limite de tamanho.

`/portal/photo/<caminho>` **fica**: é como toda imagem chega ao talento, porque `/uploads` exige
sessão de *staff* e para ele vira ícone quebrado. Conferido antes de tocar: nenhum módulo importa
de `talent_portal.routes` (os cinco `api/portal_*.py` importam dos `*_ops`), e
`api/portal_auth.py:92` grava `session["talent_id"]` — **a mesma chave** que `portal_photo` confere,
então o login do React mantém a foto funcionando. Saiu junto o `before_request`
`portal_domain_routing`, que já não fazia efeito (o proxy usa `changeOrigin`, então o Host que chega
ao Flask nunca é o do portal) e passaria a apontar para uma rota inexistente.

**243 — a descoberta que muda a fase 3.** O plano tratava a fase 3 como remoção limpa. **Errado:**
uma varredura de imports mostrou **cinco módulos vivos importando lógica de negócio de dentro dos
`routes.py` Jinja**. O caso do `feedback`, registrado na 241, era a ponta de um padrão sistêmico.

Três eram re-exportação e viraram repontamento: `ensure_recurring_entries`/`recurring_alerts` já
viviam em `gastos_ops` (:445, :482) e `_parse_period` era um alias para `rating_ops.parse_period`.
Dois foram extração de verdade: `app/feedback/feedback_ops.py` (novo, com as etiquetas e a regra
por nota) e **271 linhas** do núcleo dos formulários para `formularios_ops.py` — `FORM_META`,
`_save_response`, `_validate_dynamic`, `retry_auto_link_pending` e mais dez, que o **formulário
público React** consome. `formularios/routes.py` foi de 631 para 361 linhas.

**Pegadinha do recorte:** ele não podia ser contíguo. Os decorators de RBAC no meio do arquivo usam
`current_user` e `abort` — são camada de rota e ficaram. E o `ruff --select F821` pagou o próprio
custo: pegou quatro nomes que ficaram sem import (`SiteSetting`, `urllib`, `normalize_phone`,
`not_`) e uma chamada por prefixo de módulo que virou local.

**Regra que fica para as próximas fases:** antes de apagar qualquer blueprint, rodar
`grep "from app\.<nome>\.routes import"` no repo inteiro. `calendar` e `financeiro` têm a mesma
doença em escala maior, com *imports tardios* dentro de função.

**Verificação (as duas).** `create_app()` sobe com 506 rotas; a única rota `/portal` restante é
`/portal/photo`; `verify_206` 20/20; `verify_241` 11/11; zero mojibake nos arquivos reescritos por
script (conferido com `git diff --stat`, que tocou só as linhas pretendidas).

### 241-avaliar-aponta-para-react — O link da cliente para de cair no Jinja            (branch · 2026-08-19 · sem migration)

**Motivação.** A página React de avaliação existe e funciona desde a feature 164, mas a geração do
link nunca foi trocada — então **toda cliente que recebeu o link continuava caindo na página
Jinja**, e nenhuma leitura casual do código denunciava isso. Foi confirmado executando o
`frontend/server.js` real contra um backend falso: `GET /avaliar/<token>` é proxiado ao Flask,
porque `isBackendRequest` é a **primeira** checagem do handler, antes de qualquer mount de SPA —
inclusive com `Host` de portal e de alo.

**O que mudou.** `GET /avaliar/<token>` devolve 302 para `/catalogo/avaliar/<token>` em vez de
renderizar Jinja, e os dois geradores passam a emitir o endereço novo direto.

**Por que a rota antiga não some nunca.** `/avaliar/<token>` é o endereço que a comercial copia e
cola no WhatsApp desde a feature 130, **o token não expira** e não há como recolher um link já
enviado. Ela vira redirect permanente de compatibilidade.

**Decisões de implementação.** Redirect **relativo**: sai pelo mesmo host público e o browser
reentra no `server.js`; uma URL absoluta montada no Flask pegaria o Host do serviço backend, porque
o proxy usa `changeOrigin`. **302 e não 301**, para o navegador não memorizar e o destino continuar
nosso para mudar. O prefixo `/catalogo` existe porque o bundle da vitrine roda com
`basename="/catalogo"`.

**O POST Jinja foi mantido de propósito** — quem estiver com o formulário antigo aberto no
navegador ainda consegue enviar.

**Armadilha registrada para a fase 5.** `app/api/feedback_write.py:18` importa `POSITIVE_TAGS`,
`ATTENTION_TAGS` e `_tags_for_score` de `app/feedback/routes.py`. **Apagar o arquivo Jinja hoje
derrubaria a API React de avaliação, que está viva em produção.** Extrair essas constantes para um
módulo próprio é pré-requisito da remoção do blueprint. É o segundo caso de API importando do
Jinja — o outro são os imports tardios de `calendar/routes.py`.

**Verificação.** `scripts/db/verify_241_avaliar_react.py` (novo): 11/11 contra o `manto_local`.
`verify_206`: 20/20. Ruff: 1 erro em `main` → 1 aqui, o mesmo, pré-existente.

### 240-remocao-jinja-fase1 — Órfãos e código morto do Jinja legado            (branch · 2026-08-19 · sem migration)

**Motivação.** O sistema tem três estágios convivendo desde a migração para React, e as páginas
Jinja substituídas continuavam registradas. O plano completo de remoção está em
`docs/PLANO_REMOCAO_JINJA.md`: 530 rotas auditadas, 346 ficam (326 são `/api/*`), 175 removíveis.
Esta é a primeira fase — só o que a verificação adversarial confirmou não ter nenhuma referência
viva. −1.043 linhas, zero mudança de comportamento em produção.

**O que saiu.** Templates órfãos `home.html`, `admin_layout.html` e `financeiro_layout.html` — os
três eram documentos autocontidos com `<!doctype html>` próprio, não layouts herdados (os 12
`admin_*.html` sempre estenderam `base.html`). O estático `slapwars.gif`, cujo ciclo de vida o
`git log -S` mostra inteiro: entrou nas páginas de erro e foi trocado por `source.gif` no 74f97f0.
Em `calendar/routes.py`, `travel_estimate` (que **já respondia 404**, porque perdeu o decorator em
algum momento — quem atende é `GET /api/events/<id>/travel-estimate`) e `_is_outside_sp`, sem
nenhum chamador. E as rotas `/impersonate/<role>` e `/impersonate/reset`, que só recebiam POST do
`base.html`.

**Pegadinhas encontradas — as três valem mais que a remoção em si.**

1. **Existe um `home.html` VIVO.** `app/templates/portal/home.html` é renderizado em
   `talent_portal/routes.py:462`. Um glob recursivo derrubaria o Portal do Artista. Deletado pelo
   caminho exato.
2. **`_SP_CITY_TERMS` foi preservada de propósito.** A constante fica no mesmo bloco "LOGÍSTICA" do
   `_is_outside_sp` removido, mas é usada também por `_lookup_sp_status`, como fallback quando o
   ViaCEP falha — e isso **roda em produção**. Apagar o bloco inteiro daria `NameError`.
3. **`_safe_next` também foi preservada.** Parece morta depois que as rotas de impersonação saem,
   mas `financeiro/routes.py:12` a importa de `app`. Só vira código morto na fase 3.

**O que NÃO entrou, e por quê.** O `rh_bp` estava listado nesta fase como "risco zero". A
verificação adversarial derrubou: `scripts/db/verify_166_rh_tools_bp.py:107-110` bate em
`GET /rh/dashboard` esperando 200 e sai com código 1 se falhar. Produção não quebra (`/rh` não é
proxiado, o React existe em `App.tsx:143`, a API em `api/rh_read.py:16`), mas o harness de
regressão local sim. Escapou da varredura inicial porque `scripts/db/` é gitignorada. Foi para a
fase 3, junto com a adaptação do verify.

**Verificação.** `create_app()` sobe e `/impersonate/*` sumiu do `url_map`, restando só
`/api/auth/impersonate` (que grava na mesma chave de sessão e valida contra a mesma
`IMPERSONABLE_ROLES`). `verify_206_react_primario.py` contra o `manto_local`: 20/20. Ruff nos
arquivos tocados: 16 erros em `main` → 15 aqui, nenhum novo.

### 239-backlog-agosto — Carrinho de transporte, presença sem valor, troca de tipo automática            (branch · 2026-08-18 · migration `d1c7b93a2f60`, `e2d8ca4b3071`)

**Motivação.** Rodada de 11 itens do backlog levantados pelo João em 18/08/2026, investigados
item a item (`specs/239-backlog-agosto/research/*.md`, um arquivo por item, causa raiz +
evidência arquivo:linha) e fechados em `decisoes.md` (fonte de verdade em conflito com qualquer
proposta da investigação): (1) carrinho de transporte fora de SP no casting + fix do apagamento
de `travel_cache`; (2) Técnico de Som (Presença) sem valor e fora da planilha de pagamentos;
(3) show→não-show remove ensaio/vagas automaticamente e corrige o prefixo do título; (4) link do
orçamento de origem na aba Comercial; (5) Coordenador/Técnico/Maquiador nunca no título;
(6) badge de maquiador; (7) teto do cachê visível a superadmin com a conta em valores;
(8) link do portal na cobrança WhatsApp; (9) EducaManto — descoberta da Contratação Manto + 4
defeitos + `InfoTip` real; (10) Catálogo no topo do menu; (11) dialog de produção/compra com
scroll interno.

**O que mudou.**
- **Banco**: `event_roles.does_transport` (Boolean, nullable — `d1c7b93a2f60`) e
  `event_roles.cache_cap_note` (Text, nullable — `e2d8ca4b3071`), encadeadas em `c8f4d92e17ab`
  (catalogo-fase-1). Head atual: `e2d8ca4b3071`.
- **Backend**: `app/calendar/casting_ops.py` ganhou `e_vaga_de_presenca`,
  `valor_transporte_papel` (cascata: orçamento → `travel_distance_km × 2 × tarifa` → zero),
  `set_transporte`, e o sentinela `_UNSET` em `assign_role` para `travel_cache` (só grava quem
  manda a chave — o casting em React nunca manda). `app/calendar/event_ops.py` ganhou
  `aplicar_troca_de_tipo`/`build_gc_title`/`EventTypeChangeBlocked`/`_sincronizar_e_trocar_tipo`,
  fonte única chamada por `update_event_core` e `update_event_basics`. `app/calendar/routes.py`
  ganhou a denylist `RESERVED_TITLE_NAMES` (+ `_strip_reserved_title_segments`, usada no sync do
  Google) e `_create_extra_roles_from_orcamento` (vagas de apoio do orçamento criadas no
  servidor). Endpoints novos: `POST`/`DELETE /api/roles/<id>/transporte` (gate
  `_can_edit_event()`; `POST` recusa fora de `event.is_outside_sp`). `app/api/agenda_read.py`
  serializa `is_presence`, `does_transport`, `transporte_valor`, `cache_cap_efetivo` em cada
  papel, restringe `cache_cap`/`cache_cap_note` a superadmin, e `venda.orcamento_history_id` ao
  dono do orçamento/superadmin; `data.maquiagem` (`{precisa, fechado}`) no detalhe do evento.
  `app/api/dashboard_service.py` ganhou `portal_url`. `app/financeiro/routes.py`,
  `app/api/financeiro_read.py` e `_compute_kpi` passaram a excluir a vaga de presença dos
  somatórios.
- **Frontend**: `CastingSection.tsx` (botão de carrinho, badge 🚗, teto+nota só para
  superadmin, card somente-leitura da presença, badges de maquiador, 💄 por personagem),
  `ComercialSection.tsx` (link "Orçamento de origem"), `EnsaioSection.tsx` (esconde "+ Agendar
  ensaio" sem necessidade), `ResumoSection.tsx`/`EventEditPage.tsx` (`AvisosCard` para os
  `warnings` da troca de tipo), `EventCreatePage.tsx` (pré-fill filtra `characters` por
  `role_type === "character"`), `ElencoBlock.tsx` (denylist defensiva em `generateTitle`),
  `EducaMantoCalculadoraPage.tsx` (card Contratação Manto reposicionado, aba "+ Manto", banner
  Sem/Com NF, `contratacao_manto` sempre enviada quando ativa, deep-copy em Nova Página,
  `event_location` no payload), `navigation.tsx` (Catálogo na 1ª seção, `everyone`),
  `FigurinoProducaoListPage.tsx` (`max-h-[85vh] overflow-y-auto`). Componente novo
  `InfoTip` em `@manto/ui` (hover/clique/toque/teclado, Framer Motion, `useReducedMotion`).

**Regras de negócio novas (decisões-chave).**
1. **Parcela de UM veículo** — nunca `event.transport_value` cheio: aquele campo já inclui o
   adicional fora-SP por pessoa (somado dentro do `cache_cap` de todo mundo) e a rodagem de
   TODOS os carros; usá-lo pagaria o adicional duas vezes e daria a frota inteira a um motorista.
   Com 2 carros no orçamento, cada motorista marcado recebe a parcela de 1 carro.
2. **Teto com carrinho** — `teto_efetivo = max(cache_cap + parcela_do_veículo_quando_marcado,
   valor_já_salvo)`, a parcela somada **dentro** do `max` (nunca por cima — ver pegadinha 1
   abaixo). O valor pago fica todo em `cache_value` (um número só): entra automático em
   planilha de pagamentos/custo/DRE, sem mudar nada no financeiro.
3. **Presença sem valor e fora de tudo** — `assign_role`/`add_role` forçam `cache_value=None`
   para a vaga "Técnico de Som (Presença)"; ela sai de custo de evento, KPI, DRE, dashboard
   `money_total`, comissões e planilha de pagamentos. Continua visível no casting como somente
   leitura (a designação é tarefa do painel de Ensaio).
4. **Equipe nunca no título** — denylist (`RESERVED_TITLE_NAMES`: Coordenador, Técnico de Som,
   Técnico de Som (Presença), Maquiador) aplicada em três pontas: pré-fill/`generateTitle` no
   cliente, `parse_characters`/reconciliação no servidor, e o sync do Google
   (`_strip_reserved_title_segments`, para uma edição manual do título feita direto na Agenda
   não reintroduzir o nome).
5. **Troca de tipo com push-antes-do-destrutivo** — sair de SHOW cancela ensaios agendados
   (inclusive no Google), remove as duas vagas de som (mesmo preenchidas) e desliga
   `needs_rehearsal`, tudo registrado em `EventLog` e devolvido como `warnings` não-bloqueantes.
   O título com o prefixo `(TIPO)` novo vai ao Google **antes** dessa automação rodar; se o push
   falhar numa troca que envolve SHOW, a troca inteira é desfeita e o endpoint devolve **409**
   `EventTypeChangeBlocked` — o resto do salvamento fica gravado.
6. **Extras do orçamento criados no servidor** — `_create_roles_from_input`/
   `_create_extra_roles_from_orcamento` criam as vagas de apoio (Coordenador/Técnico de
   Som/Maquiador) a partir de `orc_caches`, com `cache_cap`/`cache_cap_note`, independente do que
   o cliente mandar em `characters` (que agora só traz personagens).

**Pegadinhas encontradas (revisão adversarial antes do merge, commit `ce7b66b`).**
- **A catraca do teto**: a primeira versão de `assign_role` somava a parcela do veículo **por
  cima** de `max(cache_cap, valor_já_salvo)` em vez de dentro dele. Como o valor rebaixado vira o
  `old_cache_value` da chamada seguinte, cada "Salvar" empilhava mais uma parcela — um casting
  comum (não-superadmin) conseguia escalar o cachê indefinidamente, em degraus do tamanho da
  parcela do veículo, sem nenhum aviso de "acima do limite" na tela (o `cache_cap_efetivo`
  servido acompanhava a mesma catraca). Corrigido somando a parcela **dentro** do `max` — vira
  ponto fixo: depois de salvo `cap + parcela`, o próximo `max` devolve o mesmo número.
- **O filtro do pré-fill quase matou as vagas de Coordenador/Maquiador**: filtrar
  `characters` por `role_type === "character"` em `EventCreatePage.tsx` (para cumprir a decisão
  4) tirou os extras da lista que o servidor usa para CRIAR `EventRole` — e como
  `came_from_orcamento` continuava `True`, `_apply_default_roles` também pulava a criação de
  fallback do Coordenador. Evento nascido de orçamento passava a sair **sem** vaga de Coordenador
  nem de Maquiador (a de Técnico de Som sobrevivia só por `_ensure_sound_technician`, mas sem
  teto). Corrigido no servidor: `_create_extra_roles_from_orcamento` cria essas vagas a partir de
  `orc_caches` independente do que o cliente mandou.
- **O sync do Google revertendo o tipo pelo prefixo do título**: `aplicar_troca_de_tipo` rodava
  **antes** do push do título ao Google. Se o push falhasse numa troca saindo de SHOW, os
  ensaios já tinham sido apagados de verdade (banco **e** Google Calendar) e as vagas de som já
  tinham sumido — mas o título na Agenda continuava "(SHOW) ...", e o próximo `sync_events`
  reimpunha `event_type = SHOW` a partir do prefixo, religava `needs_rehearsal` e recriava as
  vagas de som, num evento cujos ensaios já não existiam mais. Corrigido invertendo a ordem
  (`_sincronizar_e_trocar_tipo`): título primeiro; falha numa troca com automação desfaz a troca
  e devolve 409 em vez de rodar a parte irreversível às cegas.
- **`travel_cache` apagado por `parse_brl(None)`**: o casting em React nunca manda a chave
  `travel_cache` no `POST /api/roles/<id>/assign` (não edita esse campo nessa tela); sem
  tratamento especial, `assign_role` gravava `parse_brl(None)` = `None` por cima do adicional já
  salvo a cada "Salvar" — apagamento silencioso, decisão 5 da rodada exigia a correção mesmo sem
  o carrinho usar `travel_cache`. Corrigido com o sentinela `_UNSET`: só quem manda a chave
  escreve nela.
- **Reconciliação por título deletando role reservada com e-mail de remoção**: a denylist limpa
  o título antes da reconciliação de `EventRole` a partir dele (`sync_events`, eventos
  `source != "platform"`); sem tratamento, um "COORDENADOR" que saía do texto do título era
  interpretado como personagem removido — a role era apagada e, se tivesse talento, o
  `send_removal_email` disparava "você foi removido do evento" para quem ninguém decidiu
  remover. Corrigido migrando o role reservado para `role_type="extra"` em vez de apagar; o
  script `cleanup_titulos_239.py` já nasce fazendo essa migração junto da limpeza de título.

**Scripts retroativos** (`scripts/db/`, **não executados ainda** — só relatório `--dry-run` até
aqui; exigem `DATABASE_URL` no ambiente e a flag `--execute` para gravar de verdade, liberada só
depois do deploy e com aprovação explícita do João, porque a execução real mexe no Google
Calendar de produção):
- `cleanup_presenca_239.py` — zera `cache_value`/`travel_cache` das vagas de Presença **não
  pagas** (linha já paga fica intacta); relatório prévio por evento/data/pessoa/valor/status.
- `cleanup_show_nao_show_239.py` — eventos **futuros** com `event_type != SHOW`: desliga
  `needs_rehearsal`, remove as vagas automáticas de som (mesmo preenchidas), cancela ensaios
  filhos já agendados (Google incluído) e corrige o prefixo do título, empurrando ao Google
  **antes** da parte destrutiva (mesma ordem obrigatória da correção acima).
- `cleanup_titulos_239.py` — remove segmentos de equipe de títulos já poluídos (todos os
  eventos com `google_event_id`, exceto cancelados/virtuais/ENSAIO) e migra junto os
  `EventRole` reservados de `character` para `extra`, para a própria limpeza não gerar e-mail de
  remoção no sync seguinte.

**Critérios de aceite da rodada**: `npx tsc --noEmit` limpo nos apps tocados, `py_compile` limpo
no backend, migrations encadeadas a partir do head real (`c8f4d92e17ab`), regras do CLAUDE.md
respeitadas (`@manto/money`, `*_ops` puros, RBAC como função, UI pt-BR com feedback TanStack,
Framer Motion 150–350ms com `useReducedMotion`).

### catalogo-fase-1 — item avulso veste ficha própria            (2026-08-18 · migration `c8f4d92e17ab`)

**Motivação.** Levantamento do catálogo real (458 itens, 619 fichas) explicou a confusão de quem
organiza: **só `CatalogCharacter` podia apontar para uma ficha**. Um item sem elenco — Coringa,
Arlequina, Abóbora Maldita, Capitão América — não tinha onde guardar o figurino, e a saída era
criar um "elenco" de UM personagem só, com o mesmo nome, dentro do próprio item. Eram **12
itens** nesse estado, e o efeito vazava para a vitrine: a seção "Elenco Individual" abria com um
card único repetindo a foto da capa. Não era erro de quem cadastrou — era o modelo forçando.

**O que mudou.**
- **`catalog_items.figurino_sheet_id`**: item avulso veste ficha direto.
- **INVARIANTE nova**: item COM elenco é um tema, e tema não veste figurino — a ficha pertence a
  cada personagem. Guardada nos dois sentidos: `catalog_ops.set_item_figurino` recusa ficha em
  tema, e `_require_sem_ficha_propria` recusa montar elenco em item com ficha própria nos
  **quatro** caminhos que criam elenco (`create_character`, `reuse_character`,
  `adopt_item_as_character`, `move_characters` — este último era o furo menos óbvio).
- **Migration achata os 12 auto-temas**: item cujo único personagem tem nome idêntico (sem
  acento/caixa) herda a ficha e o personagem redundante é apagado. Regra deliberadamente
  estreita: os **11** casos de nome só parecido ("Wandinha Addams" contendo "Wandinha",
  "Aracnídeo" contendo "Aranha") NÃO foram tocados — podem ser tema legítimo, e a decisão é de
  quem organiza, pelo botão **"Transformar em item avulso"** (`flatten_to_avulso`). Personagem
  com campanha da Loja Virtual é pulado (`virtual_campaigns.catalog_character_id` é NOT NULL);
  não havia nenhum, mas a guarda fica. Downgrade recria os personagens — simétrico e testado.
- **Gerenciador**: selo **Tema · N personagens** × **Avulso** com a ficha do avulso ao lado; o
  painel do item mostra o campo de ficha (avulso) ou o botão de achatar (tema de um só).
- **Coerência das outras telas**: `list_catalog_characters` passou a incluir itens avulsos como
  aparição (`is_avulso: true`) — sem isso os 12 sumiriam da visão "onde este personagem
  aparece"; e `elenco-busca` expõe `kind`/`figurino_sheet_id` do item, para a tela da Ficha
  mostrar "vinculado ao item avulso X" em vez de "sem vínculo" (as 12 fichas mudaram de dono).

**Pegadinha de payload.** `admin_catalogo_write.py` tinha um `_item_summary` MENOR que o da
listagem. As ações que mudam o tipo do item passaram a responder com `_item_summary_full`
(import local, para não criar circularidade na ordem de registro das rotas) — senão a tela
recebia de volta um objeto sem `kind`/`figurino_sheet_*`, justamente o que acabou de mudar.

**Verificação.** Ensaio da migração destrutiva num banco descartável (`manto_ensaio`, clone do
espelho de produção) rodando o `startCommand` do Railway inteiro: `flask db upgrade` (12
achatados) + `seed.py`; 458 itens intactos, 231→219 personagens, 12 itens com a ficha certa e
fotos preservadas, invariantes zeradas; downgrade devolveu os 231. Depois: 10 checks de regra de
negócio nas ops, 13 checks nos endpoints reais como superadmin, e a vitrine conferida no
navegador (Abóbora Maldita sem a seção redundante e com as 13 fotos; Aladdin com os 6
personagens intactos).

**Fases seguintes (não feitas aqui):** 2) mutirão assistido de vínculos (fichas ligadas ao
catálogo estão em 22%, cargos de evento com ficha em 32%); 3) estoque real (as 619 fichas estão
todas com `quantity = 1`, o default); 4) PDF da vendedora com as fotos do catálogo.

### vincular-na-criacao (hotfix) — personagem já na criação da ficha            (2026-08-17 · sem migration)

O campo "Vincular a um Personagem do Catálogo" (feature 186, `FigurinoCatalogLinkField`) só
existia na EDIÇÃO da ficha — na criação ele sumia porque o vínculo é um PATCH no personagem que
precisa do `sheetId`, que ainda não existe. Mesmo problema que a foto já tinha, mesma solução
(`NewFigurinoPhotoField`): o novo `NewFigurinoCharacterField` guarda a escolha e o submit roda o
vínculo logo após o `POST` da ficha. Decisões: (1) a lista só oferece personagens **sem** ficha —
dar ficha a quem não tem é o caso da criação; trocar a de quem já tem fica na edição, onde o
vínculo atual é visível antes de sobrescrever; (2) escolher o personagem com o nome da ficha
vazio preenche o nome (nunca sobrescreve o digitado); (3) com foto e/ou vínculo pendentes, a
navegação pós-criação vai para a edição, para a confirmação visual dos dois; falha do vínculo
não desfaz a ficha criada.

### fichas-por-escalacao + adotar-item-honesto (hotfixes)            (2026-08-17 · sem migration)

**1. Imprimir fichas do evento: 1 folha por ESCALAÇÃO, não por personagem.** No Transformers do
dia 20, dois talentos vestindo "Soldado" saíam como UMA folha — e a folha imprime o nome e as
medidas de quem veste (`figurino_print.html`), então faltava a folha de um deles. O gatilho real
era o `seen_sheets` do `print_event_figurinos`: qualquer cargo apontando para uma ficha já
impressa era pulado (no caso, os cargos nem tinham o mesmo nome — "…Transformers" e
"…Transformes", com typo — mas compartilhavam a ficha). Reescrito: agrupa por personagem
(identidade = ficha quando existe, senão nome normalizado) e sai uma folha por talento distinto.
Continuam deduplicados: extras, o mesmo talento 2× no personagem, cargo vago quando o personagem
já tem gente (vago sozinho ainda sai como folha anônima) e a herança de ficha entre cargos de
mesmo nome. Verificado contra o `manto_local` (evento 429): 4 folhas, os dois Soldados presentes.

**2. Busca de "Adotar item existente" mostra o bloqueado com o motivo.** A Gabi buscava
"Cinderella" e só via a versão Live Action — a versão Desenho é um TEMA com 9 personagens de
elenco próprio, e a regra da feature 209 (tema não vira personagem de outro tema; item já adotado
não é adotado de novo) a escondia EM SILÊNCIO: "Nenhum item disponível" não distinguia "não
existe" de "existe mas não pode". Agora o item bloqueado aparece na lista, apagado e sem botão,
com o motivo ("É um tema com elenco próprio…" / "Já é a página de um personagem no tema X").
A regra de negócio não mudou — o backend segue validando as mesmas condições.

### cadastro-raiz (hotfix) — `/cadastro` curto no React, Jinja aposentado, upload imune a `ERR_UPLOAD_FILE_CHANGED`            (2026-08-17 · sem migration)

**Motivação.** Uma artista perdeu o formulário inteiro no envio com a tela do Chrome
`ERR_UPLOAD_FILE_CHANGED`: o `<input type="file">` guarda só uma referência ao disco, e o Chrome
aborta o POST se tamanho/mtime mudaram desde a escolha (Google Fotos/Drive reescrevendo o
temporário, HEIC→JPEG descartado pelo iOS, foto editada depois de anexar). Ela estava no
formulário **Jinja** (`/cadastro`), que era o link divulgado — e o React só existia em
`/catalogo/cadastro`, endereço que não faz sentido divulgar (o `/catalogo` é a vitrine de
personagens, não onde alguém se inscreve).

**O que mudou.**
- **`FileUpload` (`@manto/ui`) tira snapshot em memória** no `onChange` (`arrayBuffer` → `File`
  novo) até 24 MB — o `FormData` deixa de apontar para o disco e o erro do Chrome fica
  impossível. Acima de 24 MB (só o Acervo 3D, 50 MB, desktop) segue a referência de sempre.
  De quebra: rejeita acima de `maxSizeBytes` na escolha (antes só o backend barrava, depois do
  upload inteiro) e arquivo ilegível avisa na hora, não no envio.
- **`/cadastro` na raiz é o endereço canônico**, nos dois hosts (`app.` e `portal.`).
  `frontend/server.js` serve o bundle da vitrine nesse prefixo SEM reescrever a URL (não é
  redirect — a barra de endereço fica limpa); `apps/public/src/App.tsx` escolhe o `basename`
  pela URL (`/cadastro/*` roda sem o `/catalogo`). `WishlistFloat` some nessa superfície e o
  link "Ver o catálogo" da confirmação virou âncora absoluta (com `basename` dinâmico, `to="/"`
  cairia no ERP).
- **`/catalogo/cadastro/*` continua vivo de propósito**: os e-mails de confirmação já enviados
  apontam para lá e o token não expira. E-mails novos saem com `/cadastro/confirmar/<token>`.
- **Jinja do cadastro apagado**: `app/cadastro/routes.py`, `templates/cadastro/{form,success}.html`
  e o registro do `cadastro_bp`; `/cadastro` saiu de `BACKEND_PREFIXES` e da exceção do
  `portal_domain_routing`. Sobrou do cadastro no Flask só `/api/cadastro/*` (o `check-cpf` do
  Jinja era rota própria; o React sempre usou o da API).
- **Pegadinha nova no `server.js`**: o host do portal ganhou exceção de redirect para
  `/catalogo/*` — a página de cadastro carrega os assets de `/catalogo/assets/` (o `base` do
  bundle), e sem a exceção cada asset viraria 302 para `/portal/catalogo/...` (página sem JS).
- Copy do erro de rede do formulário deixou de vazar "Failed to fetch".

**Verificação.** `verify-proxy.mjs` (+7 casos: raiz, host do portal, endereço antigo, API) todos
verdes; typecheck limpo nos 3 apps; smoke do Flask lista só as 4 rotas `/api/cadastro/*`;
navegação real no bundle de produção (mobile) com escolha de arquivo simulada e rejeição de
11 MB no campo de 10 MB.

### 235-educamanto (4ª rodada) — Gate fechado: cenário sai, equipe vem dos itens            (branch · 2026-08-17 · migration `b7e3a91d5c24` reescrita)

**Motivação.** Últimas 3 pendências do dono, respondidas de uma vez: (1) o cenário **não tem
custo adicional hoje** e não existe diferença Manto×contratante — "pode tirar por enquanto,
talvez futuramente a gente volte"; (2) personagens×produção **derivam da tabela antiga de
itens** ("3 cara limpa e 5 bonecos = 8 personagens"); (3) frases de alimentação aprovadas.

**O que mudou.** Responsabilidade `cenario` removida por inteiro: dataclass, linha de custo,
colunas `custo_cenario_*` (model + migração), textos/ordem do PDF, card do formulário e tipos
do front. `Responsabilidades.from_dict` ignora chaves desconhecidas — snapshot v2 antigo com
`cenario` carrega sem erro (e o rótulo segue no histórico do front). Derivação na migração:
`num_personagens = Σ qty(Cara Limpa, Bonecos, Papai Noel)`, `num_producao = qty(Produção)`
— resultado: UAA 9+2 · Jardim 8+2 · Onda 7+2 · Unicórnios 5+1 · Turma 8+2 · Natal 6+2 ·
Natal c/ PN 7+2. Valores finais intocados (cenário valia 0): UAA 1d/1s tudo Manto segue
16.700/19.800 (verify_235: 44/44).

**Dois defeitos achados na revisão pré-deploy (corrigidos antes do merge).**
1. **`POST /api/orcamento/settings` ignorava `educamanto_som_luz`**: o handler só copia do corpo
   as seções da allowlist, e o card novo "EducaManto — Som e Iluminação" (criado nesta feature)
   não tinha bloco. A tela salvava, respondia 200, e os campos voltavam sozinhos ao default —
   ou seja, a maior linha de custo do orçamento (R$ 4.200/dia) ficaria travada no hardcode, sem
   nenhum erro que denunciasse. Corrigido com o mesmo padrão do `transporte`.
2. **`GET /api/educamanto/historico/<id>` vazava `transporte.caminhao`** (custo interno,
   R$ 800) no snapshot v2 para Comercial/Ensaio/Revendedor — exatamente o campo que
   `_cortar_breakdown` esconde no cálculo. O corte passou a valer também no histórico. Os v1
   não têm custo interno (conferido nos 34 reais de produção).

**Pegadinhas.**
- **Cenógrafo/Maquiador ficam FORA das contagens** (não são personagens nem produção). O
  headcount antigo do catering os incluía — por isso a derivação anterior (catering −
  produção) dava 1 a mais em Unicórnios/Turma/Natal/Natal c/ PN. Se o dono quiser
  alimentá-los no evento, é ajuste manual no musical.
- "Cenário" continua existindo como palavra para o **cenário de margem** (1S/2S/diárias) —
  só a responsabilidade morreu.
- **Ensaio do deploy antes do push**: o dump de produção foi restaurado num banco descartável
  (`manto_preflight`) e a sequência real do Railway (`flask db upgrade && python seed.py`)
  rodou nele — exit 0 nos dois, 22 pacotes → 7 musicais, e os **34 orçamentos v1 reais
  re-renderizaram o PDF**. Vale repetir isso em toda migração destrutiva.
- O estado pré-migração (22 pacotes, 233 itens, com os custos por nível) foi exportado para
  `backups/educamanto_pre_235_2026-08-17.json` — os `.dump` são podados após 15 dias e essa
  é a única fonte do que cada nível Intermediário/Econômica incluía.

### 238-teto-autorizado — Valor do superadmin vira o teto do papel            (branch · 2026-08-14 · sem migration)

**Motivação.** Caso real na véspera do Baile do Addan: o dono (superadmin) subiu os cachês dos
papéis acima do teto do orçamento; o casting foi escalar as pessoas e não conseguia salvar — o
rebaixamento de não-superadmin usava sempre o `cache_cap` original, derrubando o valor que o
próprio dono tinha acabado de autorizar.

**O que mudou.** Em `casting_ops.assign_role`, o teto para não-superadmin virou o **teto
efetivo** = `max(cache_cap, valor já salvo no papel)` — o invariante segura sozinho, porque só
superadmin consegue deixar salvo algo acima do cap. O aviso do `CastingSection` usa a mesma
regra. Superadmin, papéis sem cap e valores abaixo do cap seguem idênticos.

**Pegadinhas.** O teto efetivo ACOMPANHA o valor vigente: se o casting baixa de 460 para 420,
o teto passa a ser 420 (não dá para voltar a 460 sem superadmin). `verify_238.py`: 9/9 no
manto_local, com evento de laboratório próprio (o espelho é recriado com frequência — não
dependa de dados de verifies anteriores).

### 237-solicitar-ficha — Solicitar ficha pela busca            (branch · 2026-08-14 · sem migration)

**Motivação.** Quando a busca de ficha não tem o personagem, o pedido de criação saía do
sistema (voz/lembrete). Agora a própria busca abre o pedido, que cai na fila que o figurino já
usa (Produção e Compras, feature 225) como o quarto tipo: **Ficha**.

**O que mudou.** `FIGURINO_KIND_FICHA` (sem migração — kind é string) com fluxo curto sem
aprovação (= manutenção); `criar_solicitacao_ficha` reusa `create_producao` (log, e-mail ao
setor); `POST /api/figurino/producoes/solicitar-ficha` com o gate `pode_abrir` de sempre;
transição para `pronto` de kind=ficha **exige `figurino_sheet_id`** (o pedido concluído aponta
para a ficha criada). No front: botão no rodapé do `FigurinoPicker` (dialog pré-preenchido via
`Combobox.onInputValueChange`, prop nova que observa o texto SEM desligar o filtro local),
tipo/filtros nas telas de produção, vínculo da ficha no detalhe. `ElencoBlock` (criar/editar
evento) trocou o Combobox cru pelo picker — restaurando a "porta única" da 225d.

**Pegadinhas.**
- `onQueryChange` do Combobox DESLIGA o filtro local (contrato de busca remota) — por isso a
  prop nova `onInputValueChange`, que só observa.
- O pedido registra a origem (rota) na descrição; decisão de escopo: sem vínculo estruturado
  com evento nesta versão.
- `verify_237.py` (14/14 no manto_local) cria pedidos de teste "TESTE VERIFY 237" no espelho.

### 236-cache-por-duracao — Cachê sugerido pela duração real            (branch · 2026-08-14 · sem migration)

**Motivação.** Caso real (Baile do Addan, evento 1235, 22h–4h): a criação de evento mapeava a
duração com `{"1".."4"}.get(..., 0)` — evento de 6 horas nascia com cachê E TETO (imposto por
`casting_ops` a não-superadmin) de **1 hora**; a tela de criação nem oferecia mais que 4h. O
preço ao cliente escala por hora, o valor das pessoas não escalava junto.

**O que mudou.** `_compute_performer_caches` ganhou `horas_extra`: acima de 4h cada papel de
tabela recebe `cache_custom` = **base de 4h sem adicionais ÷ 4 × horas** + adicionais fixos
(delta de make, noturno de R$ 50 — repasse ao artista —, adicional fora-SP, show customizado);
maquiador não escala (por make). A criação valida `duracao` como int ≥ 1 e, com orçamento
vinculado, **recalcula os cachês no servidor** (fonte única; a lista `orc_caches` do cliente é
só fallback sem orçamento). `/events/new` ganhou "Outra (h)". **2ª rodada (mesmo dia)**: o
cachê passou a NASCER VAZIO — o valor da régua vira só o `cache_cap` invisível (decisão de
incentivo: personagens têm horários distintos não modelados de propósito, a venda cobra a
duração cheia como margem, e expor sugestão ancoraria o casting no máximo — quem escala pode
se escalar). O aviso "abaixo do sugerido" foi adicionado e removido nesta mesma rodada. Preço
ao cliente intocado.

**Pegadinhas.**
- Gabarito real: orçamento 1806 em 6h → Green 520 / Space 500 / Coordenador 575 (verify_236,
  14/14 no manto_local; evento de teste 1236 criado só no espelho local).
- O teto de 400 do evento 1205 (mascotes) não incluía o adicional fora-SP — a função de hoje
  dá 467; o gabarito de paridade é a função, não caps antigos.
- O dublê `run-local-sem-google.py` NÃO cobre o `insert_event` importado dentro de
  `api_create_event` (import tardio de `app.calendar.routes` — este está patchado; conferir se
  o servidor local usado é mesmo o script dublê, o launcher pode ter config em cache).

### 235-educamanto (3ª rodada) — Valores reais de som/iluminação            (branch · 2026-08-14 · migration `b7e3a91d5c24` reescrita)

**Motivação.** O dono entregou `EspecificacoesEducamanto.md` com os valores e riders reais dos
4 casos de som/iluminação — e eles NÃO são aditivos (som+luz 4.200 < 750 + 2.150 + 2.150), com
a equipe técnica já dentro. O modelo por blocos independentes + técnicos avulsos foi
substituído por **tabela única por combinação** em `pricing_config['educamanto_som_luz']`
(4.200/2.900/2.900/750), custo com margem em cima, cobrado POR DIA de evento. As 12 colunas
`custo_som_*`/`custo_iluminacao_*` saíram do musical (migração reescrita — ainda não aplicada
em produção); os PROVISÓRIOS de técnicos e áreas morreram; os riders viram os textos reais do
PDF e a cobertura (≈300 m²/150 pessoas) é impressa só quando o som é da Manto. Editável na
tela de Configurações de Preços. Gabarito novo: UAA 1d/1s tudo Manto = 16.700/19.800
(verify_235: 36/36). **Gate restante**: custo do cenário + divisão personagens×produção.

### 235-educamanto — EducaManto por responsabilidades            (branch 235-educamanto-responsabilidades · 2026-08-13 · migration `b7e3a91d5c24`)

**Motivação.** Os pacotes por nível (Master/Intermediário/Econômica) engessavam a venda: o
cliente que queria o espetáculo completo com a própria iluminação não cabia em nenhum pacote.
O dono pediu a reestruturação completa (conversa de 13/08/2026, esteira SDD completa em
`specs/235-educamanto-responsabilidades/`).

**O que mudou.**
- **Musicais** (`educamanto_musicals`, rename com ids preservados) substituem os 22 pacotes; a
  migração poda Intermediário/Econômica/cópia órfã e move Som/Catering/Transporte para colunas
  ou regra. `Recalcular` de snapshot v1 mapeia por id preservado ou prefixo do nome.
- **Responsabilidades** som/iluminação/alimentação/cenário (Manto×contratante) ligam/desligam
  blocos de custo; **matriz técnica** de 4 casos (sonoplasta fixo); headcount de ensaio
  (personagens+produção+ensemble) ≠ headcount do evento (+técnicos).
- **Fechamento preservado** (margens, desconto>3d, teto do acréscimo, ceil100, ÷0,84); novo:
  ensaios ×`num_ensaios` (mín. 2, **não** escalam com dias do evento), caminhão SP R$ 800
  (`pricing_config['transporte']['caminhao_sp']`), fora de SP 2 vans + adicional por pessoa 1×,
  à vista −5% **calculado** (era só texto no PDF).
- **Snapshot v2** multi-configuração **recalculado no servidor** (fim da confiança no payload
  do cliente); v1 re-renderiza intacto. PDF v2 por configuração com "o que levaremos"/"mínimo
  exigido", avisos fixos (palco 5×4, camarim=headcount, som área X/Y, visita técnica), dias
  zerados ocultos, observação com transbordo.
- **Contratação Manto embutida**: reusa `app.orcamento.quote_ops.calculate_quote` com
  `nota_fiscal=False`/`fora_sp=False`; NF única sobre a soma por duração (FR-016).
  `PerformersEditor`/`AcrescimosEditor` extraídos de `OrcamentoCalculadoraPage` para
  `components/orcamento/` (fonte única, render idêntico).
- **RBAC**: breakdown/custos cortados **no servidor** para não-superadmin (`_cortar_breakdown`);
  tela de musicais mostra custos só a superadmin.
- **Jinja do EducaManto desligado**: templates removidos, rotas viram 301 para o SPA — morre a
  réplica JS da fórmula (que divergia do Python no transporte e no headcount).

**Regras de negócio novas.** Nível não existe mais em lugar nenhum (fim da detecção por
substring no nome); alimentação da contratante é negociada com o vendedor; camarim obrigatório.

**Pegadinhas.**
- `PROVISORIO` (grep) em `pdf_textos.py` + colunas de iluminação/cenário zeradas + divisão
  personagens×produção dos musicais ≠ UAA: **gate de deploy** — dono ainda envia os valores
  (técnicos, áreas X/Y do som) e revisa os textos.
- O default do model `discount_days` virou 3 (paridade com produção; era 2 e pacote novo
  nascia diferente).
- `verify_235.py` (specs/235) roda 34 checagens contra `manto_local`, incluindo re-derivação
  independente da fórmula; a senha local do SUPERADMIN agora é `verify-235-senha`.
- Havia colisão de numeração: a migration `f4a8d61c9e27` (quantidade de figurinos) se dizia
  "feature 235" no docstring — esta entrada usa **235-educamanto** para desambiguar.

### 225g — Fotos já na abertura do pedido, nos três tipos            (main · 2026-08-12 · sem migration)

**Motivação.** *"Gostaria que nos 3 modos de input fosse possível adicionar fotos: opcional, pode
adicionar mais de uma, importante essas fotos seguirem o padrão de compressão para não pesar
tanto."*

**O que faltava.** Anexar foto só existia **depois** de o pedido ser criado, na tela de detalhe —
e lá o anexo passa por `pode_executar_pedido`. Ou seja: quem abria o pedido (comercial, casting)
muitas vezes não conseguia anexar nada ao próprio pedido. A foto do defeito, que é o enunciado da
manutenção, ficava de fora justamente de quem a tinha no celular.

**Onde ficou.** Logo abaixo do campo de detalhes, nos três tipos. É continuação do enunciado
("é este defeito", "é esta peça"), não anexo administrativo no fim do formulário.

**A criação trocou de contrato: JSON → `multipart/form-data`.** O formulário passou a carregar
arquivo, e manter os dois caminhos seria dois contratos para a mesma rota. Consequência a
lembrar: **todo campo chega como string**. Os resolvedores já tratavam ausente e `""` como "sem
valor", mas engasgariam com a string `"null"` — por isso o front **omite** campo vazio em vez de
mandar `null`. O teste 2 do verify confere um pedido com todos os campos preenchidos, um por um,
porque uma regressão aqui perde evento/prazo/responsável **em silêncio**.

**Validação antes de criar.** `validar_fotos` roda com o pedido ainda inexistente: se a terceira
foto for um `.exe`, o pedido inteiro é recusado e nada é salvo. O contrário — pedido salvo com
duas fotos e uma mensagem de erro — deixaria lixo que ninguém iria limpar.

**Uma linha de histórico, não N.** `add_fotos_iniciais` não reusa `add_anexo` de propósito: N
fotos gerariam N linhas "Foto do andamento." embaixo da linha de abertura, dizendo a mesma coisa
N vezes. As fotos aparecem na grade de Fotos, e o histórico ganha "3 fotos anexada(s) na
abertura.".

**Compressão: a do app, sem inventar outra.** `storage.save_file` já reduz para 1200px de lado
máximo e JPEG qualidade 85. Medido no verify: **3000×2000 / 286 KB → 1200×800 / 26 KB**. E no
navegador, com duas fotos de 2400×1600 vindas do formulário real: **1200×800, 74 KB cada**.

**Bug pego pelo próprio teste.** `FIGURINO_ANEXO_FOTO` não estava importado em `producao_ops` —
`NameError` na primeira foto. Passou pelo `py_compile` porque só quebra em execução.

**FURO CONHECIDO — `.heic` não é comprimido.** `FOTO_EXTENSIONS` aceita `.heic`/`.heif` (formato
nativo do iPhone), mas `_COMPRESS_EXTS` do `storage` é só `{jpg, jpeg, png, webp}`: o
`_compress_image` devolve `None` na porta e o arquivo original é gravado inteiro. Medido: **900 KB
sobem, 900 KB ficam.** Isto é **anterior a esta feature** e vale para todo upload do app, não só
aqui. Na prática o iOS Safari costuma transcodificar para JPEG em upload web, então o caso comum
não é atingido — mas um `.heic` vindo de um Mac passa direto. Fechar isso exige `pillow-heif` no
`requirements.txt` (dependência nativa, com risco de build no Railway) e acrescentar as duas
extensões a `_COMPRESS_EXTS`. **Decisão pendente do cliente**, por isso não foi feito junto.

**Verificação.** `scripts/db/verify_fotos_na_abertura.py` contra `manto_local` — **41/41**:
foto opcional nos três tipos, multipart preservando todos os campos, campo omitido virando nulo,
a redução de 3000×2000 medida no arquivo salvo em disco, três fotos com uma linha só de
histórico, `.exe` barrando o pedido inteiro sem deixar órfão, campo de upload vazio não criando
anexo fantasma. Regressões: `verify_producao_figurinos.py` 70/70 e `verify_pedido_compra.py`
64/64. No navegador, o fluxo real com `DataTransfer` no input.

### 225f — Um menu só para produção, manutenção e compra            (main · 2026-08-12 · sem migration)

**Motivação.** *"Não estou vendo a necessidade de 2 menus diferentes. Acho melhor unificá-los."*
Está certo, e a 225c é que tinha errado: ela criou "Pedidos de Compra" como item separado no
mesmo dia em que decidiu que a compra seria o **terceiro `kind` da mesma tabela**. Dois itens de
menu para uma tabela só é porta duplicada — o usuário tem de escolher a porta antes de saber que
as duas dão no mesmo cômodo.

**O que ficou.** Um item, **"Produção e Compras"**, em `/figurinos/producao`. O rótulo cita a
compra de propósito: com um menu só, ele é o único letreiro que ela tem, e ninguém procurando
onde pedir uma compra clicaria em "Produção de Figurinos".

**A aba mudou de lugar — foi para a URL.** Era `useState`; virou `?tipo=`. Isso é o que permite
`/figurinos/producao?tipo=compra` ser um link de verdade: o item de menu que morreu virou esse
link, e é para ele que **`/compras` redireciona** (`<Navigate replace>`) — a rota já circulou em
favoritos, e é ela que mantém "abrir direto nas compras" possível de qualquer lugar. A troca de
aba usa `replace`, para quatro cliques não deixarem quatro paradas no botão Voltar.

**A aba ativa pré-seleciona o tipo no diálogo** de "Novo pedido" — quem está em Compras e clica
já encontra "Comprar" marcado. Mas o seletor dos três **deixou de ser escondível** (`tipoFixo`
virou `tipoInicial`): com um menu só, é ali que a pessoa descobre que existe pedido de compra.
Sugestão, não trava.

**O que não mudou.** Nada de backend, nada de banco: os três tipos, os três fluxos, o RBAC e o
detalhe compartilhado (`/figurinos/producao/:id`) seguem como a 225c os deixou. Isto é
navegação. O breadcrumb do detalhe é que passou a voltar para a aba de origem.

**Verificado no navegador**: `/compras` → `/figurinos/producao?tipo=compra` com a aba Compras
ativa; cada aba escrevendo seu `?tipo=` e trocando os chips de situação junto (Compras mostra
"Comprados/Recebidos", Manutenção esconde "Aprovados"); "Tudo" limpando o parâmetro; e o deep
link `?ficha=` continuando a cair em Manutenção com a faixa "Mostrando só o figurino".

### 225e — Hotfix: menu "Ferramentas" cortado atrás da barra lateral            (main · 2026-08-12 · sem migration)

**Sintoma.** No detalhe do evento, o menu "⋯ Ferramentas" abria com o texto cortado no meio da
palavra ("cronizar", "ortar elenco", "firmar dados do"). Relatado como *"não acontece na minha
tela que é gigante, mas na tela de outros usuários tá cortado"* — e essa frase é o diagnóstico.

**Não é o 220b de volta.** Aquele era empate de `z-index` com a régua de abas, e o sintoma era
uma faixa horizontal embaçada no meio do menu. Este corta na vertical, sempre do lado esquerdo, e
tem outra causa.

**Causa.** O painel era `absolute right-0`: ancorado à direita, ele **cresce para a esquerda**. O
cabeçalho do evento é `flex flex-wrap justify-between` — em tela larga o grupo de ações fica na
mesma linha do título, lá na direita, e há espaço de sobra à esquerda. Quando a largura aperta (ou
o título é comprido, como o do relato, com três personagens), o grupo **quebra para a linha de
baixo e vai para o começo do conteúdo**. Aí o painel de 208px cresce a partir de x=403 para trás,
chega em x=195 — e a área de conteúdo só começa em 256, porque a barra lateral é
`fixed left-0 w-64 z-40`. Os 61px que sobram não saem da tela: ficam **atrás** da barra, que
ganha de `z-30` do painel por ter z maior. Daí o texto começar no meio da palavra.

**Medição (antes).** vw=1280: gatilho `[280,403]`, painel `[195,403]`, `main.left=256`,
61px escondidos, e `elementFromPoint` no ponto do primeiro item devolvendo o `NAV` da sidebar.

**Correção.** O lado da abertura passa a ser medido. `useLayoutEffect` (antes da pintura, para não
piscar do lado errado) compara a largura do painel com o espaço até a borda da **área de
conteúdo** — lida do DOM via `closest("main")`, e não repetindo os 256px em número, para não sair
de sincronia com o `lg:pl-64` do `AppLayout`. Não cabendo à esquerda e cabendo à direita, o painel
vira `left-0`. Sem espaço dos dois lados, fica no padrão da direita.

Subir o painel para `z-50` resolveria o corte e criaria coisa pior: um menu flutuando por cima da
navegação. O que estava errado era o lado, não a camada.

**Medição (depois).** vw=2560 → âncora direita, painel `[547,755]`, 0px escondidos (o
comportamento de antes, preservado). vw=1920/1280/1100/900 → âncora esquerda, 0px escondidos,
**0 de 10 itens cobertos** em todas. Kebabs de ícone do catálogo (o uso original, na ponta direita
do card) seguem abrindo para a esquerda, 0 cobertos.

**Pegadinha de quem for medir isto de novo.** Na aba Árvore do catálogo os kebabs dos nós
recolhidos continuam no DOM dentro de um contêiner `overflow-hidden` com `height:0` e
`opacity:0`. Abrir um deles por script dá um menu "coberto" que **não é bug nenhum** — é um menu
dentro de um nó fechado. Filtre com `checkVisibility({ checkOpacity: true })` antes de concluir
qualquer coisa.

### 225d — Espaçamento padrão nas telas coladas na sidebar, e uma só busca de figurino            (main · 2026-08-11 · sem migration)

**Motivação.** Dois relatos: *"todas as páginas têm uma distanciazinha da barra lateral, essa está
sem"* (apontando a Produção de Figurinos) e *"preciso que absolutamente todos os lugares que
tenham busca de figurino sigam o padrão de outras páginas"*.

**Espaçamento.** `AppLayout` renderiza `<main className="min-h-screen">` **sem padding**: o
espaçamento é de cada página. A auditoria das 57 achou **6** sem ele — Produção de Figurinos
(lista e detalhe) e as quatro telas de Interações Virtuais; as outras 51 já usavam `p-4 sm:p-6`.
Todas passaram para `mx-auto max-w-<X> space-y-N p-4 sm:p-6`. Os ramos de **carregando e de erro**
levam o mesmo invólucro — senão o esqueleto nasce deslocado e a tela pula quando os dados chegam.
Medido: `paddingLeft=24px` e conteúdo em `left=256px` nas seis, igual à Agenda.

**Busca de figurino.** Havia três aparências para a mesma tarefa: o `<select>` cego do pedido de
figurino/compra, o `FigurinoSheetPicker` (209, lista própria) e o `FigurinoPicker` (215,
`Combobox` do design system). Ficou só o último, promovido de `components/EventDetail/` para
`components/`; o `FigurinoSheetPicker` foi apagado e seus 4 usos no catálogo migraram (a API dos
dois já era a mesma; `ariaLabel` virou opcional com o default antigo). `fichaId` do
`NovoPedidoDialog` deixou de ser string e virou `number | null`, o que dispensou o `fichaOptions`
e as conversões na borda.

O `Combobox` já traz filtro sem acento, teto de 30 resultados, limpar e teclado — o picker da 209
reimplementava tudo isso à mão. São 616 fichas (612 com foto): lista alfabética é inviável e a
escolha é visual, daí a miniatura quadrada (Princípio X.2).

**Pegadinha.** No `Combobox`, `role="option"` fica no `<li>` mas o `onClick` mora no `<button>` de
dentro. Testar com `document.querySelector('[role=option]').click()` não seleciona nada e o campo
volta nulo **em silêncio** — o que quase virou um bug reportado que não existia. Use
`[role=option] button`.

A tabela de onde o `FigurinoPicker` aparece está em `docs/02` → "Padrões transversais do app
interno", junto com o padrão de espaçamento.

### 225c — Pedido de Compra, e a Revisão movida para Marketing            (main · 2026-08-11 · sem migration)

**Motivação.** Três pedidos numa mensagem só: *"essa revisão deve estar em marketing"*; *"a
produção de figurinos deve ser acessível para o comercial, figurino e casting"*; e *"novo pedido
de compra — onde a pessoa pede o que precisa ser comprado, coloca o prazo, coloca pra qual
figurino (ficha) e qual evento está associado (opcionais), e coloca quem é o responsável"*.

**O segundo pedido não virou código.** Conferido antes de mexer: o item "Produção de Figurinos"
já era `isVisible: notRevendedor` (todo papel interno) e `producao_ops.pode_abrir` já liberava a
leitura e a abertura de pedido para qualquer papel interno. Comercial, Figurino e Casting já
tinham acesso — restringir a exatamente esses três tiraria Financeiro, Ensaio, Marketing e
Artista 3D, que hoje veem. Perguntado, o cliente decidiu **deixar como está**.

**A decisão do Pedido de Compra: terceiro `kind`, não tabela nova.** A alternativa (módulo
"Compras" próprio) foi oferecida e recusada. O objeto é literalmente o mesmo da 225 — uma coisa a
fazer, com prazo, responsável, histórico, anexos, vínculo opcional a evento e a ficha, e vínculo
com Gasto Extra. Reusar deu **zero migration** (`kind` e `status` são `String(20)` sem CHECK) e
trouxe de graça o convite no Google Agenda, o painel pessoal da home, os orçamentos comparados e
a soma de gasto aprovado. O preço, explícito: o pedido nasce dentro do módulo de figurino, e é
por isso que ele ganhou **rota própria** (`/compras`) em vez de viver só como uma aba —
comprar tinta de cenário não é assunto da oficina, e obrigar a passar pela fila dela para achar
onde pedir esconderia a porta de entrada.

**O fluxo.** `solicitado → aprovado → comprado → recebido`, com `cancelado` como saída. Entrou
como mais uma lista em `FIGURINO_PROD_FLUXOS`; as transições continuam **derivadas** dela por
`_transicoes_do_fluxo`, sem segunda tabela. Duas escolhas que valem registro:
- **`comprado` é estado ABERTO.** O dinheiro saiu, a coisa não chegou — e é exatamente esse
  intervalo ("comprei, prometeram para sexta") que hoje se perde. Fechar ali apagaria o que
  ainda falta acompanhar.
- **O estado final feliz virou `_fluxo_de(p)[-1]`.** Antes `mudar_status` listava
  `FIGURINO_PROD_PRONTO` na mão para carimbar `done_at`; com três fluxos isso seria a próxima
  coisa a esquecer. Derivar do fluxo faz o carimbo seguir sozinho quando um quarto tipo nascer.

**A regra de permissão que a feature obrigou a criar.** `pode_executar` (FIGURINO/SUPERADMIN) não
serve para compra: quem pede a pedraria e vai buscá-la costuma ser do comercial. Com a regra
antiga, um pedido entregue ao Comercial travaria em "aprovado" para sempre e a feature não
serviria para nada. Nasceu `pode_executar_pedido(user, producao)`, que soma **o responsável pela
própria compra** — e **só em compra**: o teste `verify_pedido_compra.py` §3 existe para provar
que a exceção não vaza para produção (um responsável de produção fora da oficina continua
recebendo 403). Consequência de contrato: `flags.can_execute` do endpoint de detalhe passou a ser
avaliado **para aquele pedido**, não para o usuário em abstrato.

**Aprovar continua sendo só de SUPERADMIN**, inclusive aqui — é o único ponto em que alguém olha
o dinheiro antes de sair, e foi a decisão do cliente ao escolher "com aprovação".

**Onde o ruído foi cortado.** Compra sem responsável avisa **só o Superadmin**
(`equipe_figurino(kind)`) e entra na caixa de entrada do setor apenas para quem aprova
(`resumo_setor`). Mandar "tinta de cenário" para a costureira transformaria o aviso em ruído, e
aviso ignorado deixa de ser lido — mesma lógica que a 225b já aplicava à gravidade. Pelo mesmo
motivo os e-mails ficaram cientes do tipo: um pedido de compra que chega dizendo *"você ficou
responsável por produzir"* manda a pessoa fazer a coisa errada.

**A Revisão em Marketing — e o efeito colateral que se aceitou.** O item saiu da seção "Produção"
e foi para "Marketing", entre "Metas de Frequência" e as Interações Virtuais. Ele mantém
`isVisible: notRevendedor`, e **isso muda quem vê a seção**: como os outros cinco itens de
Marketing são gateados por papel, "Marketing" só existia no menu para
`MARKETING`/`COMERCIAL`/`CASTING`/`SA`; agora aparece para todo papel interno, com "Revisão"
dentro. A alternativa — gatear a Revisão por papel — foi descartada porque quebraria o produto:
`review_ops.can_view` libera qualquer pessoa que esteja em `space.reviewer_ids`, e
`GET /api/revisao/reviewer-options` oferece **qualquer usuário ativo** como revisor. Um convidado
do financeiro perderia a única porta de entrada (a rota `/revisao` não tem guard próprio).

**Verificação.** `scripts/db/verify_pedido_compra.py` contra `manto_local` — **64/64**: o ciclo
inteiro com histórico a cada passo, `comprado` contando como aberto, o retorno de `recebido` para
`comprado` limpando `done_at`, RBAC dos três recortes (Revendedor não abre; Figurino não aprova;
nem o responsável aprova a própria compra), a exceção do responsável não vazando para produção,
`?tipo=compra` na lista de responsáveis, os painéis da home e a trava do Google. Regressão da 225
rodada junto: `verify_producao_figurinos.py` **70/70**. Na tela, o fluxo de ponta a ponta com o
banco real: criar pelo formulário → Aprovado → Comprado → Recebido, com o breadcrumb voltando
para `/compras` e os botões vindo de `transicoes`.

### 235 — O mesmo personagem em vários temas, e quantos figurinos existem dele            (main · 2026-08-11 · `f4a8d61c9e27`)

**Motivação.** Relato: *"foi criado no [tema] normal os personagens Gatuno e Pandy; porém, ao
tentar adicionar os mesmos personagens no Gabby humanizada, não aparece como uma opção"* — e o
pedido de uma terceira visão listando os personagens já criados, mostrando se têm ficha e em
quantos temas são usados, "pra dar uma noção de progressão". Mais: poder marcar na ficha **quantos
figurinos iguais** existem.

**Por que não aparecia.** `CatalogCharacter` é linha-filha de UM tema (`catalog_item_id NOT NULL`).
O único reuso que existia — "adotar item existente" (209, caso Coelho→Alice) — exige que o
personagem seja um **produto com página própria**; Gatuno não é item, é linha de elenco, então a
busca não tinha o que oferecer. Não era bug: a capacidade nunca existiu.

**A decisão de modelo: a identidade de um personagem é a FICHA DE FIGURINO.** Duas linhas de
`CatalogCharacter` apontando para a mesma ficha são o mesmo personagem em dois temas. Foi escolha
consciente contra criar uma entidade "Personagem" nova: a ficha já é a âncora do resto do ERP
(elenco do evento, alerta de "sem ficha", manutenção, produção), e um terceiro cadastro seria uma
segunda verdade sobre quem é o personagem — com nome e foto para manter em sincronia. O preço é
explícito e está na tela: **personagem sem ficha não pode ser reaproveitado**, porque não há o que
afirme que dois personagens de temas diferentes são o mesmo. Isso vira a pendência que o termômetro
mostra (10 dos 38 hoje).

Cada aparição continua sendo uma linha própria — nome, foto, vídeo e ordem podem diferir de tema
para tema, e mexer numa não mexe na outra. Nenhuma coluna nova foi precisa para isso: o `slug` já
é prefixado pelo tema (`unique_character_slug`), e nada impedia duas linhas com a mesma ficha.

**O que o banco disse antes de eu escrever qualquer coisa.** 39 personagens em 458 temas, 29 com
ficha, **0** com página própria, **0** reuso — o cadastro está no começo, então dava para escolher
o modelo certo sem backfill. E **616 fichas cadastradas contra 28 ligadas ao catálogo**: é isso que
define o desenho da aba nova. Ela **não** lista uma linha por ficha (isso é o Banco de Figurinos,
que já existe em `/figurinos`); lista os personagens **do catálogo**, e mostra as 588 fichas de
fora como número de progresso. Quem alcança o acervo inteiro é a busca de reaproveitar.

**Tema ≠ aparição.** Descoberto nos dados durante a verificação: a ficha 488 (Astronauta) é usada
por "Astronauta 1" e "Astronauta 2" **no mesmo tema** — dois performers do mesmo figurino no mesmo
show. A primeira versão do agrupamento contava isso como "em 2 temas". A estrutura passou a ser
`temas: [{tema_id, aparicoes: [...]}]`, o chip do tema mostra `×2`, e daí saiu o alerta que só
existe porque as duas informações ficaram na mesma linha: *"um tema pede 2 ao mesmo tempo, temos
1"*.

**Quantidade na ficha** (`figurino_sheets.quantity`, padrão 1). Não confundir com o `qty` de dentro
de `pieces` — aquele é "2 luvas" DENTRO de um figurino; este é "temos 3 Gatunos". Zero é válido e
significa ficha cadastrada de figurino ainda não produzido (o pedido vive em `figurino_producoes`).
`edit_sheet(quantity=None)` é "não alterar", e não "zerar": o formulário Jinja legado não conhece a
coluna e não pode apagá-la só por não mandá-la.

**Onde ficou.** Terceiro botão 🎭 Personagens ao lado de Cards e Árvore (as duas olham pelo produto
e pela hierarquia; esta olha pelo personagem). No modo Personagens a busca é client-side de
propósito — a lista de temas precisa vir inteira, porque é dela que sai o "usar em outro tema".
Dentro do tema, "Reaproveitar personagem que já existe" vem ANTES de "Novo personagem", reusando o
`FigurinoSheetPicker` (busca visual nas 616 fichas).

**Verificação.** `scripts/db/verify_235_personagens_reuso.py` contra `manto_local`: quantidade no
POST/PATCH/listagem (incluindo PATCH sem o campo preservando o valor, e zero aceito), reuso criando
a segunda aparição com a mesma ficha e slug diferente, recusa com mensagem útil ao repetir no mesmo
tema, a aba agrupando as duas aparições numa linha só, o caso Astronauta e o personagem sem ficha
como pendência. Na tela, roteiro Playwright sobre harness temporário com os dados REAIS do banco:
38 linhas, termômetro, filtros, e o fluxo do pedido de ponta a ponta — buscar "gatuno" → "Usar em
outro tema" → "A Casa Mágica da Gabby (Humanizada)" → `POST {"figurino_sheet_id": 509}`.

### 234 — Trocar fotos de lugar no catálogo: a ordem que nunca era salva, e a grade refeita            (main · 2026-08-11 · sem migration)

**Motivação.** Relato do usuário: *"o esquema para trocar as fotos de lugar está ruim, preciso de
um design melhor disso — além de que ao trocar e salvar, não está mudando."* As duas queixas eram
o mesmo assunto por dois lados: a interação era ruim **e** o resultado dela era descartado.

**A causa do "salvei e não mudou".** `catalog_ops.apply_photos` só gravava `position` **dentro do
`if cover is not None`**. A capa vinha de `cover_photo_id`/`new_photo_cover_index`, e o formulário
React nunca mandava nenhum dos dois: `coverPhotoId` nascia `undefined` e não era hidratado do item.
Então numa edição que **apenas reordenava**, `cover` ficava `None`, a lista `remaining` era
reordenada só em memória e o commit não escrevia posição nenhuma — 200 na API, nada no banco. O
formulário Jinja legado escapava por acidente: o radio de capa tem `{% if loop.first %}checked`, ou
seja, sempre manda `cover_photo_id`. Foi por isso que `verify_142` passava: ele manda a capa
explicitamente. **Regra nova: a posição é sempre regravada no fim, com ou sem capa explícita.**

**A capa deixou de ser um campo.** O banco já dizia que capa é `images[0]` (`CatalogItem.cover_image`),
mas a tela pedia as duas coisas em separado — dava para arrastar uma foto para a frente e a capa
continuar sendo outra. Agora **a primeira foto é a capa**, e "★ Tornar capa" é só um atalho de
"mover para a 1ª posição". O React não manda mais `cover_photo_id` nem `new_photo_cover_index`; o
backend continua aceitando os dois (o Jinja legado depende deles).

**`photo_order` virou lista de tokens.** Cada item é o id de uma foto salva **ou** `new:<i>`,
apontando para o i-ésimo arquivo de `new_photos` — é o que permite uma foto recém-escolhida cair no
**meio** das antigas (antes toda foto nova ia para o fim, obrigatoriamente). Quando a ordem cobre
todas as fotos ela é soberana; quando é parcial (o Jinja, que só lista as existentes) a regra antiga
da 141 continua valendo, inclusive a de promover a primeira foto nova a capa.

**A grade (`CatalogPhotoManager`).** Fotos salvas e novas numa **grade só**, com selo de ordem,
"CAPA" na primeira e "nova" nas não salvas. O arraste saiu do **HTML5 drag-and-drop** (que não
funciona no toque, não anima e não mostra onde a foto vai cair) para o **arraste por ponteiro do
Framer Motion** — o mesmo padrão do quadro de Marketing, com `viewportPoint`/`attributeAtPoint`
agora extraídos para `lib/pointerDrag.ts`. As vizinhas se reorganizam **ao vivo** por baixo do dedo.
Também entraram: botões ‹ › ★ ✕ por foto (teclado/toque), remoção pendente com desfazer, soltar
arquivos do desktop na grade e o selo "alterações não salvas".

**Duas armadilhas do arraste, ambas custaram uma rodada de verificação.**

1. **O card arrastado tapava o próprio alvo.** `elementsFromPoint` devolve a pilha inteira, e o card
   em arraste está por cima com `z-index` do `whileDrag` — como ele também é uma zona de soltura,
   o hit-test respondia sempre "ele mesmo" e nada nunca se movia. Correção: `pointer-events: none`
   no card enquanto ele é arrastado (o gesto sobrevive porque o Framer escuta a `window`).
2. **`onDrag` dispara a cada quadro, não a cada movimento.** Medir as vizinhas ao vivo lia caixas no
   meio da animação de troca, e a foto oscilava entre duas posições — soltava um lugar antes do
   pretendido. Correção: as células da grade são medidas **uma vez**, no `onDragStart`, em
   coordenadas de página (a grade tem sempre o mesmo número de espaços; o que muda é quem ocupa
   cada um).

**Adoção de foto por personagem** (arrastar da galeria até o personagem) continua existindo, mas a
mutação subiu para `AdminCatalogoFormPage`: quem detecta o alvo agora é o card arrastado, e o painel
só recebe `photoDropTargetId`/`adoptingCharacterId`/`photoDropError` para desenhar realce, spinner e
erro.

**Verificação.** `scripts/db/verify_catalogo_fotos_ordem.py` contra `manto_local`: criação com
tokens, **PATCH que só reordena e sem campo de capa** (o bug), foto nova intercalada por `new:0`,
remover+reordenar no mesmo salvamento e o caminho Jinja legado com capa explícita. Na tela, roteiro
Playwright sobre um harness temporário (cache do TanStack pré-carregado, sem login): reordenação ao
vivo, ordem após soltar, ‹ ›, ★, remover/desfazer, realce do personagem, mobile sem rolagem
horizontal e o corpo do multipart enviado ao salvar.

### 233 — Coordenadora sem ver o figurino, e o convite que nunca era enviado            (main · 2026-08-11 · sem migration)

**Motivação.** Relato: a coordenadora do evento 1192 entra nele pelo portal e **não consegue ver os
figurinos**; e na tela interna o cargo dela não aparece como aceito nem como pendente. A hipótese
do usuário: *"imagino que tenha faltado o pessoal do casting clicar em convidar — mas acho que
podemos nos blindar disso. Talvez quando preencherem a pessoa e o valor, automaticamente
convidar."* A hipótese estava certa na origem e errada no culpado — ninguém esqueceu de clicar,
porque **nenhuma tela pedia o clique**.

**Duas causas empilhadas.**

**1. Regressão da 230 (minha).** A 230 trocou a regra da agenda e do histórico para
`nao_recusada()` — mas `get_figurino` ficou com a trava antiga, `invite_status.in_(["accepted",
"pending"])`. Como o cargo dela tem `invite_status = NULL`, o resultado foi o pior dos dois mundos:
a 230 passou a mostrar o evento na agenda **com** o link "Ver ficha de figurino", e o link caía em
403 *"você não está escalado neste evento"*. Antes da 230 o evento não aparecia, então o link
morto não existia — eu criei o caminho e esqueci de abrir a porta no fim dele. Reproduzido e
corrigido: agora ela vê as 2 fichas do elenco (Mulher Algodão Doce → Mel Gomes, Mulher Sorvete →
Iara Oliveira).

**2. O cargo nasce com pessoa e sem convite.** A tela de casting **já** convidava sozinha
(`assign_talent_to_role` marca `pending` e dispara o e-mail desde sempre). O que não convidava eram
os dois caminhos que montam o elenco **junto com o evento**: `_create_roles_from_input` /
`_apply_default_roles` na criação e `_reconcile_characters` na edição. Eles gravavam `talent_id` +
`assigned_at` e paravam ali. É a origem dos 26 cargos futuros sem convite que a 231 mediu — e o
efeito era invisível dos dois lados: para a produção o cargo parecia resolvido; para a pessoa, o
evento não existia.

`casting_ops.convidar_recem_escalados()` passa a ser chamada nos dois caminhos, depois do commit,
usando a **mesma lista** `assigned_now` que eles já montavam para avisar de conflito de horário —
ou seja, a lista que sabe quem é realmente novo.

**Não exijo o cachê preenchido, ao contrário do que o pedido dizia ao pé da letra.** A pré-escala do
**coordenador** não tem campo de cachê (`_apply_default_roles` cria o cargo só com `talent_id`), e
era exatamente esse o caso que originou o relato: gatilho em "pessoa **e** valor" deixaria a
Miminha de fora outra vez. A regra virou "pessoa escalada, evento no futuro" — a mesma da tela de
casting, que também não olha o cachê. O e-mail de convite já omite a linha do valor quando ele
ainda não existe.

**Travas do convite automático.**

- **Só cargo sem convite nenhum** (`invite_status IS NULL`): quem está `pending`, `accepted` ou
  `rejected` não pode ser reiniciado por uma edição de evento.
- **Só evento que ainda vai acontecer**: editar evento antigo (ajuste de cachê, troca de ficha) é
  rotina, e "confirme sua presença" para um show da semana passada é ruído.
- **E-mail só depois do commit**, e só para os cargos que **esta** chamada marcou. A primeira versão
  reconsultava por `invite_status == "pending"` depois do commit — isso pegaria também quem já
  estava convidado antes, e reenviaria convite a cada edição de evento. Corrigido guardando as
  linhas marcadas.
- Registra `EventLog` "Convite automático para X (personagem) ao ser escalado no evento", para o
  histórico do evento não ter e-mail sem dono.

**Efeito colateral bom.** Com o convite saindo na escalação, o lembrete automático da 231 passa a
alcançar essas pessoas: ele só cobra quem está `pending`, e antes elas ficavam em `NULL`, fora do
alcance de qualquer cobrança.

**Verificação.** `verify_233_convite_automatico.py` 15/15, com `send_invite_email` dublado e toda
escrita desfeita no fim: o caso real do evento 1192 (a coordenadora deixando de receber 403 e vendo
as fichas, com o link da agenda concordando com a tela); quem recusou seguindo fora; o convite
marcando `pending`, disparando o e-mail e registrando no log; reexecutar não reenviando; e evento
passado sendo ignorado sem e-mail e sem alterar o cargo. Sem regressão: `verify_176` 41/41,
`verify_227` 19/19, `verify_230` 10/10, `verify_231` 19/19, `verify_232` 17/17.

### 232 — Avaliação por partes: a etapa 2 deixou de ser destino e virou cartão abaixo da dobra            (main · 2026-08-10 · sem migration)

**Motivação.** Relato: *"em algum momento da migração deu problema nas avaliações que as pessoas do
portal fazem. Antes era feita a avaliação, além da geral, por partes."*

**O que os dados dizem — e o que eles NÃO dizem.** A etapa 2 não morreu: as seis categorias
continuam recebendo nota, e a taxa de conclusão até **subiu** com o React (81% das avaliações
feitas a partir de 28/07 têm `detail_submitted_at`, contra 71% antes). Última etapa 2 registrada:
06/08. Então o problema não é o backend nem a gravação — conferido também que `submit_rating`
(etapa 1) não marca `detail_submitted_at`, ou seja, a métrica mede etapa 2 de verdade.

**O que realmente se perdeu: o caminho.** Comparando tela a tela com o Jinja (`rate.html` e
`rate_detail.html`):

| | Jinja (antes) | React (depois da 191) |
|---|---|---|
| Botão principal da nota geral | **"Enviar e avaliar em detalhes →"** | "Enviar avaliação" |
| Desvio | "Só enviar a nota geral" (`skip_detail`) | não existia |
| Depois de salvar | **redirect** para a página das partes | mensagem "Avaliação enviada. Obrigado!" e um cartão "Detalhar (opcional)" anexado **abaixo** |
| Categoria `texto` | **"🎭 Show no geral"** + "Falar sobre coreografia, posicionamento, texto e interações" | "Texto / roteiro", sem explicação |
| CTA da etapa 2 | "Enviar avaliação completa ✓" | "Enviar detalhamento" |
| Saída da etapa 2 | "Pular — já enviei o suficiente" | — |

Ou seja: detalhar era o **padrão** e virou **opcional abaixo da dobra**, atrás de um "Obrigado!"
que se lê como fim. Quem não rolava a tela nunca via as partes.

**O que mudou.** A etapa 2 volta a ser destino, sem voltar para duas páginas: o botão principal
salva a nota geral **e rola até o bloco das partes** (`scrollIntoView`, respeitando
`useReducedMotion`), com "Só enviar a nota geral" como desvio explícito. Restaurados também os
rótulos com emoji (👗 Figurino · 🎵 Som · 🎭 Show no geral · 🎭 Colegas artistas · 🧑‍💼 Coordenação ·
💄 Maquiagem), a explicação embaixo de "Show no geral", o cabeçalho "Avaliação detalhada", a linha
"Você deu N estrelas para este evento", o CTA "Enviar avaliação completa ✓" e o "Pular — já enviei
o suficiente".

**`texto` é a correção mais silenciosa e a mais importante.** A coluna guarda 42 registros feitos
sob a pergunta "Show no geral — coreografia, posicionamento, texto e interações". Rebatizá-la de
"Texto / roteiro" fez as pessoas passarem a responder outra coisa **na mesma coluna** — o dado
histórico e o novo deixariam de ser comparáveis sem que nada quebrasse.

**Pegadinha do `scrollIntoView`.** O bloco das partes só existe no DOM **depois** do sucesso da
etapa 1, então a rolagem vai dentro de dois `requestAnimationFrame` — sem isso ela dispara antes do
React pintar o alvo e a tela fica parada, que é exatamente o sintoma que a feature conserta.

**Verificação.** `tsc --noEmit` limpo e build verde em `apps/portal`. Três estados conferidos na
tela a 375px com entry Vite temporária (apagada depois), com dublê de rede para o POST da nota
geral: (1) avaliação nova → dois botões, sem bloco de partes; (2) nota geral enviada → bloco das
partes aparece com as seis categorias, as quatro pessoas do elenco nos três grupos, "Você deu 4
estrelas", CTA e "Pular"; (3) fora do prazo → tudo em leitura, sem botão de envio, com
"Avaliação completa enviada".

**Não verificado.** A **rolagem** não é observável no painel de browser desta sessão: ele não aplica
scroll nenhum (`window.scrollTo(0, 200)` deixa `scrollY` em 0, com documento de 1703px em viewport
de 812px). Confirmei o que dá para confirmar — o alvo do `ref` existe, é o cartão certo (único
`.scroll-mt-4` da página, com `scroll-margin-top: 16px` aplicado) e o `scrollIntoView` roda sem
erro. O comportamento em si precisa de um olhar no celular.

### 231 — Quem ainda não confirmou: painel para o casting e cobrança automática sem spam            (main · 2026-08-10 · `e3f7c25a8b90`)

**Motivação.** Do relato do usuário: *"o ideal é de fato que todo mundo confirmasse, mas nem todos
confirmam. Muitos recebem o convite e não estão aceitando no portal."* Os números confirmam: **41
das 78 escalações futuras estão sem confirmação** — 15 com convite enviado e sem resposta, 26 com
convite **nunca enviado** (concentrados em 3 colaboradores fixos, que a produção escala direto). E
do lado de dentro não havia lista: o sistema só mostrava "X/Y confirmadas" **dentro de cada
evento**, na aba Resumo, então descobrir quem falta na semana exigia abrir evento por evento.

**O painel.** Novo `SectorPanel` "🙋 Confirmações pendentes" na home, ao lado do de Casting, com os
eventos de hoje em diante. Cada linha diz **quem** falta, **qual** evento, a urgência (o mesmo
`getUrgency` do resto da home) e — o que torna a lista útil — **a ação certa para cada caso**:

- convite enviado e sem resposta → botão **"Cobrar no WhatsApp"**, com a mensagem já escrita;
- convite nunca enviado → botão **"Enviar convite"**, que leva ao evento (aqui quem precisa agir é
  o casting, não a pessoa).

A linha também mostra quantos lembretes automáticos já saíram, para ninguém cobrar de novo quem o
robô acabou de cobrar.

**A regra do e-mail, e por que ela é assim.** O pedido foi explícito — *"não quero ficar spammando
as pessoas"*. Cinco travas, todas em `app/calendar/invite_reminders.py`:

1. **Só quem já recebeu o convite** (`invite_status="pending"`). Cargo sem convite (`NULL`) nunca
   recebe e-mail automático: o primeiro contato é o convite, e mandá-lo é decisão de quem escala.
2. **Só na semana do evento** — entre 24h e 7 dias. Antes é ruído; depois, e-mail já não resolve.
3. **No máximo 2 lembretes por convite**, com 3 dias de intervalo.
4. **No máximo 1 e-mail por pessoa por dia**: quem tem três eventos sem responder recebe **um**
   e-mail com os três. É a trava que mais importa contra a sensação de spam.
5. **Só entre 9h e 20h** de Brasília.

Na cópia de hoje isso dá **7 e-mails** para 37 pendências no painel — a desproporção é o ponto.

**Decisões que valem o registro.**

- **Uma consulta só** alimenta o painel e o e-mail (`escalacoes_sem_confirmacao`). Se cada um
  tivesse a sua, o painel cobraria quem o robô já cobrou — ou o contrário.
- **Corte de data próprio, não o `dashboard_cutoff()`** dos outros painéis: aquele vale
  `release_date` (01/06/2026 hoje), e com ele a lista vinha com **59 eventos que já aconteceram**.
  Ninguém cobra confirmação de evento de junho. Aqui é da meia-noite de hoje para a frente, o que
  mantém o evento de HOJE ainda não confirmado — o mais urgente que pode existir na tela.
- **`invite_status` NULL exige `or_` explícito**: em SQL `NULL != 'accepted'` é NULL, não
  verdadeiro, e o cargo sem convite sumiria justamente da lista feita para encontrá-lo.
- **A marcação só acontece depois do envio dar certo** — e-mail que não saiu não gasta a cota de
  lembretes daquele convite.
- **Trava atômica em `site_settings`** (mesmo `UPDATE` condicional de `_claim_auto_sync`): a
  produção roda 3 workers do gunicorn e, sem ela, os três mandariam o mesmo lembrete. Num recurso
  cujo requisito é "não spammar", este é o detalhe que decide.
- **A thread acorda de hora em hora**, não de 24 em 24: quem decide se hoje já teve rodada é a
  trava. Um laço diário perderia o dia inteiro se o container reiniciasse no meio dele.
- **Desligável sem deploy** por `INVITE_REMINDERS_ENABLED=false`, e já nasce **desligada** em
  ambiente que suprime e-mail — senão um processo local apontado para o espelho cobraria artista de
  verdade.
- **Assunto truncado em 42 caracteres**: título de evento aqui chega com 140 ("TURMA DO PETER
  RABBIT - GORRO VERDE + TURMA DO PETER RABBIT - BLUSA AZUL + ..."), e o que sobraria na caixa de
  entrada seria o nome do personagem no meio da frase, não o pedido.

**Migration `e3f7c25a8b90`**: `event_roles.invite_reminder_at` + `invite_reminder_count` (memória
por convite) e `site_settings.invite_reminder_run_at` (a trava). Três colunas, nenhuma obrigatória.

**Verificação.** `verify_231_lembrete_confirmacao.py` 19/19, com o envio **dublado** e as marcações
desfeitas no fim: painel sem evento passado/cancelado/ensaio/dispensado e sem quem já aceitou ou
recusou; elegibilidade só com convite enviado, só na janela de 24h–7d, respeitando o teto; um
e-mail por pessoa; rodar de novo no mesmo dia não cobra ninguém; o segundo worker vê a rodada já
feita; e o corpo citando o evento, levando ao portal e dizendo que recusar também ajuda. Sem
regressão: `verify_176_portal_artista` 41/41 e `verify_230` 10/10. `tsc --noEmit` limpo e build
verde em `apps/internal`. Painel conferido na tela a 375px: sem vazamento horizontal, os três
estados (sem convite / sem resposta / com lembrete já enviado) com a ação certa em cada um, e o
link do WhatsApp com a mensagem pronta.

**Achado à parte, não corrigido.** Qualquer script que chame `create_app()` **sobe as threads de
fundo** — inclusive `calendar-sync`, que fala com o Google Agenda de verdade. O guarda existente
(`FLASK_ENV == "development"`) não pega scripts, que rodam sem essa variável. Nesta sessão nada
disparou (`calendar_auto_sync_at` seguia no horário do espelho, 08/08 17:02), porque os scripts
terminam antes dos 15s de espera da thread — mas isso é sorte de temporização, não proteção. A 231
não cai nessa armadilha (nasce desligada quando o e-mail está suprimido), e o
`run-local-sem-google.py` cobre o servidor, não os scripts.

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
