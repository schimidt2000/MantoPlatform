# Contrato — bloco `formularios` do `GET /api/dashboard` (feature 298)

Gate inalterado: `show_formularios = show_comercial` (COMERCIAL, FINANCEIRO e SUPERADMIN), respeitando o
"Ver como" (`dashboard_service.py:512-516, 577`). `null` significa sem permissão ou painel que
falhou (`_bloco`). O verify confere que a chave veio preenchida para quem tem o papel.

**Todos os campos abaixo são opcionais no tipo TS e lidos com fallback** (`?.`, `?? 0`, `[]`). Servidor
e site sobem separados e ficam ~1 min em versões diferentes em todo deploy (portão da constituição).

## Formato

```json
{
  "formularios": {
    "contagens": { "total": 1548, "sem_destino": 36, "com_evento": 140, "encerrados": 0, "historico": 1372, "corte": "2026-06-01" },
    "pode_criar_evento": true,
    "motivos_encerramento": [ { "codigo": "desistiu", "rotulo": "A cliente desistiu" } ],
    "a_chegar": [ <LinhaFormulario>, ... ],
    "ja_passou": [ <LinhaFormulario>, ... ]
  }
}
```

As partições somam o total (FR-017).

**`pode_criar_evento`** = `is_superadmin` (real e sem impersonar, `dashboard_service.py:508`) OU
`_effective_has_role(user, impersonate, papel)` para algum papel de `_CAN_CREATE`
(`calendar/routes.py:60`), sem repetir a lista de papéis. Com isso, "Ver como FINANCEIRO" vê "Abrir".

`LinhaFormulario`:

```json
{
  "chave": "tel:5511999999999",
  "representante_id": 3994,
  "cliente": { "id": 812, "nome": "Fulana" },
  "nome_no_formulario": "Fulana de Tal",
  "tipo": "comum",
  "tipo_rotulo": "Festa",
  "data_informada": "2026-09-12",
  "dias_ate_a_data": 2,
  "dias_desde_chegada": 16,
  "grupo": "a_chegar",
  "severidade": "vermelho",
  "data_suspeita": false,
  "repetido": false,
  "outro_com_evento": false,
  "formularios": [
    { "id": 3994, "tipo_rotulo": "Festa", "data_informada": "2026-09-12", "chegou_em": "2026-08-25T14:02:00+00:00", "dias_desde_chegada": 16 }
  ],
  "sugestao": null
}
```

`sugestao`, quando existe:

```json
{ "event_id": 1236, "titulo": "(R&I) ...", "data": "2026-09-27", "dias_diferenca": 1 }
```

- `cliente` é `null` quando não há ficha; aí a linha mostra `nome_no_formulario`.
- Os valores de `severidade` são `vermelho` (0–7 dias), `amarelo` (8–30 e "já passou") e `cinza` (>30 ou
  data suspeita). O front só mapeia para os tons `red`, `gold` e `neutral`.

## Consumo no React (`DashboardPage.tsx`)

- **Tipos.** `FormulariosSummary` deixa de ser `StatusCounts` (`lib/types.ts:148`) e vira um tipo
  próprio, com todos os campos opcionais. `StatusCounts` (`lib/formulariosAdmin.ts:29-35`) muda para
  as partições, mais `corte`. A troca de forma vai **no mesmo commit** do servidor e dos dois
  consumidores.
- **`computeSectionStats`.**
  - O `count` é `contagens?.sem_destino ?? 0`.
  - O `urgent` é a soma de `formularios.length` das linhas `vermelho`.
  - O `detail` é "N formulário(s) sem evento desde DD/MM", com o `corte`.
  - O painel lê `statPorSecao.get("formularios")?.urgent`.
- **Painel "📝 Formulários sem evento na agenda"**, logo depois de "💼 Comercial":
  - dois `PanelGroup` ("A data informada ainda vai chegar" e "A data informada já passou"), cada um
    com a sua `ListaTruncada` (6 linhas);
  - vazio: "Nenhum formulário esperando evento ✓";
  - em tela estreita a linha quebra em duas, sem rolagem horizontal, com a ação principal sempre
    visível.
- **Linha (`FormularioSemDestinoRow`, local).** Mesma estrutura de `PendingPaymentRow` e
  `UnconfirmedRow` (`-mx-4 px-4 py-2.5 border-b border-line`), com fundo `bg-red-50` ou `bg-gold-50`
  (tokens que acompanham o tema escuro) e `MetricBadge size="xs"`.
  - **Marcas**, nesta ordem fixa: "data suspeita" (já na US1), "preencheu N vezes", "já tem outro
    formulário com evento".
  - **Linha 1**: cliente e data informada (`formatShortDate`) com a distância em palavras. O
    formatador é local, a partir de `dias_ate_a_data`: "hoje", "amanhã", "em N dias", "passou há N
    dias". **Não** usar `formatRelativeDay`, que diz "ontem/há N dias" e usa o relógio do navegador.
    A urgência nunca é dita só pela cor.
  - **Linha 2**: `tipo_rotulo` · "chegou há N dias" (de `dias_desde_chegada`).
  - **Ação principal**: "Criar evento" (`variant="default"`) → `/events/new?form_response_id=<id>`,
    ou "Abrir" → `/formularios?resposta=<id>` quando `pode_criar_evento` é falso.
  - **Ação secundária**: "Encerrar…", que abre o diálogo com os `motivos_encerramento` do servidor.
  - **Sugestão**: faixa curta, com entrada e saída animadas: "Parece ser o evento de DD/MM — [Ligar]
    [Não é este]".
    - "Não é este" abre um `ConfirmDialog`: "A sugestão não voltará para este formulário; ainda dá
      para ligar à mão pela tela Formulários".
    - Depois de "Ligar", se vier `divergencia_cliente`, a faixa mostra as duas clientes e "Usar a
      cliente do evento neste formulário".
  - **Repetidos**: a linha expande (Framer Motion com `useReducedMotion`) e mostra os formulários,
    cada um com "Este é o que vale".
  - **Saída**: a linha resolvida sai com `AnimatePresence` (`exit` de 150–350 ms, `useReducedMotion`).
    Onde não for possível, fica sem animação (decisão do dono).
- **Erros.** Toda mutation mostra o erro inline em pt-BR. O 409 também invalida a lista
  (`invalidarDestinoDeFormulario`).
