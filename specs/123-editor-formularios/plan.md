# Implementation Plan: Editor de Formulários (123)

**Branch**: `123-editor-formularios` | **Date**: 2026-07-09 | **Spec**: [spec.md](./spec.md)

## Summary

Move a estrutura hoje hardcoded dos dois formulários públicos (`comum`, `corporativo`) para
uma tabela nova (`FormFieldDefinition`), editável por SUPERADMIN numa tela do painel. As
rotas/templates públicos passam a renderizar e validar dinamicamente a partir dessa tabela em
vez de macros/listas fixas no código. A migration semeia a tabela com os campos exatamente como
existem hoje (mesmos rótulos, tipos, obrigatoriedade, ordem) para não mudar nada no primeiro
deploy — só passa a ser editável dali em diante.

**TanStack (sugestão do usuário) avaliado e descartado**: é uma lib de estado de formulário
para React/Solid/Vue — o projeto é Jinja2 + JS vanilla (CLAUDE.md, sem framework JS) e não usa
build step de frontend. Adotá-lo exigiria introduzir um bundler e um framework SPA só para esta
tela, o que violaria a stack do projeto sem necessidade: o problema ("estrutura hardcoded") é
resolvido movendo a definição dos campos para o banco e renderizando com o motor de templates já
usado em todo o projeto (Jinja2 + JS vanilla), reaproveitando os componentes de campo (máscara,
erro inline, honeypot) que já existem em `_field_macros.html` e `_form_scripts.html`.

## Technical Context

**Language/Version**: Python 3.14 (Flask), o já usado no projeto.

**Primary Dependencies**: Flask, SQLAlchemy, Flask-Login — nenhuma dependência nova.

**Storage**: PostgreSQL (produção + `manto_local`). Nova tabela `form_field_definitions`.

**Testing**: Verificação funcional com test client do Flask contra `manto_local` (requests fora
de `app_context`), conforme portão do projeto.

**Target Platform**: Web — tela de edição é interna (painel, desktop-oriented, como as demais
telas de admin); os formulários públicos continuam mobile-first (Princípio VIII).

**Project Type**: Web app monolito Flask existente — sem novo projeto/serviço.

## Modelo de dados

Nova classe em `app/models.py`, próxima a `FormResponse`:

```python
class FormFieldDefinition(db.Model):
    """Definição editável de um campo de formulário público (feature 123).

    Substitui os campos hardcoded de app/formularios/routes.py. Cada linha é um campo de um
    dos dois formulários (`form_type`: 'comum' | 'corporativo'), agrupado visualmente por
    `section_name` e ordenado por `order` (a seção muda quando `section_name` muda ao
    percorrer os campos em ordem — não existe tabela de seção separada, YAGNI).
    """

    __tablename__ = "form_field_definitions"

    id = db.Column(db.Integer, primary_key=True)
    form_type = db.Column(db.String(20), nullable=False)  # 'comum' | 'corporativo'
    section_name = db.Column(db.String(100), nullable=False)
    field_key = db.Column(db.String(60), nullable=False)  # nome estável (name do <input>)
    field_type = db.Column(db.String(20), nullable=False)
    # 'texto_curto' | 'texto_longo' | 'selecao' | 'data' | 'hora' | 'telefone' | 'email' |
    # 'cpf' | 'cnpj' | 'cep' | 'sim_nao'
    label = db.Column(db.String(200), nullable=False)
    help_text = db.Column(db.String(300), nullable=True)
    placeholder = db.Column(db.String(200), nullable=True)
    required = db.Column(db.Boolean, default=False, nullable=False)
    options = db.Column(db.Text, nullable=True)  # JSON list[str], só para field_type='selecao'
    order = db.Column(db.Integer, nullable=False)
    is_system = db.Column(db.Boolean, default=False, nullable=False)  # não removível
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (db.UniqueConstraint("form_type", "field_key", name="uq_form_field_key"),)

    @property
    def options_list(self) -> list[str]:
        import json
        try:
            return json.loads(self.options or "[]")
        except (ValueError, TypeError):
            return []
```

`FormResponse.data` (JSON) muda de `campos: [[rotulo, valor], ...]` para
`campos: [[chave, rotulo, valor], ...]` — inclui a `field_key` usada no momento do envio, sem
quebrar leitura de respostas antigas (`_field_from_sections` passa a aceitar entradas de 2 ou 3
posições; respostas antigas sem chave simplesmente não participam da busca por chave, igual ao
comportamento best-effort que a feature 119 já tinha).

## Migration

