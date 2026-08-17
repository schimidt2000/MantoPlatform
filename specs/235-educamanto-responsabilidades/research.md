# Research — Feature 235: EducaManto por responsabilidades

Decisões técnicas da Phase 0. Fatos citados do código foram verificados no repositório em 13/08/2026 (panorama da geração de orçamentos + leitura direta de `app/educamanto/*` e `app/orcamento/*`).

## D1 — Modelagem: renomear a tabela de pacotes para musicais (preservando ids)

**Decision**: Renomear `educamanto_packages` → `educamanto_musicals` e `educamanto_items` → `educamanto_musical_items` via Alembic, adicionando os campos novos (nº de personagens, nº de produção, nº de ensaios, custos de som/iluminação/cenário/alimentação como colunas próprias). A migração **poda os níveis**: mantém as 7 linhas Master (que viram os musicais), apaga Intermediário/Econômica e a cópia órfã (id 32), e move o custo do item "Som" do Master para a coluna `custo_som_*` (removendo o item da lista).

**Rationale**: Preservar os ids dos Master (1, 11, 15, 18, 23, 26, 29) mantém o "Recalcular" de snapshots antigos funcionando sem tabela de-para para a maioria dos casos; renomear explicita a mudança de semântica (1 linha = 1 musical, não 1 nível). Snapshots antigos são JSON autocontidos (sem FK) — o re-download do PDF nunca consulta a tabela.

**Alternatives considered**: (a) Tabelas novas + drop das antigas — quebra o mapeamento de ids do Recalcular; (b) manter a tabela com as 22 linhas e um flag "musical" — estado híbrido permanente, viola o fim do conceito de nível (FR-002).

**Recalcular de snapshot antigo**: se o `package_id` do snapshot não existir mais (era Intermediário/Econômica), mapear pelo prefixo do nome ("Jardim Mágico - Econômica" → musical "Jardim Mágico"), pré-marcando responsabilidades conforme o nível antigo (Econômica → alimentação e iluminação da contratante) e avisando o vendedor do mapeamento aplicado.

## D2 — Responsabilidades como blocos de custo do musical

**Decision**: Cada responsabilidade vira colunas de custo no musical, nos 4 cenários existentes (1 sessão, 2 sessões, diária 1s, diária 2s — mesmo shape dos itens de hoje):
- **Som completo** (`custo_som_*`): migrado do item "Som" do pacote Master (ex.: Uma Aventura Animal 4000/4000/3500/3500).
- **Iluminação completa** (`custo_iluminacao_*`): coluna nova, valor inicial provisório (hoje a iluminação está embutida na diferença Master×Intermediário, não existe como item separado — o dono envia o custo real junto com os dos técnicos).
- **Cenário** (`custo_cenario_*`): coluna nova, provisória (mesma situação).
- **Alimentação**: continua sendo o item por pessoa "Catering apresentação" (55/73 por pessoa); o alternador remove/inclui esse item. Catering de ensaio e ajuda de custo **não** são afetados (sempre entram, × nº de ensaios — decisão do dono).

Quando a responsabilidade é da contratante, o bloco sai da soma de custos **antes** da margem. Os demais itens do musical (elenco, produção, gráfica, caminhão…) permanecem itens comuns sempre inclusos.

**Rationale**: Mantém a fórmula atual (Σ custo × margem por cenário) intacta — responsabilidade é só presença/ausência de parcelas no Σ. Colunas dedicadas (vs. itens marcados) impedem que um musical nasça sem definição de som/iluminação e simplificam o PDF.

**Alternatives considered**: flag `responsabilidade` por item da lista — mais flexível, porém permite estados inválidos (dois itens de som, nenhum de iluminação) e complica a matriz técnica.

## D3 — Equipe técnica: itens derivados, sonoplasta fixo

**Decision**: Técnicos são custos por cenário definidos em constantes provisórias num módulo único (`app/educamanto/pdf_textos.py` concentra textos; valores em `PROVISORIOS` no mesmo módulo ou `constants.py`): `SONOPLASTA_*`, `TECNICO_SOM_*`, `TECNICO_ILUMINACAO_*`. Entram na soma de custos como o elenco (passam pela margem). A matriz: sonoplasta sempre; técnico de som quando som = Manto; técnico de iluminação quando iluminação = Manto. O nº de técnicos do caso soma no headcount.

**Rationale**: Tratar técnico como custo com margem é consistente com o resto do elenco (hoje "1 técnico" já está implícito no headcount 11 da Uma Aventura Animal). Constantes num único módulo tornam o gate de lançamento (trocar provisório por definitivo) um diff de um arquivo.

**Alternatives considered**: custo por musical (colunas) — técnicos custam o mesmo em qualquer musical; global é o correto e evita 7× manutenção.

## D4 — Headcount unificado

**Decision**: `headcount = nº personagens + nº produção + técnicos do caso + ensemble`. Alimenta: cadeiras do camarim (PDF), itens por pessoa (catering apresentação quando Manto, catering ensaio e ajuda de custo × nº ensaios) e o adicional por pessoa da viagem. Substitui a derivação atual por `max(linhas com ensemble_add>0)`.

**Rationale**: O nº de personagens/produção vira dado declarado do musical (o dono pediu essas quantidades no PDF); derivar o headcount deles elimina a gambiarra do `pessoas_transporte` e a dependência de itens de catering para contar gente.

## D5 — Transporte: caminhão SP e 2 vans fora de SP

