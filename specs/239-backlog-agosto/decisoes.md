# Decisões do João (18/08/2026) — rodada 239-backlog-agosto

## Transporte fora de SP (carrinho)
1. VALOR: a parcela do VEÍCULO do orçamento (km ida-e-volta × tarifa: van 6,30/5,50, carro 1,90/km), NUNCA o transport_value cheio (o adicional fora-SP por pessoa já está dentro do cachê de todos).
2. FORMA: o teto (cache_cap efetivo) da pessoa marcada SOBE em +parcela do veículo; o valor pago fica todo em cache_value (um número só). NÃO usar travel_cache para o carrinho. Com isso entra automático em planilha de pagamentos/custo/DRE, sem mudança no financeiro.
3. VÁRIOS MARCADOS: cada pessoa marcada tem direito à parcela de UM veículo (com 2 carros no orçamento, cada motorista = parcela de 1 carro).
4. Carrinho só disponível quando event.is_outside_sp. Quem marca: mesmo gate de quem escala casting (_can_edit_event).
5. O bug de apagamento do travel_cache (todo Salvar zera) DEVE ser corrigido de qualquer forma (sentinela _UNSET), mesmo que o carrinho não use travel_cache.

## Título de eventos
6. Coordenador / Técnico de Som / Técnico de Som (Presença) / Maquiador NUNCA aparecem no título. Padronizar limpando: filtrar no pré-fill de orçamento (EventCreatePage), blindar generateTitle com denylist, e ignorar esses segmentos no sync do Google (parse_characters/reconciliação).

## Show → não-show
7. Na troca de tipo saindo de SHOW: CANCELA/REMOVE TUDO AUTOMATICAMENTE — apaga ensaios já agendados (inclusive no Google Calendar), remove as duas vagas automáticas de som (presença e a do PIX/Nivaldo) mesmo preenchidas, desliga needs_rehearsal. Registrar TUDO em EventLog (o que foi removido, valores que existiam) para rastreabilidade, e devolver warnings não-bloqueantes informando o que foi removido.
8. Reescrever o prefixo do título "(SHOW)" → "(TIPO)" na troca e empurrar para o Google (é o que impede o sync de reverter). Na volta (vira SHOW de novo): recria vaga de som e liga needs_rehearsal como na criação.

## Técnico de Som (Presença)
9. Nunca tem valor: trava no servidor (assign_role/add_role força cache_value=None e travel_cache=None para a vaga de presença) e sem campo de dinheiro na UI.
10. Sai da planilha de pagamentos e de TODOS os somatórios (custo de evento, KPI, DRE, dashboard money_total, comissões).
11. No casting (Equipe de apoio) a vaga FICA VISÍVEL como SOMENTE LEITURA (sem campo de dinheiro, sem botões de convite/pagamento) — designação continua no painel de Ensaio.

## Limpezas retroativas (as 3 aprovadas; SEMPRE com dry-run/relatório antes de executar de verdade)
12. Zerar cache_value/travel_cache das vagas de Presença que NÃO estão pagas (linhas pagas ficam intactas). Gerar relatório prévio (evento, data, pessoa, valor, payment_status).
13. Corrigir eventos show→não-show já errados: eventos FUTUROS com event_type != SHOW — desligar needs_rehearsal, remover vagas de som automáticas, corrigir prefixo do título (empurrando ao Google). Seguindo a decisão 7, remoção vale mesmo para vaga preenchida; ensaio filho já agendado é cancelado.
14. Limpar títulos poluídos existentes (remover nomes de equipe do título; empurrar ao Google).
15. Scripts com --dry-run como padrão (só relatório); execução real SÓ depois do deploy e de aprovação explícita do João (mexe no Google Calendar real).

## Outros itens (defaults aprovados por omissão)
16. Link do orçamento no evento: mostrar na aba Comercial apenas para quem consegue abrir (superadmin + comercial dono do orçamento); para os demais (ex.: FINANCEIRO) o campo vem null e o link não aparece.
17. Maquiador: badge na CastingSection do detalhe do evento ("Falta maquiador" gold/red quando precisa && !fechado; "Maquiador fechado" green quando fechado). Critério fechado = vaga extra com nome ~maquiad + talent_id preenchido. 💄 ao lado dos personagens com needs_makeup. Sem automação de criação de vaga (continua manual).
18. Teto p/ superadmin: nova coluna event_roles.cache_cap_note preenchida na criação via orçamento com a conta em valores ("base 2h R$X + noturno R$Y + fora-SP R$Z = R$W"); papéis sem orçamento: nota "definido manualmente, sem orçamento vinculado" (ou null e a UI mostra esse texto). Visível SÓ para superadmin na CastingSection, discreto, perto do cachê.
19. WhatsApp de cobrança: incluir a URL raiz do portal (PORTAL_URL, mesma dos e-mails) no texto; se env ausente, omitir o link.
20. EducaManto: (a) InfoTip novo em @manto/ui (hover+clique+toque+teclado, Framer Motion, useReducedMotion); (b) fallback de rótulos pt-BR e estados loading/erro dos textos; (c) enviar contratacao_manto sempre que ativa (validação do servidor dispara) + desabilitar Gerar com aviso inline quando ativa && sem duração; (d) duracaoCustom 1-4 marca checkbox correspondente, >0 não-padrão aceita; (e) deep-copy da contratação em Nova Página; (f) event_location no payload (FR-015); (g) mover o card Contratação Manto para logo após "Dias e ensemble"; (h) linha explícita sob os cards Sem NF/Com NF quando contratação ativa: os valores NÃO incluem a contratação Manto. RBAC continua COMERCIAL/SUPERADMIN.
21. Catálogo: mover item do menu para a 1ª seção (logo após Agenda), visibilidade everyone (inclusive REVENDEDOR_EDUCAMANTO — o catálogo já é público sem login). "Gerenciar catálogo" fica onde está.
22. Produção/compra: DialogContent do NovoPedidoDialog ganha max-h-[85vh] overflow-y-auto (padrão Fila3DPage/FormulariosAdminPage).

## Regras de execução (obrigatórias para todos os agentes)
- Branch: 239-backlog-agosto. NÃO commitar, NÃO push, NÃO tocar em docs/ (docs serão atualizados numa fase própria).
- NUNCA reescrever arquivo via PowerShell Get-Content/Set-Content (corrompe UTF-8/acentos). Usar SEMPRE os tools Edit/Write.
- Dinheiro no front sempre via @manto/money; arquivos servidos pelo Flask via assetUrl() de @manto/api-client; lógica de negócio em *_ops.py; RBAC como função no início da view; type hints + docstrings Google style; UI pt-BR, Tailwind + @manto/ui, feedback via TanStack Query, Framer Motion 150-350ms com useReducedMotion.
- Migrations: revisar o head atual (ver migrations/versions/) e encadear down_revision corretamente.
- Depois de mexer em frontend: npx tsc --noEmit limpo no(s) app(s) tocado(s). Backend: python -m py_compile nos arquivos tocados.
- NÃO rodar servidor, NÃO mexer em banco nenhum nesta fase (scripts retroativos são só escritos, não executados).
