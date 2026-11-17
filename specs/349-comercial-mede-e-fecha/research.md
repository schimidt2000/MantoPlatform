# Pesquisa (Phase 0) — 349

Sem NEEDS CLARIFICATION no contexto técnico. As decisões abaixo saem da leitura do código na `main` (`20bf93c0`) e da
pesquisa "Máquina de vendas Manto" (§3.7, §6.5, §8.2, §8.4).

## R1 — Primeira resposta: colunas na conversa, gravadas no evento e recalculadas só na falha

- **Decisão**: quatro colunas em `conversas` (`primeira_recebida_em`, `primeira_resposta_em`,
  `primeira_resposta_por_id`, `primeira_resposta_origem`). A primeira mensagem é gravada por UPDATE condicional
  (`IS NULL OR > :momento`) quando chega mensagem da cliente que não é reação (`aviso_ops._gravar_recebida`,
  `instagram_ops._chegou_da_cliente`). A primeira resposta é gravada por UPDATE condicional
  (`primeira_resposta_em IS NULL AND primeira_recebida_em <= :momento`) nos três pontos que já encerram a espera
  (`equipe_ops.resposta_da_equipe` para a Plataforma, `aviso_ops._gravar_eco` para o celular,
  `instagram_ops._gravar_eco` para outro app). A falha depois do aceite (`_aplicar_status`) e a primeira mensagem que
  anda para trás recalculam pelas mensagens, com a régua de resposta válida da 328 restrita a `enviada/entregue/lida`.
- **Por quê**: o funil (coorte de até um ano) e a lista precisam do número sem varrer mensagens; a gravação no ponto
  do fato é O(1). A régua de "resposta válida" já existe (`equipe_ops._resposta_valida`) e é reaproveitada.
- **Alternativas**: derivar na leitura (cara no funil e repetida a cada 5 s); tabela de eventos de SLA (sobra para uma
  métrica só).

## R2 — Resposta sem autor fica visível

- **Decisão**: `primeira_resposta_origem` copia `conversa_mensagens.origem` (`plataforma`, `celular`, `outro`); autor
  nulo com origem `celular`/`outro` aparece como "pelo celular, sem autor" / "por outro app, sem autor" e é contado à
  parte no funil (`sem_autor`).
- **Por quê**: o limite da coexistência é conhecido (pesquisa, `erp_crm_funil` §F); esconder distorce o ranking por
  vendedor.

## R3 — Perda e qualificação são estado da conversa, não tabela

- **Decisão**: colunas `perdida_*` e `qualificacao*` em `conversas`; motivos em lista fechada em `constantes.py`
  (fonte única dos rótulos, devolvida pela API com `pede_frase`, como `FORM_CLOSE_REASONS` da 298). Reabrir apaga as
  quatro colunas da perda.
- **Por quê**: uma conversa tem uma situação de cada vez; o histórico de idas e vindas não foi pedido. O funil lê as
  colunas na mesma consulta da coorte.
- **Alternativas**: tabela de transições (mais escrita e leitura para nada pedido); reabrir automático na mensagem
  nova (rejeitado no clarify).

## R4 — Pontuação calculada na leitura, em lote, só com colunas

- **Decisão**: `pontuacao_ops.contexto(linhas)` roda `funil_ops._etapas` (etapa) e mais duas consultas em lote: a data
  do evento do orçamento e do formulário mais recentes da ficha depois do primeiro contato (colunas
  `orcamento_history.event_date` e `form_responses.event_date`) e a recompra (evento vivo da ficha criado antes do
  primeiro contato). Regras v1 em `constantes.py`: formulário +3, data ≤ 90 dias +2 / > 90 dias +1, orçamento +1,
  recompra +2; corte 3. Qualificada = decisão manual se houver; senão pontos ≥ corte.
- **Por quê**: guardar a pontuação exigiria gancho no orçamento, no formulário e na agenda (três domínios); calcular
  em lote custa poucas consultas indexadas. Nada lê JSON (`form_snapshot`) no caminho da lista.
- **Alternativas**: persistir e recalcular na varredura (defasagem e escrita a cada minuto); ler "fora de SP" do
  `form_snapshot` (JSON em `Text` no caminho quente da lista; fica para a revisão trimestral).

## R5 — Lista: contexto em lote e recorte no SQL

- **Decisão**: `venda_ops.resumos_da_lista(conversas)` monta as `Linha` do funil para a página (primeiro contato =
  o menor entre `primeira_recebida_em` e `created_at`), consulta o anúncio numa vez e chama `pontuacao_ops.contexto`.
  O recorte vira filtro na consulta da lista: `esperando` = `aguardando_desde IS NOT NULL`; `anuncio` = EXISTS em
  `conversa_anuncios` com `tipo = 'anuncio'`; `orcamento_parado` = o predicado único de `parado_ops` (R6).
