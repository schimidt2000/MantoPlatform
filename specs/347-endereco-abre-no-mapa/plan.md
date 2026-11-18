# Plano de implementação: Tocar no endereço do evento e escolher o app de mapas

**Branch**: `347-endereco-abre-no-mapa` | **Data**: 2026-11-17 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/347-endereco-abre-no-mapa/spec.md`

## Resumo

O endereço do evento passa a ser tocável na página do evento do app interno (cabeçalho e "Local"
de "Dados do evento") e nos cards de "Próximos eventos" e "Convites" do Portal do Artista. O toque
abre "Abrir endereço" com Google Maps, Apple Mapas e Waze; cada opção é um link universal HTTPS que
abre o app instalado (ou o site do serviço). Uma peça só em `@manto/ui` — função pura
`linksDeMapa` + componente `EnderecoNoMapa` sobre o `Dialog` existente — consumida pelas duas SPAs.
Só frontend.

## Contexto técnico

**Linguagem/Versão**: TypeScript + React 18 (Vite) no frontend. Backend não muda.

**Dependências principais**: `@manto/ui` (`Dialog` sobre Radix + Framer Motion, `cn`),
`lucide-react` (ícones `MapPin`, `ExternalLink`), Tailwind com o preset do design system. Nenhuma
dependência nova.

**Armazenamento**: nenhum. Lê `location`, que já está no payload (data-model.md).

**Verificação**: `verify_347.py` (esbuild + node para os links; leitura no `manto_local` para o
payload); `cd frontend && npm run typecheck`;
tela aberta no Browser pane — app interno em 390px e tela larga, portal em 375×812.

**Plataforma-alvo**: app interno no celular (instalado na Tela de Início) e no computador; portal
no celular.

**Tipo de projeto**: SPA desacoplada (API JSON + React).

**Metas de desempenho**: N/A — nenhum pedido de rede; o diálogo abre na hora.

**Restrições**: 320–430px sem rolagem horizontal; alvo de toque ≥ 44px no portal e nas opções;
`useReducedMotion` (herdado do `Dialog`); link para fora com `target="_blank"` (research R2).

**Escala/escopo**: 0 tabelas, 0 endpoints; 2 arquivos novos em `@manto/ui` + `index.ts`; 4 telas
(2 componentes do app interno, 2 páginas do portal).

## Constitution Check

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | `Dialog`/`DialogHeader`/`DialogTitle`/`DialogDescription` e `cn` de `@manto/ui`; nenhum primitivo novo. Peça única para os dois apps (FR-010). |
| II. Padrões de código | TS estrito; constantes de URL no topo de `mapas.ts`; comentário só do porquê, em pt-BR. Sem Python de produção (o verify segue `ruff check`). |
| III. Camadas / API First | Não toca backend. Componente novo exportado em `packages/ui/src/index.ts`. |
| IV. Não quebrar o que funciona | Aditivo: só troca a renderização do texto do endereço; sem endereço, a tela fica igual (FR-008). Cabeçalho perde o "•" antes do endereço (o ícone faz esse papel). |
| V. UI/UX com feedback | Sem ação de rede. O gatilho tem estado de foco/hover; o diálogo abre e fecha com animação; o link fecha a escolha ao ser tocado. |
| VI. Esteira (Nível 1) | Esteira completa: dois domínios (Agenda, Portal). |
| VII. Living Spec | A spec ganhou a tabela do verify antes do código. |
| VIII. Verify antes do núcleo | `verify_347.py` na fase Foundational, antes de `mapas.ts` (falha: módulo ausente), com cenário que deve falhar e leitura no `manto_local` provando que o endereço chega às telas (research R5). |
| IX. Dinheiro BRL | Não se aplica. |
| X. Mobile-first público | Portal: alvo ≥ 44px no endereço e nas opções; conferido a 320/375/430px. |
| XI. Framer Motion | Herdado do `Dialog` (150–200 ms, `useReducedMotion`). |
| XII. Combobox / Maps | Não há input de endereço (o `GoogleAddressInput` é para digitar). Nenhuma chave do Google vai ao navegador: links universais públicos, sem API. |
| XIII. RBAC declarado | Sem endpoint. O endereço só aparece onde o payload já o entrega (RBAC do servidor intacto). |
| XIV. Config / efeito externo | Sem env, sem escrita externa: o link só abre um app na mão da pessoa. |
| XV. Texto por superfície | Textos novos: "Abrir endereço" (título), "Google Maps", "Apple Mapas", "Waze" (nomes próprios), `title`/rótulo acessível "Abrir no app de mapas". Neutros, servem ao interno (operacional) e ao portal (cordial); "Abrir" segue o verbo do vizinho "Abrir no Maps" da Logística. Nada comparado em lógica. |
| Stack | Sem migration, sem Jinja, sem segredo. |
| Operação e Deploy | Só `frontend/` muda → deploy só do `manto-frontend`, sem queda; pode subir em horário de equipe. |

**Resultado**: aprovado, sem violação.

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/347-endereco-abre-no-mapa/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/endereco-no-mapa.md
├── checklists/
├── tasks.md
└── verify_347.py
```

### Código

```text
frontend/packages/ui/src/lib/mapas.ts                          # NOVO — linksDeMapa (pura)
frontend/packages/ui/src/components/endereco-no-mapa.tsx       # NOVO — EnderecoNoMapa
frontend/packages/ui/src/index.ts                              # exportar os dois
frontend/apps/internal/src/components/EventDetail/EventHeader.tsx    # cabeçalho
frontend/apps/internal/src/components/EventDetail/ResumoSection.tsx  # "Local" de DadosLeitura
frontend/apps/portal/src/pages/PortalAgendaPage.tsx            # RoleCard (Próximos eventos)
frontend/apps/portal/src/pages/PortalConvitesPage.tsx          # InviteCard (Convites)
```

**Decisão de estrutura**: a montagem do link é função pura separada do componente para o verify
testá-la sem navegador e para a regra (ordem, codificação, vazio → nada) ter uma fonte só. No
portal, o endereço sai da linha da data (onde era "· endereço" no fim) para uma linha própria: um
botão no meio de uma frase não tem alvo de 44px.

## Pós-desenho (Constitution Check reavaliado)

Sem mudança: o desenho da Phase 1 (contrato em `contracts/endereco-no-mapa.md`) não introduz
endpoint, dado, env nem dependência. Aprovado.

## Rastreamento de complexidade

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| Verify e tela rodaram no `manto_347`, não no `manto_local` (Princípio VIII) | O `manto_local` diz estar na head (`d334b2c4e6f8`) mas não tem a coluna `site_settings.meta_pixel_id` da 344: as migrations do CRM rodaram nele antes do reencadeamento sobre a 344. Todo endpoint que lê `SiteSetting` quebra ali | Consertar o `manto_local` mexe no banco compartilhado das outras sessões; o `manto_347` é o dump de produção de 17/11 02h, já na head e com o esquema completo |
