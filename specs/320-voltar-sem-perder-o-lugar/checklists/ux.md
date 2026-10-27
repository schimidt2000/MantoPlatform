# Checklist de qualidade dos requisitos: navegação e UX (320)

**Purpose**: testar se a spec da 320 descreve sem lacuna o "voltar", a rolagem e o visualizador de
arquivo no iPhone — antes das tarefas.
**Created**: 2026-10-27 · **Profundidade**: padrão · **Público**: revisão do autor antes do `/speckit-tasks`
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [contracts/ui.md](../contracts/ui.md)

## Completude

- [x] CHK001 - Estão listados todos os estados de lista que voltam iguais (busca, categoria, situação, visão, aba, filtros, página)? [Completeness, Spec §FR-001–FR-003]
- [x] CHK002 - A fila "E-mails com problema" do banco de talentos tem requisito de volta, ou está explicitamente fora? [Gap, Spec §FR-003] — resolvido: FR-003 passou a incluir a fila
- [x] CHK003 - Está definido o que "voltar" faz em cada página de detalhe (tema público, categoria pública, edição no gerenciador, ficha de talento), inclusive depois de salvar/rejeitar? [Completeness, Spec §FR-006–FR-007, História 2 cenário 2]
- [x] CHK004 - Estão listados os tipos de arquivo com prévia e o que acontece com os demais? [Completeness, Spec §FR-010, FR-013]
- [x] CHK005 - O comportamento do "Baixar" no iPhone está especificado de modo a não recriar a armadilha (arquivo abrindo sem volta)? [Gap, Spec §FR-012] — resolvido: FR-012 diz que "Baixar" nunca tira a pessoa do sistema
- [x] CHK006 - Os textos novos estão nomeados e alinhados ao glossário (Ver, Baixar, Voltar, Tentar novamente)? [Completeness, Spec §FR-014, FR-018; Plan §XV]

## Clareza

- [x] CHK007 - "Exatamente onde estava" está quantificado (item aberto visível sem rolar)? [Clarity, Spec §SC-001]
- [x] CHK008 - "Arquivo do app interno" está delimitado contra links para outros sites (InfinitePay, Drive, ClickSign, WhatsApp)? [Ambiguity, Spec §FR-009] — resolvido: FR-009 restringe a arquivos guardados no sistema
- [x] CHK009 - "App instalado" está definido de forma que distinga a cliente no navegador comum? [Clarity, Spec §FR-016–FR-017, História 4 cenário 3]
- [x] CHK010 - "Navegação nova" × "voltar" está definida para a rolagem (topo × ponto salvo)? [Clarity, Spec §FR-004–FR-005]

## Consistência

- [x] CHK011 - O rótulo dos atalhos ("← Voltar ao catálogo", "‹ Talentos pendentes") é coerente com o destino quando a pessoa NÃO veio da lista? [Consistency, Spec §FR-006]
- [x] CHK012 - O "Voltar" do visualizador e o voltar do navegador/gesto têm o mesmo efeito? [Consistency, Spec §FR-011, História 3 cenário 3]
- [x] CHK013 - A regra de digitação na busca (não empilhar "voltar") é compatível com a busca no endereço? [Consistency, Spec §FR-001, FR-008]

## Cobertura de cenários e bordas

- [x] CHK014 - Há requisito para lista que mudou enquanto a pessoa estava no detalhe (item sumiu, página deixou de existir)? [Coverage, Spec §Casos de borda]
- [x] CHK015 - Há requisito para lista ainda carregando na volta (cache expirado)? [Coverage, Spec §Casos de borda]
- [x] CHK016 - Há requisito para arquivo que falha ao carregar e para PDF longo? [Exception Flow, Spec §FR-014, Casos de borda]
- [x] CHK017 - Está coberto o visualizador aberto a partir de um diálogo (o diálogo continua ao voltar)? [Coverage, Spec §Casos de borda]
- [x] CHK018 - Está coberto recarregar a página com o visualizador aberto? [Recovery, Spec §Casos de borda]
- [x] CHK019 - Os links do gerenciador que levam a outras telas (visão Personagens → figurino) estão dentro ou fora? [Gap] — resolvido: "Fora de escopo"

## Não funcionais

- [x] CHK020 - Teclado e foco estão especificados para o visualizador no computador? [Accessibility, Spec §Casos de borda]
- [x] CHK021 - Está dito que o visualizador não muda permissão de acesso a arquivo? [Security, Spec §FR-019, RBAC]
- [x] CHK022 - O impacto de peso nas telas que não abrem PDF tem meta? [Performance, Plan §Contexto técnico]

## Dependências e premissas

- [x] CHK023 - A premissa "iPhone com o sistema na Tela de Início abre sem a barra do Safari" está registrada e é a que o verify simula? [Assumption, Spec §Premissas; Research R5–R6]
- [x] CHK024 - A premissa de que comprovantes são fotos e PDFs está apoiada em dado? [Assumption, Spec §Premissas; Research R6 — 3 JPG e 15 PDF no `manto_local`]

## Notas

- Quatro lacunas (CHK002, CHK005, CHK008, CHK019) foram corrigidas na spec nesta rodada.