- **Por quê**: a lista já pagina por cursor; filtrar no SQL mantém a paginação certa.

## R6 — "Orçamento parado": um predicado SQL para a lista e para a régua

- **Decisão**: `parado_ops.SQL_ULTIMO_ORCAMENTO` calcula, por conversa, o último orçamento enviado
  (`GREATEST` entre o último envio pela conversa e o último orçamento da ficha, com `COALESCE(envio, criação)` como no
  funil), só depois do primeiro contato, e exige: sem formulário da ficha depois dele, sem evento vivo da ficha criado
  depois dele, `perdida_em IS NULL`. A lista compara com `agora − N dias`; a régua busca os que estão entre 2 e 10 dias.
- **Por quê**: a mesma definição nas duas portas (FR-015), escrita uma vez.

## R7 — Lembrete e régua na varredura das conversas, só no sino

- **Decisão**: `parado_ops.avisar_lembretes(agora_sp)` entra em `varredura.ciclo_de_varredura` (depois do alerta de
  espera). Lembrete vencido (`lembrar_em <= agora`) → `emitir(KIND_CONVERSA_LEMBRETE, dedupe =
  conversa.lembrete:{id}:{epoch})` para quem marcou (ou responsável/equipe se perdeu o acesso) e UPDATE condicional que
  apaga o lembrete (`WHERE lembrar_em = :lido`). Régua: para cada conversa parada entre 2 e 10 dias, o degrau atual
  (maior de 2/5/9 já alcançado) → `emitir(KIND_CONVERSA_ORCAMENTO_PARADO, dedupe =
  conversa.orcamento_parado:{id}:{epoch_orcamento}:{degrau})`, para o responsável ativo ou a equipe; só das 9h às 21h
  (mesmo `HORARIO_DE_ALERTA`). Push no celular (332) depois do commit, como a espera.
- **Por quê**: a varredura já roda nos três workers sem lock; a idempotência é a `UNIQUE(user_id, dedupe_key)` do sino
  (armadilha 10). O lembrete do "amanhã" é para a hora certa, mas o horário 9–21 vale também para ele (às 9h já está
  dentro).
- **Alternativas**: thread própria (mais uma); tabela de lembretes (um por conversa basta).

## R8 — Cotar sem sair: endereço, estado inicial e volta pelo endereço

- **Decisão**: o envio de orçamento ganha "Fazer orçamento" → `/orcamento?conversa=<id>&cliente=<nome>`. A calculadora
  lê os dois no estado inicial (`useState(() => …)`), mostra a faixa "Orçamento para a conversa com …" e, no "Gerar
  orçamento", navega para `/conversas?c=<id>&orcamento=<novo>`. A tela de Conversas passa o `orcamento` à caixa de
  envio, que abre o diálogo com o orçamento escolhido (a lista dos recentes já foi invalidada pelo salvar) e apaga o
  parâmetro (`replace`).
- **Por quê**: zero requisição a mais na calculadora (o nome entra no primeiro payload, que já ia sair); nenhum endpoint
  novo.

## R9 — Criar evento: o que levar vem do servidor, o vínculo num ponto único

- **Decisão**: `fechamento_ops.o_que_levar(conversa)` devolve o último orçamento enviado na conversa, a ficha e o
  vendedor (responsável ativo; senão o autor do último envio). A conversa navega para
  `/events/new?orcamento_id=<id>&conversa=<id>`; a criação lê `venda.fechamento` (mesma consulta da conversa) para pôr a
  ficha como Contratante e o vendedor (se estiver na lista de vendedores), e manda `conversa_id`. `POST /api/events`
  valida a conversa antes do Google (422 `conversa_id`) e, depois do núcleo, chama
  `fechamento_ops.ligar_evento_a_conversa(evento, conversa)`: garante a ficha entre as clientes do evento, apaga a
  perda e é o lugar onde a 348 grava `calendar_events.conversa_id`.
- **Por quê**: o vendedor sai de quem atendeu sem regra nova na agenda; a 348 se pluga sem tocar a agenda.

## R10 — Banco de verificação

- **Decisão**: `manto_349`, restaurado de `backups/manto_2026-11-17_0200.dump` (head `d334b2c4e6f8`).
- **Por quê**: 348–351 migram sobre a mesma head ao mesmo tempo; o `manto_local` é compartilhado.