`migrations/versions/<novo_id>_form_field_definitions.py` — `down_revision="d5e6f7a8b9c0"`:
- `upgrade()`: cria `form_field_definitions` (colunas acima); insere, via `op.bulk_insert`, as
  linhas equivalentes aos campos hoje hardcoded em `PAGAMENTO_COMUM`, `TIPOS_CONTRATACAO`,
  `ESPACOS_EVENTO`, `PAGAMENTO_CORPORATIVO` e nas funções `_sections_comum`/`_sections_corporativo`
  — mesmos rótulos, tipos, obrigatoriedade e ordem de hoje, para o comportamento não mudar no
  deploy. Campos marcados `is_system=True`: os que alimentam extração de `contact_name`/
  `contact_phone`/`event_date` (`nome_contratante`/`razao_social`, `whatsapp`, `data_evento`,
  `hora_evento`), os usados pela automação de CPF/CNPJ/endereço da feature 119 (`cpf`,
  `endereco_contratante`, `cnpj`, `endereco_empresa`), e os campos de endereço acoplados ao
  autopreenchimento por CEP (`cep`, `logradouro`, `bairro`, `cidade`, `estado`, só no formulário
  `comum`). O restante (`is_system=False`) fica livre para remoção pelo editor.
- `downgrade()`: `drop_table("form_field_definitions")`.
- Checagem obrigatória de colisão de revision-id via `grep -rl "<id>" migrations/versions/`
  antes de finalizar (regra do projeto).

## Rotas e refatoração

`app/formularios/routes.py`:
- **Público** (`/f/pre-contrato`, `/f/corporativo`): `_validate_comum`/`_validate_corporativo` →
  uma função `_validate_dynamic(form_type, f)` que itera `FormFieldDefinition` do tipo, valida
  `required` genericamente + formato específico por `field_type` (cpf=11 dígitos, cnpj=14
  dígitos, cep=8 dígitos, email=`_valid_email`, telefone=min 10 dígitos no `_national`, data/hora
  parseáveis). `_sections_comum`/`_sections_corporativo` → `_build_sections_dynamic(form_type, f)`,
  monta `[chave, rótulo, valor]` por seção a partir das defs ordenadas. `_render_comum`/
  `_render_corporativo` → um único `_render_public_form(form_type, form, errors)` passando a
  lista de campos agrupada por seção ao template.
- **Templates**: `pre_contrato.html` e `corporativo.html` (98+62 linhas hardcoded) são
  substituídos por um único `formularios/public_form.html`, iterando seções → campos e
  despachando para uma única macro `field(f, form, errors)` em `_field_macros.html` que decide o
  widget pelo `f.field_type` (reaproveita os macros existentes `text_field`, `textarea_field`,
  `select_field`, `phone_field`; `radio_field` é removido — `espaco_evento` passa a ser
  `selecao`/dropdown, mesma validação, só troca o widget visual, decisão abaixo). O script de
  autopreenchimento por CEP (hoje só em `pre_contrato.html`, hardcoded ao id `f-cep`) vira um
  bloco genérico que só ativa se existir um campo com `field_key == 'cep'` no formulário, e
  escreve nos campos com `field_key` em `{'logradouro','bairro','cidade','estado'}` quando
  existirem — grau de acoplamento igual ao de hoje, só que por chave estável em vez de id fixo
  no HTML.
- **Editor** (novo, SUPERADMIN): blueprint reaproveitado (`formularios_bp`), rotas:
  - `GET /formularios/editor/<form_type>` — lista seções/campos com ordem, tipo, obrigatoriedade.
  - `POST /formularios/editor/<form_type>/campo/novo` — cria campo (`field_key` gerado por slug
    do rótulo, dedupe com sufixo numérico se colidir); `field_type` restrito ao conjunto suportado.
  - `POST /formularios/editor/campo/<id>/editar` — rótulo, texto de ajuda, placeholder,
    obrigatoriedade, opções (só tipo `selecao`); NÃO permite trocar `field_type` nem `field_key`
    de um campo já existente (evita quebrar respostas antigas/mapeamento — mais simples que
    suportar migração de tipo, YAGNI).
  - `POST /formularios/editor/campo/<id>/mover` — `direction=up|down`, troca `order` com o vizinho
    dentro da mesma seção.
  - `POST /formularios/editor/campo/<id>/excluir` — bloqueado (`400` + flash) se `is_system`.
  - Todas exigem `_has_role(RoleName.SUPERADMIN)` (novo decorator `require_superadmin`, mesmo
    padrão de `require_vendas` já existente no arquivo).
