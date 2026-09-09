# Modelo de dados — Feature 297

Uma migration aditiva, com `down_revision = "b7d2e4f1a9c3"` (head conferido em 09/09). Nenhuma
coluna existente muda de tipo, nenhuma linha é reescrita no `upgrade`.

## 1. `nfc_tag_deliveries` — 11 colunas novas

A tabela existe desde a feature 261 e hoje guarda só `kind`, `title`, `file_path`, `link_url`,
`is_active`, `sort_order` e as datas (`app/models.py:2342-2389`). Ela não sabe nada sobre o arquivo
que aponta: nem tamanho, nem duração, nem tipo. É por isso que ninguém percebeu que os vídeos eram
grandes demais.

| Coluna | Tipo | Nulo | Default | Para que serve |
|---|---|---|---|---|
| `source_file_path` | String(500) | sim | — | O arquivo cru recebido, em `nfc_media/entrada/`. Existe só entre o envio e o fim da conversão; apagado depois. Guardado em coluna, e não em memória, para sobreviver a um deploy no meio do caminho |
| `master_file_path` | String(500) | sim | — | O mestre 1080p **sem moldura**, em `nfc_media/mestres/`. É a origem de todo reprocessamento (decisão D4) |
| `mime_type` | String(60) | sim | — | Gravado na conversão. Hoje o tipo é readivinhado da extensão a cada requisição, e `.m4v` produz `video/m4v`, que não existe |
| `file_size_bytes` | BigInteger | sim | — | Peso do arquivo entregue. É o número que teria denunciado o problema meses atrás |
| `duration_seconds` | Numeric(7,2) | sim | — | Duração, para a tela e para o cálculo de peso por segundo |
| `width` | Integer | sim | — | Largura do entregue |
| `height` | Integer | sim | — | Altura do entregue. Com a largura, decide o retrato na tela |
| `has_frame` | Boolean | não | `false` | Se a moldura está gravada neste arquivo. É também o que a caixinha do diálogo pediu |
| `processing_status` | String(20) | não | `'pronto'` | `pendente`, `processando`, `pronto`, `falhou` |
| `processing_error` | String(500) | sim | — | Motivo legível da falha, mostrado no card com o botão de tentar de novo |
| `processed_at` | DateTime | sim | — | Quando a conversão terminou |

**Estados e transições**:

```text
pendente ──(claim atômico)──► processando ──(ffmpeg ok)──► pronto
    ▲                              │
    └──(preso há > 30 min)─────────┘
                                   └──(ffmpeg falhou)────► falhou ──(reprocessar)──► pendente
```

- `pronto` é o único estado que a **rota pública** enxerga. Nos demais, `deliveries` sai vazia e a
  cliente vê a página sem a mensagem especial (FR-015 continua valendo: o shape não muda).
- O ERP enxerga todos os estados, porque é onde a equipe está esperando.
- **As 10 linhas existentes nascem `pronto`**, com `has_frame = false` e o arquivo atual como
  entregue. O `upgrade` não as reescreve; quem as converte é o comando de reprocessamento, rodado à
  mão depois do deploy.

**Claim entre os três workers** — extensão do padrão de `app/calendar/sync.py:122`, mas na própria
linha da entrega em vez de em `site_settings`, porque aqui a unidade de trabalho é o registro:

```sql
UPDATE nfc_tag_deliveries
   SET processing_status = 'processando', updated_at = :agora
 WHERE id = (SELECT id FROM nfc_tag_deliveries
              WHERE processing_status = 'pendente'
              ORDER BY id LIMIT 1)
   AND processing_status = 'pendente'
RETURNING id;
```

Quem receber linha leva o trabalho; os outros dois recebem nada e voltam a dormir. O `AND` repetido
não é redundância: sem ele, dois workers que selecionassem o mesmo `id` fariam dois `UPDATE`.

**Índice novo**: `ix_nfc_tag_deliveries_status` parcial em `processing_status`, com
`postgresql_where=processing_status != 'pronto'` e o `sqlite_where` correspondente — o padrão do
índice parcial da 272 (`migrations/versions/b7d2e4f1a9c3_notifications.py:57-61`). A fila é sempre
minúscula; o índice existe para o claim não varrer a tabela.

