# Feature 239 — Backlog Agosto/2026 (11 itens)

Rodada de 11 itens levantados pelo João em 18/08/2026, investigados item a item no código
(ver `research/*.md`, um arquivo por item, com causa raiz e evidência arquivo:linha) e com
as decisões de produto fechadas com o João em `decisoes.md` (fonte de verdade em conflito
com qualquer proposta da investigação).

## Itens

| # | Item | Tipo | Complexidade |
|---|------|------|--------------|
| 1 | Carrinho de transporte fora de SP no casting (teto = cachê + parcela do veículo) + fix do apagamento de travel_cache | feature + bugfix | média |
| 2 | Técnico de Som (Presença) sem valor e fora da planilha de pagamentos (read-only no casting) | bugfix | baixa |
| 3 | Show→não-show: troca de tipo remove ensaio/vagas automaticamente e corrige prefixo do título (sync Google deixa de reverter) | bugfix | média |
| 4 | Link do orçamento de origem na aba Comercial do evento | feature | baixa |
| 5 | Coordenador/Técnico/Maquiador nunca no título (pré-fill, generateTitle, sync) | bugfix | média |
| 6 | Badge de maquiador (falta/fechado) na CastingSection + 💄 por personagem | feature | baixa |
| 7 | Teto do cachê visível para superadmin com explicação da conta (cache_cap_note) | feature | média |
| 8 | Link do portal na mensagem de cobrança WhatsApp | feature | baixa |
| 9 | EducaManto: descoberta da Contratação Manto + 4 defeitos + InfoTip real no ⓘ | bugfix + UX | média |
| 10 | Catálogo no topo do menu, visível a todos | UX | baixa |
| 11 | Dialog de criar produção/compra com scroll interno (max-h 85vh) | bugfix | baixa |

## Limpezas retroativas aprovadas (scripts com --dry-run padrão; execução real só pós-deploy com aprovação)
- Zerar cachês de vagas de Presença não pagas (com relatório prévio).
- Corrigir eventos futuros show→não-show (ensaio, vagas, prefixo do título → Google).
- Limpar títulos poluídos existentes (→ Google).

## Critérios de aceite globais
- `npx tsc --noEmit` limpo em todos os apps tocados; `py_compile` limpo no backend.
- Migrations encadeadas linearmente a partir do head atual.
- Regras do CLAUDE.md respeitadas (@manto/money, *_ops puros, RBAC como função, UI pt-BR com feedback TanStack, Framer Motion + useReducedMotion).
- docs/01, 02 e 03 atualizados ao final da rodada (fase própria).
