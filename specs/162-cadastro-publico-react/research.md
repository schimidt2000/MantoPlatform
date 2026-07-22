# Research: Cadastro Público de Talentos em React

## §1 — Reaproveitar as funções de validação/parsing do Jinja

**Decisão**: `app/api/cadastro_write.py` importa diretamente `_build_phone`, `_height_to_cm`,
`_validate_upload`, `_yes_no` (movidas de `app/cadastro/routes.py` para um módulo compartilhado,
ver §4) e `parse_date`/`normalize_tags`/`only_digits`/`_parse_passport_status` (já em
`app/talents/importer.py`, sem mudança). O endpoint novo só troca a fonte dos dados
(`request.form`/`request.files` — igual ao Jinja, pois o body chega como multipart nos dois
casos) e o formato de resposta (`jsonify` em vez de `render_template`/`redirect`).

**Razão**: Princípio I (reutilizar antes de criar) — nenhuma dessas funções depende de HTTP
além de ler `request.form`/`request.files`, que a rota API também recebe (multipart). Duplicar
seria a violação exatamente descrita na constituição.

**Alternativas consideradas**: reimplementar a validação em Python puro recebendo um dict — mais
"correto" architecturalmente (services sem HTTP), mas essas funções já são pequenas o bastante e
usadas em um único lugar hoje; extrair um serviço novo só para isto seria complexidade
desproporcional ao tamanho da fatia (mesma leitura aplicada às fatias 145/154/156/161: extrai só
quando o núcleo é reusado por 2+ chamadores reais).

## §2 — Multipart com múltiplos arquivos nomeados numa única requisição

**Decisão**: `POST /api/cadastro` aceita `Content-Type: multipart/form-data` com até 4 campos de
arquivo distintos (`photo_face`, `photo_full`, `doc_photo`, `cnh_file`) mais todos os campos de
texto do formulário, numa única requisição — igual ao POST do Jinja hoje
(`request.files.get("photo_face")` etc.).

**Razão**: a convenção multipart da feature 153 (`specs/153-upload-anexos-evento/contracts/
upload-endpoints.md`) foi desenhada para "um arquivo por requisição" porque cada endpoint de
anexo de evento lida com um tipo de arquivo por vez. Aqui o formulário inteiro (dados + até 4
arquivos) é uma única submissão atômica no Jinja hoje — dividir em múltiplas requisições
(1 por arquivo + 1 para os dados) mudaria a atomicidade (o que acontece se 1 de 5 requisições
falhar no meio?) e exigiria um talento "rascunho" intermediário, aumentando complexidade sem
necessidade. Multipart HTTP nativamente suporta múltiplos campos de arquivo com nomes diferentes
na mesma requisição — não é uma extensão de protocolo, só um uso do multipart não usado ainda
neste projeto.

**Alternativas consideradas**: (a) endpoint de criação em JSON + endpoints de upload separados
por arquivo (padrão 153) — rejeitado por quebrar atomicidade e criar estado intermediário
("talento incompleto") que não existe hoje; (b) 4 requisições em paralelo do frontend — mesma
razão, mais complexidade de sincronização no cliente para nenhum ganho.

## §3 — Componente de upload de arquivo no design system

**Decisão**: `FileUpload` novo em `packages/ui/src/components/file-upload.tsx` — input de
arquivo estilizado (`Button` + input escondido), preview de imagem (thumbnail) quando o arquivo
selecionado é `image/*`, estado de erro (borda vermelha + mensagem), label de tipo/tamanho
aceito. Recebe `accept`, `maxSizeBytes`, `onChange`, `error?`, `label`, `required?` como props.

**Razão**: é o primeiro componente de upload compartilhado do design system — hoje `apps/
internal` tem upload de foto de talento/figurino (feature 155) implementado ad-hoc por tela, sem
componente reutilizável. Criar em `@manto/ui` (não em `apps/public` isolado) evita duplicar de
novo na próxima tela que precisar de upload, e mantém a fonte única do Princípio I — mas migrar
as telas da 155 para usá-lo é trabalho de outra fatia (fora de escopo aqui: tocar `apps/internal`
não faz parte da US5).

**Alternativas consideradas**: implementar o upload direto em `CadastroForm.tsx` sem componente
compartilhado — mais rápido agora, mas repete o problema que a 155 já deixou (upload ad-hoc por
tela); rejeitado por criar a mesma dívida de novo em vez de resolvê-la na primeira oportunidade.

## §4 — Onde ficam as funções compartilhadas de parsing

**Decisão**: `_build_phone`, `_height_to_cm`, `_validate_upload` e `_yes_no` saem de
`app/cadastro/routes.py` para um módulo novo `app/cadastro/cadastro_ops.py` — mesmo padrão
`_ops` já usado em `talent_ops.py`/`figurino_ops.py`/`casting_ops.py`/`event_ops.py`/
`observation_ops.py` para núcleo compartilhado entre o handler Jinja e o endpoint API. A rota
Jinja passa a importar dessas funções do módulo novo (mesmo comportamento, zero duplicação).

Na implementação, essa extração foi um passo além do previsto: como as ~100 linhas de
validação/montagem do `Talent` em `submit()` (honeypot → obrigatórios → CPF duplicado →
uploads → `Talent(...)`) não têm nada de `render_template` misturado — só leem
`request.form`/`request.files` e devolvem um `Talent` ou uma mensagem de erro —, essa orquestração
inteira também foi extraída para `cadastro_ops.process_submission(form, files) ->
SubmissionOutcome` (honeypot/talent/error/field), evitando duplicar ~100 linhas idênticas entre
`routes.py` e `cadastro_write.py`. `routes.py` (Jinja) e `cadastro_write.py` (API) ficam cada um
só com ~15 linhas de transporte HTTP (o que fazer com o `SubmissionOutcome`: redirect/render vs.
JSON). `check_cpf_exists(raw_cpf) -> (exists, valid)` recebeu o mesmo tratamento.

**Razão**: diferente da leitura do catálogo (161, onde as queries foram *copiadas* porque a
rota Jinja tinha `render_template` inline e nada extraível), aqui a lógica inteira é pura o
bastante para não precisar de contexto HTTP — extrair para um módulo compartilhado é a mesma
decisão já tomada em toda fatia de ESCRITA anterior (146–160): núcleo compartilhado quando há 2
chamadores reais (Jinja + API).

**Alternativas consideradas**: copiar as funções para `cadastro_write.py` (mesmo padrão da 161,
e o que o `plan.md`/`tasks.md` originalmente descreviam para as 4 funções pequenas) — rejeitado
na prática porque, diferente das queries do catálogo, essa lógica não tem `render_template`
misturado — é uma unidade pura, extraível sem esforço extra; copiar criaria duas fontes de
verdade para a mesma regra de validação (exatamente o problema que o Princípio I existe para
evitar), e o texto de mensagem de erro por campo precisaria ser mantido idêntico manualmente em
dois lugares.

## §5 — CPF: checagem em tempo real via API

**Decisão**: `GET /api/cadastro/check-cpf?cpf=...` replica exatamente `check_cpf` do Jinja
(`app/cadastro/routes.py:104-110`) — mesmo rate limit (`60 per hour`), mesma resposta
`{"exists": bool, "valid": bool}`.

**Razão**: já é um endpoint JSON hoje (só que servido pelo blueprint Jinja) — mover para
`app/api/cadastro_write.py` é uma troca de blueprint, não de lógica.