## 2. `nfc_tag_messages` — tabela nova

O recado da cliente. Nome no plural, como `nfc_tag_deliveries`.

| Coluna | Tipo | Nulo | Default | Observação |
|---|---|---|---|---|
| `id` | Integer PK | não | — | |
| `tag_id` | Integer FK `nfc_tags.id` | não | — | `ondelete="CASCADE"`: apagar a tag leva os recados |
| `client_id` | Integer FK `clients.id` | sim | — | `ondelete="SET NULL"`. **Fotografia do vínculo no momento do envio** — a tag pode ser reassociada depois, e o recado pertence a quem o recebeu |
| `author_name` | String(120) | sim | — | Opcional, como a spec decidiu |
| `message` | Text | não | — | Limite de 1000 caracteres validado no núcleo, como o resto da casa faz |
| `created_at` | DateTime | não | `now_sp` | Relógio de São Paulo, convenção do projeto |
| `read_at` | DateTime | sim | — | `NULL` = não lido. Mesma convenção de `notifications` (`app/models.py:603-643`) |

**Índices**: `ix_nfc_tag_messages_tag` em `(tag_id, created_at DESC)` para a lista da tag, e
`ix_nfc_tag_messages_client` em `client_id` para um dia cruzar recado com cliente.

**Relação**: `tag.messages`, com `cascade="all, delete-orphan"`, espelhando `tag.deliveries`
(`app/models.py:2386-2389`).

**O que NÃO tem, de propósito**: IP, impressão do navegador, e-mail, telefone. O controle de abuso
é o limite de taxa, que o `flask-limiter` faz em memória sem persistir nada (research D7).

## 3. `site_settings` — 2 colunas novas

Linha única `id = 1`. Segue exatamente o molde de `logo_path` (`app/models.py:809` e
`app/admin/config_ops.py:78-88`): o banco guarda o caminho, o arquivo mora no disco.

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| `nfc_frame_path` | String(300) | sim | A moldura PNG do sistema, em `nfc_media/sistema/`. `NULL` = ainda não cadastrada, e todo envio sai sem moldura com aviso |
| `nfc_intro_video_path` | String(300) | sim | O vídeo de abertura. `NULL` = a página pula a capa e abre direto no menu |

Ambos com **nome de arquivo fixo** (`moldura.png`, `abertura.mp4`), sobrescrito a cada cadastro,
como o `logo.png` faz. A consequência conhecida é que o navegador pode segurar a versão antiga em
cache; por isso as duas rotas que servem esses arquivos mandam `max_age` curto e um parâmetro de
versão derivado da data de modificação.

## 4. Layout do disco

```text
instance/nfc_media/
├── <uuid>.mp4                 # o arquivo ENTREGUE (nomes de hoje, inalterados)
├── entrada/<uuid>.<ext>       # o cru recebido; vive minutos
├── mestres/<uuid>.mp4         # o mestre 1080p sem moldura
└── sistema/
    ├── moldura.png
    └── abertura.mp4
```

O backup de mídia empacota `instance/nfc_media` inteiro (`app/backup_drive.py:31`), então as
subpastas entram sozinhas. `entrada/` pode aparecer no pacote com um arquivo a meio caminho — é
inofensivo e some no backup seguinte.

## 5. Constantes novas (`app/constants.py`)

| Constante | Valor | Porquê |
|---|---|---|
| `MANTO_SPOTIFY_URL` | o link que o dono mandou | Endereço público é constante de código, nunca env (Princípio XIV), igual ao `MANTO_INSTAGRAM_URL` que já está em `:85` |
| `NFC_VIDEO_LARGURA_MAXIMA` | `1080` | Decisão do dono na pergunta 5 |
| `NFC_VIDEO_CRF` | `23` | Medido: dá 14,5 MB por 30 s (research D3) |
| `NFC_MOLDURA_EXTENSOES` | `frozenset({".png"})` | A moldura precisa de canal alfa; JPEG não tem |
| `NFC_MENSAGEM_MAX_CHARS` | `1000` | Teto do recado |
| `NFC_PROCESSAMENTO_PRESO_MINUTOS` | `30` | Depois disso, `processando` volta a `pendente` |
