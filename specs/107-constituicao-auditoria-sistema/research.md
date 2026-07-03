# Research — Constituição + Auditoria Geral (107)

## R1. Diagnóstico da constituição atual (v1.2.0)

Problemas encontrados:

1. **Portão inexequível**: "testes relevantes passam (`pytest tests/ -v`)" — o repositório
   **não tem diretório `tests/`**; nenhuma feature (088–106) criou. A prática real e
   comprovada (104/105/106) é: script de verificação funcional com test client do Flask
   contra `manto_local`, requests fora de `app_context` (memória:
   flask-test-client-app-context-leak).
2. **Ferramenta ausente**: mypy citado nos portões não está instalado no venv.
3. **Lacunas operacionais não escritas**: migrations à mão (autogenerate quebrado — memória),
   mobile-first para superfícies públicas (features 104/106), Postgres-only bugs (regra de
   testes já no CLAUDE.md mas não na constituição).

**Decision** (v1.3.0):
- Portões reescritos: (a) verificação funcional automatizada por feature contra `manto_local`
  (test client, requests fora de app_context) — obrigatória antes do merge; (b) `ruff check`
  limpo nos arquivos tocados; (c) `ruff format` para arquivos NOVOS (legado mantém estilo
  circundante para não gerar diffs gigantes); (d) mypy = recomendado, vira obrigatório quando
  instalado no ambiente.
- Princípio novo VIII: **Superfícies públicas são mobile-first** (portal, cadastro, revisão)
  — alvos de toque ≥44px, sem scroll horizontal 320–430px, teclado virtual considerado.
- Stack/Restrições: registrar "migrations SEMPRE manuais (autogenerate quebrado por drift)"
  e "verificar contra manto_local, nunca SQLite vazio".
- Changelog datado, versão 1.2.0 → 1.3.0.

**Alternatives considered**: criar suíte pytest do zero — mudaria a prática consolidada no
meio de um ciclo e exigiria infra (fixtures de banco); registrado no backlog como evolução
desejável. Instalar mypy agora — geraria centenas de erros legados; backlog.

## R2. Varreduras executadas (números reais)

| Classe | Resultado |
|---|---|
| Moeda `{:,` em templates | 11 ocorrências em 5 arquivos: `desempenho.html` (2 — reinventado sem decimais), `event_create.html` (5 — reinventado com replace), `home.html` (1 — **AMERICANO**), `financeiro/dashboard.html` (1 — macro local reinventada), `talent_detail.html` (2 — **AMERICANO**) |
| `except` amplo sem log | `calendar/routes.py:1956,2021`, `calendar/service.py:186`, `cli.py:71`, `email_service.py:500`, `models.py:365`, `storage.py:201`, `talents/importer.py:34,42` (`figurino/routes.py:368` conferir se loga) |
| `print()` em código de app | `figurino/drive_service.py:91` |
| `alert(` em templates | 11 ocorrências em 6 arquivos: `event_detail` (2), `figurino_form` (1), `financeiro/pagamentos` (1), `orcamento/resultado` (1), `orcamento/settings` (5), `revisao/asset` (1 — fallback aceitável) |
| Forms POST × proteção duplo envio | 45 templates com form POST; só 16 com padrão de desabilitar botão |
| `innerHTML` sem escape aparente | 68 usos — **backlog** (análise por tela; área autenticada) |

## R3. Formato do relatório de auditoria (auditoria.md)

Uma tabela por módulo (12 módulos: agenda/eventos, talentos, financeiro, vendas, admin,
figurino, ferramentas/orçamento, clientes, revisão, portal, cadastro, auth) com colunas:
**Achado | Severidade (crítico/alto/médio/baixo) | Esforço (B/M/A) | Status (✅ corrigido |
📋 backlog)**. Cabeçalho com resumo executivo (contagens). Seção final "Backlog priorizado"
ordenada por severidade×esforço com recomendação de próxima feature.

## R4. Padrão das correções

- **Moeda**: `R$ {{ x | brl }}` (fonte única `app/money.py`). No dashboard financeiro, o
  corpo do macro `money(v)` vira `R$ {{ (v or 0) | brl }}` — call sites intactos.
  `desempenho.html` passa a exibir decimais (efeito da padronização, previsto na spec SC-003).
- **Logging**: logger de módulo (`logger = logging.getLogger(__name__)`) onde não houver;
  `logger.warning("<contexto>: %s", exc)` para recuperações esperadas;
  `logger.exception(...)` para falhas inesperadas. Zero mudança de fluxo.
- **Duplo envio**: `onsubmit="var b=this.querySelector('button[type=submit]'); if(b){b.disabled=true;}"`
  ou handler equivalente já usado no projeto; aplicar nos forms principais dos módulos
  detectados sem proteção (lista final na auditoria).
- **alert() de erro** → mensagem inline na área de feedback da própria tela (padrão da tela);
  `confirm()` de ação destrutiva permanece (é o padrão aceito pela constituição V).

## R5. O que explicitamente NÃO entra (→ backlog)

- Revisão dos 68 `innerHTML` (XSS interno) — por tela.
- Suíte pytest + mypy no ambiente.
- Padronização de cores hardcoded em templates legados (centenas) — quando cada tela for tocada.
- Migração `datetime.utcnow()` (deprecado no Py3.12+) — mecânica mas ampla (models inteiro).
- Otimizações de query/índice e redesigns de tela.
