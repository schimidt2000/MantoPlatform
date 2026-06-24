# Feature Specification: Arquivos no volume do Railway + migração do Google Drive

**Feature Branch**: `087-migrar-drive-volume`

**Created**: 2026-06-24

**Status**: Draft

**Input**: "Salve os arquivos no próprio volume do Railway de forma organizada. Migre os dados do Google
Drive para o volume do Railway também."

## Contexto

O serviço do app no Railway já tem um **volume persistente** montado em **`/app/instance/uploads`** —
exatamente a pasta onde a plataforma grava os uploads. Logo, **novos arquivos enviados já ficam no
volume** (organizados por subpasta: `talent_photos`, `talent_docs`, `contracts`, `payments`, etc.),
desde que o armazenamento esteja no modo "disco" (não S3).

Falta resolver o **legado**: os talentos cadastrados pelo antigo Google Form têm suas fotos e
documentos **hospedados no Google Drive** (a plataforma só guardou o **link** do Drive — sem cópia).
Hoje, ~**202 de 204 talentos** dependem do Drive (~**540 fotos** + ~**109 documentos**). Se o Drive for
limpo, mexer nas permissões ou o link quebrar, as imagens **somem** do sistema.

Esta feature: (1) garante que os arquivos fiquem **no volume, organizados**; e (2) **migra** os arquivos
que hoje estão no Google Drive para o volume, atualizando os links para apontarem para o nosso
armazenamento — eliminando a dependência do Drive.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Arquivos novos no volume, organizados (Priority: P1)

Como responsável pela plataforma, quero que todo arquivo enviado fique **no volume do Railway**,
organizado em pastas por tipo, para não se perder em deploys e ser fácil de manter.

**Acceptance Scenarios**:

1. **Given** o app em produção com o volume montado na pasta de uploads, **When** alguém envia uma foto
   (ex.: pelo `/cadastro`), **Then** o arquivo é gravado **no volume**, numa **subpasta por tipo**, e
   continua acessível após novos deploys.
2. **Given** os diferentes tipos de upload (fotos de talento, documentos, contratos, comprovantes,
   notas, gastos), **When** são enviados, **Then** cada um vai para sua **subpasta própria** dentro do
   volume.

### User Story 2 - Migrar arquivos do Google Drive para o volume (Priority: P1) 🎯 MVP

Como responsável pela plataforma, quero **migrar** as fotos e documentos dos talentos que hoje estão no
Google Drive para o volume, atualizando os links, para acabar com a dependência do Drive.

**Acceptance Scenarios**:

1. **Given** um talento cuja foto/documento aponta para um link do Google Drive, **When** rodo a
   migração, **Then** o arquivo é **baixado do Drive**, **salvo no volume** (na subpasta certa) e o
   link do talento passa a apontar para o **nosso armazenamento**.
2. **Given** a migração já executada, **When** rodo de novo, **Then** ela **não reprocessa** o que já
   está no volume (idempotente) e só trata o que ainda está no Drive.
3. **Given** um arquivo que **falha** ao baixar (link quebrado/sem permissão), **When** a migração roda,
   **Then** ela **mantém o link original** desse item, registra o erro e **segue** com os demais (não
   perde dados, dá para rodar de novo).
4. **Given** um modo de **simulação (dry-run)**, **When** executo, **Then** vejo **quantos** arquivos
   seriam migrados, **sem** baixar nem alterar nada.
5. **Given** a migração concluída, **When** abro a ficha do talento, **Then** a foto/documento carrega
   **do volume** (sem depender mais do Drive).

### Edge Cases

- Campo vazio ou já apontando para o volume (`/uploads/...`) → ignorado.
- Link que não é do Drive (outra URL externa) → ignorado (fora do escopo).
- Documento que é PDF (não imagem) → migrado e salvo como está; imagens são otimizadas.
- Execução interrompida no meio → o que já migrou permanece; rodar de novo continua de onde parou.

## Requirements *(mandatory)*

### Armazenamento organizado no volume

- **FR-001**: Os uploads MUST ser gravados **no volume** do Railway (modo disco), na pasta montada
  (`/app/instance/uploads`), **organizados por subpasta** conforme o tipo.
- **FR-002**: O comportamento MUST valer para os uploads da plataforma (fotos/documentos de talento,
  e demais anexos), sem depender do Google Drive de ninguém.

### Migração do Google Drive

- **FR-003**: MUST existir uma rotina de **migração** que percorre os talentos e, para cada arquivo
  hospedado no Google Drive (fotos de rosto/corpo, foto de documento, arquivo de CNH), **baixa** o
  arquivo e **salva no volume** na subpasta apropriada.
- **FR-004**: Após salvar, a rotina MUST **atualizar o link** do talento para o caminho do nosso
  armazenamento.
- **FR-005**: A migração MUST ser **idempotente** (rodar de novo não duplica nem reprocessa itens já
  migrados).
- **FR-006**: A migração MUST ser **resiliente a falhas**: um item que falhe **não interrompe** o
  processo nem apaga o link original; o erro é registrado para reexecução.
- **FR-007**: MUST haver um modo **simulação (dry-run)** que apenas relata o que seria migrado.
- **FR-008**: As **imagens** migradas MUST ser otimizadas/comprimidas como os demais uploads da
  plataforma; documentos não-imagem são preservados.

## Success Criteria *(mandatory)*

- **SC-001**: Após a migração, **0** fotos/documentos de talento dependem de links do Google Drive
  (todos servidos do volume).
- **SC-002**: Rodar a migração duas vezes não altera nada na segunda execução (idempotente).
- **SC-003**: Itens com falha de download não derrubam o processo e mantêm o link original para nova
  tentativa.
- **SC-004**: O dry-run informa a contagem exata de arquivos a migrar sem alterar dados.
- **SC-005**: Novos uploads continuam sendo gravados no volume, organizados por tipo, e sobrevivem a
  deploys.

## Key Entities

- **Talento**: registro existente; os campos de mídia (foto do rosto, foto de corpo, foto do documento,
  arquivo da CNH) deixam de apontar para o Drive e passam a apontar para o volume.

## Assumptions

- **Mount path = pasta de uploads**: o volume já está montado em `/app/instance/uploads`; portanto,
  manter o armazenamento no **modo disco** (sem S3) faz os uploads caírem direto no volume. Nenhuma
  mudança de caminho é necessária.
- **Escopo da migração = campos de mídia do Talento** (rosto, corpo, documento, CNH). Outras
  integrações com Drive (ex.: sincronização de figurino) ficam **fora** desta feature.
- **Download dos arquivos do Drive**: os links hoje já são exibidos publicamente na plataforma, logo os
  arquivos são baixáveis a partir do próprio link (com tratamento para o formato de "documento" do
  Drive). Itens não acessíveis são pulados e relatados.
- **Execução**: rotina operacional rodada pela equipe (uma vez, mais reexecuções se necessário), com
  dry-run para conferência antes. Pode rodar em produção apontando para o volume.
- **Otimização**: imagens passam pela mesma compressão dos uploads atuais; PDFs/documentos são mantidos.
