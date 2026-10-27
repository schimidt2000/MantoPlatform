# 319 — O aviso de gasto extra diz o que é

**Branch**: `319-aviso-gasto-extra` · **Created**: 2026-10-22 · **Status**: PRONTA, aguardando deploy ·
**Migration**: nenhuma

## O pedido

O dono (22/10), com print da tela bloqueada do celular mostrando dois avisos idênticos ("Novo gasto
extra cadastrado — aprovação pendente / Novo gasto extra cadastrado — revise e aprove na plataforma.
Manto Produções Olá, João! Um novo gasto extra foi cadastrado no evento (SHOW) SEREIA + …"): "seria
interessante que ele de fato mostrasse na notificação o que está sendo feito". Decidiu: **valor
primeiro** no assunto e **incluir o botão** para a tela de gastos.

## O que muda

Só `send_new_expense_alert_email` (`app/email_service.py`). O celular mostra o assunto e a prévia
(preheader); os dois eram fixos.

- **Assunto**: `Gasto extra R$ 1.234,50 · <descrição>` (descrição cortada em 50 caracteres com "…").
- **Prévia**: `categoria · lançado por <nome> · <pagamento> · com/sem comprovante · <evento> — dd/mm`
  (ou "sem evento"). Pagamento: "já pago", "reembolsar <nome>", "pagar <fornecedor>", "devolver ao
  cliente". O evento vai por último porque o título é longo. Enchimento invisível no fim para o
  celular não completar a prévia com "Manto Produções Olá, João!".
- **Corpo**: caixa com valor, descrição, categoria, data do gasto, quem lançou, pagamento,
  comprovante, evento e observações; botão **Revisar gasto →** para `<plataforma>/gastos`.
- Texto digitado pelo usuário (descrição, fornecedor, observações) agora é escapado no HTML.

## Verificação

`verify_319.py` (10/10): monta os e-mails com gastos transitórios sobre usuários e evento reais do
`manto_local`, `_send` trocado por coletor — nada sai, nada é gravado. Cenário 6 deve falhar no
comportamento antigo (dois gastos do mesmo evento com o mesmo assunto). `VERIFY_319_HTML=<arquivo>`
grava o e-mail do cenário 1 para abrir no navegador.

## Fora de escopo

Agrupar vários gastos num aviso só; aviso por WhatsApp/push; link direto para um gasto específico
(a tela `/gastos` não abre um gasto pela URL).