- **Feature 119** (`_field_from_sections`/`_fill_client_from_response` em
  `app/formularios/routes.py`): busca passa a ser por `field_key` (`"cpf"`, `"cnpj"`,
  `"endereco_contratante"`, `"endereco_empresa"`) em vez de `secao`+rótulo em texto — sobrevive a
  renomeações de rótulo (FR-009). Como esses `field_key` são de campos `is_system=True`
  (não removíveis), a busca sempre encontra o campo, mesmo que o texto do rótulo mude.

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar | ✅ Um só template/macro genérico substitui dois pares de template+funções quase idênticos; reaproveita `_field_macros.html`, `_form_scripts.html`, `_public_base.html` existentes. |
| II. Padrões Python | ✅ Type hints, docstrings, funções pequenas nas novas rotas/helpers; `except` amplo (parsing de `options` JSON) já loga/trata com fallback documentado. |
| III. Camadas | ✅ Validação/montagem de seções isolada em helpers puros (`_validate_dynamic`, `_build_sections_dynamic`), rotas só orquestram — mesmo padrão do arquivo hoje. |
| IV. Não quebrar | ✅ Migration semeia a tabela para reproduzir exatamente o formulário atual; `FormResponse.data` aceita formato antigo e novo; feature 119 passa a ser mais robusta (por chave), não menos. Verificação cobre os dois formulários, edição de campo existente, campo novo, remoção, reordenação, e o fluxo de associação de cliente pós-edição. |
| V. UI/UX | ✅ Botão de salvar/adicionar campo no editor segue padrão de loading/disable; exclusão de campo pede confirmação (ação destrutiva); erro de validação no formulário público continua preservando o que foi digitado (comportamento já existente, mantido pela função dinâmica). |
| VI. Planejar | ✅ Este plano. |
| VII. Moeda BR | N/A — nenhum valor monetário nesta feature. |
| VIII. Mobile-first | ✅ Formulários públicos continuam mobile-first (renderização dinâmica usa os mesmos widgets/CSS já testados em mobile); a tela de editor é interna/painel, sem essa exigência (mesmo padrão das demais telas administrativas do sistema). |

**Gate: PASS.**

## Decisões

1. **Sem tabela de "Seção" separada**: seção é só um `section_name` repetido nos campos daquela
   seção, ordenados por `order` — evita uma segunda entidade e uma segunda tela de CRUD para um
   conceito que, nesta versão, não precisa ser reordenado como bloco (spec já assume isso).
2. **`espaco_evento` deixa de ser radio-button e vira `selecao` (dropdown)**: reduz para um único
   widget de "escolha entre opções" em vez de dois (`radio_field` + `select_field`) — mesma
   validação, mesma obrigatoriedade, só muda a apresentação visual desse campo específico.
   Simplificação deliberada (YAGNI/Princípio I): manter dois widgets equivalentes só duplicaria
   código no editor (tipo "seleção-dropdown" vs "seleção-radio") sem pedido do usuário para isso.
3. **Layout 2 colunas (`data`+`hora`, `número`+`complemento`, `cidade`+`estado`) vira 1 coluna
   (cada campo no seu próprio bloco)**: eram só compactação visual, não requisito funcional; um
   editor de campos dinâmico não sabe de pares "que ficam bem lado a lado" sem uma noção de
   layout adicional — abrir mão do agrupamento em pares é a opção mais simples que continua
   mobile-first (Princípio VIII) e não perde nenhuma informação/validação.
4. **`field_type` e `field_key` são imutáveis após criação**: só rótulo/ajuda/placeholder/
   obrigatoriedade/opções são editáveis num campo existente. Trocar o tipo de um campo que já tem
   respostas salvas geraria inconsistência de formato sem benefício claro pedido pelo usuário —
   fora de escopo (se for preciso, o caminho é remover e recriar, para campos não-sistema).
   `field_key` fixo também é o que garante que a busca da feature 119 (FR-009) nunca quebra.
   `is_system=True` sempre feito por identidade da migration, nunca pelo editor.
5. **Tipo `cep` acrescentado** (além dos 10 listados no spec): necessário para preservar o campo
   CEP existente (máscara de 8 dígitos + autopreenchimento ViaCEP) sem regressão — é aditivo ao
   conjunto de tipos prometido no spec, não reduz nada do que foi especificado.
6. **Editor não é mobile-first**: é uma tela interna de painel (como Admin, Financeiro,
   Configurações), não uma das "superfícies públicas" do Princípio VIII — segue o padrão visual
   comum das telas administrativas do sistema.
