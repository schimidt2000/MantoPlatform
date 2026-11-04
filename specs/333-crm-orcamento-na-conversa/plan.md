<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: 333 — Orçamento e formulário pela conversa

**Branch**: `333-crm-orcamento-na-conversa` (sobre a `332-crm-avisos-no-celular`) | **Data**: 2026-11-03 | **Spec**:
[spec.md](./spec.md)

**Input**: `/specs/333-crm-orcamento-na-conversa/spec.md`

## Resumo

O vendedor manda o orçamento pela conversa, de dentro dela ou da tela do orçamento. Saem a mensagem pronta (em partes
no Instagram) e o PDF, pelo envio que a conversa já tem.
- O envio fica registrado em `orcamento_envios`.
- O orçamento fica ligado à ficha da conversa, que nasce na hora quando falta.
- A conversa ganha ligar, trocar e remover a ficha à mão, sem que a ligação automática desfaça a escolha.
- "Enviar formulário" insere no campo o texto pronto com o link curto.
- "Criar evento" a partir do orçamento traz a cliente.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy); TypeScript + React 18 (Vite).

**Dependências principais**: as da casa; nenhuma nova. O PDF é o `gerar_orcamento_pdf` de hoje (reportlab).

**Armazenamento**: PostgreSQL. 1 tabela nova e 2 colunas ([data-model.md](data-model.md)).

**Verificação**: `verify_333.py` com dublê da Meta (molde do `verify_330`); `verify_325`, `verify_328`, `verify_330` e
`verify_332` como regressão; `npm run typecheck`; tela pela worktree em desktop e 375×812.

**Plataforma-alvo**: app interno (Conversas, Orçamento, Agenda, Clientes).

**Restrições**:
- nenhuma chamada à Meta em transação aberta (cada parte usa o `envio_ops`);
- a base é uma branch fora da `main`;
- `app/calendar/routes.py` só ganha a chave `cliente` no pré-preenchimento (`docs/00` §7).

**Escala/escopo**:
- 4 endpoints novos (`app/api/conversas_costura.py`);
- 3 endpoints alterados (o histórico e o detalhe do orçamento, o pré-preenchimento do evento);
- 2 núcleos novos (`costura_ops`, `ficha_ops`);
- 3 componentes novos e 5 telas tocadas.

## Constitution Check

| Princípio / seção | Como o plano cumpre |
|---|---|
| I. Reutilizar antes de criar | Usa sem copiar o que já existe: `envio_ops.enviar_texto`/`enviar_arquivo`, `quote_for_entry`, `gerar_orcamento_pdf`, `client_ops.quick_create_client` e `variantes_de_telefone`. Também os `GET` do histórico, das conversas e da busca de clientes, e a regra de clientes da tela do evento (298). |
| II. Padrões de código | Type hints, docstrings, funções curtas; constantes em `app/conversas/constantes.py`; `ruff check` nos tocados. |
| III. Camadas / API First | O núcleo fica em `app/conversas/costura_ops.py` e `ficha_ops.py`, sem `request`. Os endpoints ficam em `app/api/conversas_costura.py`, importado em `app/api/__init__.py`. |
| IV. Não quebrar | Mudança aditiva. Só `_vincular_cliente` muda de comportamento: ele respeita a `ficha_manual`. Os verifies 325, 328, 330 e 332 são regressão. |
| V. UI/UX com feedback | Botões com `loading`, erro no campo da ficha, toasts pt-BR, partes "não entregue" com "Tentar novamente" (já existe). |
| VI. Esteira (Nível 1) | Esteira completa em `specs/333-crm-orcamento-na-conversa/`. |
| VII. Living Spec | Spec com as decisões do dono antes do código. |
| VIII. Verify antes do núcleo | `verify_333.py` na Foundational, falhando antes do núcleo. |
| IX. Dinheiro BRL | Só exibição de valores já calculados (`@manto/money` na tela). |
| X. Mobile-first público | Não toca superfície pública. As telas internas são conferidas em 375×812, porque a equipe atende pelo celular. |
| XI. Framer Motion | Os `Dialog` existentes. |
| XII. Combobox | Busca de ficha e de conversa com lista filtrada pelo servidor. |
| XIII. RBAC declarado | `pode_conversas` (papel real) nos 4 endpoints novos; os gates de hoje nos alterados; linhas em `docs/01` §4.3. |
| XIV. Config / efeito externo | Sem env nova. O envio herda a trava e a janela do `envio_ops`. O link usa `PLATFORM_BASE_URL`, que tem valor fixo. |
| XV. Texto por superfície | Interno: "Enviar orçamento", "Enviar na conversa", "Ligar à ficha", "Trocar ficha", "Remover vínculo" (Remover = desfaz o vínculo sem apagar), "Enviar formulário". A mensagem do formulário vai para a cliente: "Oi, Ana! …". |
| Stack | Migration à mão, aditiva, sobre `b332d5f7a9c1`. Sem Jinja novo. |
| Operação e Deploy | Não toca `startCommand`. |

**Resultado**: ✅ sem violação.

## Estrutura

```text
app/models.py                                     # OrcamentoEnvio; OrcamentoHistory.client_id; Conversa.ficha_manual
migrations/versions/c333e1a5b7d9_orcamento_na_conversa.py
app/conversas/costura_ops.py                      # enviar_orcamento, dividir_texto, formularios_da_conversa, envios_do_orcamento
app/conversas/ficha_ops.py                        # ligar, remover, ficha_para_envio
app/conversas/envio_ops.py                        # conferir_envio (público)
app/conversas/aviso_ops.py                        # _vincular_cliente respeita ficha_manual
app/conversas/constantes.py                       # textos e formulários
app/conversas/leitura_ops.py                      # serializar_conversa: ficha_manual
app/clientes/client_ops.py                        # quick_create_client(source=); client_metrics: balde conversa
app/api/conversas_costura.py                      # POST orcamento; POST/DELETE ficha; GET formularios
app/api/__init__.py                               # registra o módulo (uma linha)
app/api/orcamento_read.py                         # enviado_em no histórico; cliente e envios no detalhe
app/calendar/routes.py                            # _build_orcamento_prefill: cliente
frontend/apps/internal/src/lib/conversas.ts       # hooks: enviar orçamento, ficha, formulários
frontend/apps/internal/src/lib/orcamento.ts       # tipos: enviado_em, cliente, envios
frontend/apps/internal/src/lib/eventCreate.ts     # tipo: cliente no prefill
frontend/apps/internal/src/lib/clientes.ts        # balde conversa
frontend/apps/internal/src/components/conversas/EnvioDoOrcamento.tsx     # escolha + resumo + ficha + enviar (as duas portas)
frontend/apps/internal/src/components/conversas/FichaDaConversaDialog.tsx
frontend/apps/internal/src/components/conversas/ConversaAberta.tsx       # cabeçalho: Ligar à ficha / menu
frontend/apps/internal/src/components/conversas/CaixaDeEnvio.tsx         # "Enviar orçamento", "Enviar formulário"
frontend/apps/internal/src/pages/OrcamentoResultadoPage.tsx              # "Enviar na conversa" + envios
frontend/apps/internal/src/pages/OrcamentoHistoricoPage.tsx              # selo
frontend/apps/internal/src/pages/EventCreatePage.tsx                     # cliente do orçamento
frontend/apps/internal/src/pages/ClientsListPage.tsx                     # "Conversa" no gráfico
specs/333-crm-orcamento-na-conversa/verify_333.py
```

**Reavaliação pós-design**: ✅.