**Decision**:
- **Dentro de SP** (padrão): item "Caminhão" de **R$ 800** (nova chave `caminhao_sp: 800` em `pricing_config['transporte']`, editável nas Configurações de Preços; substitui o item fixo de R$ 600 dos pacotes, que a migração remove da lista de itens). Sem vans, km ignorado.
- **Fora de SP** (checkbox): caminhão sai; entra viagem com **2 vans** — custo km = `km_total × (van_com_carretinha + van_sem_carretinha)` (tarifas existentes em `orcamento/settings`), adicional por pessoa = `headcount × km_total ÷ afsp_divisor` (uma vez), sem adicional de show; total × (d1 + d2) dias. Nova função em `app/educamanto/pricing_ops.py` usando as tarifas de `orcamento/settings` como fonte única (não reusa `calcular_van` inteira porque a composição é outra: 2 tarifas + 1 adicional).

**Rationale**: mantém tarifas centralizadas e configuráveis; espelha exatamente a regra ditada pelo dono (adicional é por pessoa fora de SP, não por veículo).

## D6 — Contratação Manto embutida: reuso de `calculate_quote`

**Decision**: O backend do EducaManto chama `app.orcamento.quote_ops.calculate_quote(payload)` com `nota_fiscal=False` e `fora_sp=False`, herdando data/local da configuração. Os `total_1h..total_4h` (+ `total_custom`) retornados somam ao líquido EducaManto **antes** do ÷ 0,84 e do arredondamento; para cada duração selecionada o resultado é um total combinado (sem NF e com NF). No frontend, `PerformersEditor` e `AcrescimosEditor` são extraídos de `OrcamentoCalculadoraPage.tsx` para `components/orcamento/` e usados nas duas telas; os hooks/tipos de `lib/orcamento.ts` são reusados.

**Rationale**: `calculate_quote` já é função pura com todo o módulo de equipe/coordenador/acréscimos/durações — reuso direto cumpre a exigência do dono ("mudança futura lá reflete aqui") e o Princípio I. `nota_fiscal=False` evita dupla aplicação (a NF do EducaManto cobre a soma); `fora_sp=False` evita transporte duplicado (a logística é do EducaManto).

**Alternatives considered**: replicar as regras de equipe no EducaManto — viola a fonte única e é exatamente o erro histórico (fórmula Jinja duplicada) que esta feature apaga.

## D7 — Multi-configurações e snapshot v2 com recálculo no servidor

**Decision**: A tela mantém um array de configurações (abas "Página 1..N"); cada edição recalcula via API a configuração ativa. "Gerar orçamento" envia **as entradas** de todas as configurações; o servidor **recalcula tudo** e grava `snapshot = {"version": 2, "configs": [{inputs, resultados}], ...}`. O PDF e o histórico usam somente os valores do servidor. Snapshots v1 continuam renderizando pelo caminho atual (detecção por ausência de `version`).

**Rationale**: Corrige a dívida de integridade (valores hoje vêm do cliente) e implementa FR-017/FR-026/FR-027 com um formato versionado.

## D8 — RBAC: corte de breakdown no servidor

**Decision**: O endpoint de cálculo monta a resposta completa e, se o usuário não é superadmin, remove antes de serializar: itens/custos (`item_rows`, `raw_cost`, `valor_base`, desconto interno, memória da contratação Manto), mantendo apenas valores finais (sem NF, com NF, à vista), transporte total e os campos do próprio acréscimo (efetivo/máximo/capado — necessários ao aviso de teto). A UI nem renderiza as seções.

**Rationale**: SC-005 exige que nada vaze "em tela, em API ou em PDF" — esconder só na UI não atende.

## D9 — PDF por responsabilidade

**Decision**: `pdf.py` reescrito: uma página A4 por configuração; seções por responsabilidade com dois textos possíveis (Manto: "o que levaremos"; contratante: "mínimo exigido"), quantidades da equipe, avisos fixos (palco 5×4 m, camarim com cadeiras = headcount, som/áreas X-Y, visita técnica em local aberto), linhas de dias só quando > 0, valores sem NF / com NF / à vista (5%), trecho da contratação Manto com totais por duração, e a observação livre do vendedor. Todos os textos em `pdf_textos.py` (rascunhos redigidos pelo dev a partir do material atual + planos.md; revisão do dono é gate de deploy). `SHORT_DESC`/`LONG_DESC`/detecção por substring morrem.

**À vista**: valor = total × 0,95, arredondado a 2 casas (sem ceil100), espelhando o padrão da calculadora de eventos (`pix_vista`).

## D10 — Desligamento do Jinja do EducaManto

**Decision**: Remover `templates/educamanto/` e as views Jinja de `app/educamanto/routes.py`; as rotas antigas viram redirect 302 para as rotas React equivalentes (`/educamanto`, `/educamanto/pacotes` → `/educamanto/musicais`, `/educamanto/historico`). A réplica JS da fórmula morre junto com o template. Endpoints de API permanecem em `app/api/educamanto_*`.

**Rationale**: FR-029; escopo limitado ao EducaManto conforme decisão do dono (o resto do Jinja fica para um plano futuro).

## Pendências de negócio (gate de deploy, fora do gate de plano)

| Item | Placeholder | Quem resolve |
|---|---|---|
| Custos de sonoplasta / técnico de som / técnico de iluminação | constantes `PROVISORIO_*` | dono envia valores |
| Áreas X (fechado) / Y (aberto) do aviso de som | constantes `PROVISORIO_*` | dono envia valores |
| Custos de iluminação completa e cenário por musical | colunas com valor provisório | dono envia valores |
| Textos do PDF e tooltips | rascunhos do dev em `pdf_textos.py` | dono revisa e aprova |
