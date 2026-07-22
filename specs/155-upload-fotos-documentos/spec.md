# Feature Specification: Upload de Fotos e Documentos (Talento + Figurino)

**Feature Branch**: `155-upload-fotos-documentos`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Upload de fotos/documentos — fecha a US3 (Talentos/Figurino) da migração React (144). Migrar para React o upload que ficou fora da fatia 154: (1) fotos/documentos do talento — rosto, corpo inteiro, documento, CNH — no perfil do talento (CASTING/SUPERADMIN); (2) foto da ficha de figurino, incluindo rotação (FIGURINO/SUPERADMIN). Mesmo padrão da migração de upload de anexos do evento (153): multipart, preview, remover anexo existente. Escopo explicitamente fora (por spec da 154): impressão de ficha, sync com Google Drive, avaliações de talentos, portal do próprio talento, import via Sheets — nada disso muda aqui."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enviar/substituir foto ou documento do talento (Priority: P1)

Como Casting, ao abrir o perfil de um talento na tela React, preciso enviar (ou substituir) a
foto de rosto, a foto de corpo inteiro, o documento de identidade ou a CNH, direto pela tela —
sem precisar abrir a tela antiga (Jinja) só para isso.

**Why this priority**: É a lacuna que mais aparece no dia a dia — perfil de talento sem foto
atual é o motivo mais comum de alguém ainda abrir a tela antiga depois da fatia 154. Fechar
isso é o que de fato completa a US3.

**Independent Test**: No perfil React de um talento, enviar uma foto de rosto via seletor de
arquivo e ver a miniatura atualizada na tela sem reload manual; repetir para corpo
inteiro/documento/CNH.

**Acceptance Scenarios**:

1. **Given** um talento sem foto de rosto, **When** um usuário Casting/Superadmin envia um
   arquivo JPG/PNG/WEBP no campo "foto de rosto", **Then** a foto aparece na tela e fica
   salva no perfil (visível também na tela antiga, mesma fonte de dado).
2. **Given** um talento que já tem CNH cadastrada, **When** o usuário envia um novo arquivo no
   campo CNH, **Then** o arquivo antigo é substituído (não fica duplicado) e o novo aparece na
   tela.
3. **Given** um talento com uma foto/documento já enviado, **When** o usuário aciona "remover"
   nesse campo, **Then** o arquivo é apagado e o campo volta ao estado vazio (com opção de
   enviar um novo).
4. **Given** um usuário sem papel Casting/Superadmin, **When** ele tenta enviar ou remover
   foto/documento pela API, **Then** a ação é recusada (403) e a tela não mostra os controles
   de envio/remoção.
5. **Given** um arquivo de formato não aceito (ex.: `.exe`, `.docx` num campo de foto), **When**
   o usuário tenta enviar, **Then** a tela mostra mensagem de erro amigável e nada é salvo.

---

### User Story 2 - Enviar/rotacionar/remover foto da ficha de figurino (Priority: P2)

Como Figurino, ao abrir uma ficha de figurino na tela React, preciso enviar a foto do figurino,
girar essa foto quando ela vier na orientação errada, e remover a foto — tudo pela tela nova.

**Why this priority**: Fecha o CRUD de figurino da fatia 154 (que ficou só com nome/peças/
notas); é a segunda lacuna mais usada, mas menos frequente que fotos de talento no dia a dia.

**Independent Test**: Numa ficha de figurino sem foto, enviar uma imagem, depois rotacionar
90°, depois remover — cada ação reflete na tela imediatamente.

**Acceptance Scenarios**:

1. **Given** uma ficha de figurino sem foto, **When** um usuário Figurino/Superadmin envia um
   arquivo JPG/PNG/WEBP, **Then** a foto aparece na ficha.
2. **Given** uma ficha com foto, **When** o usuário aciona "girar", **Then** a foto é rotacionada
   90° e a tela mostra o resultado atualizado.
3. **Given** uma ficha com foto, **When** o usuário envia uma foto nova, **Then** a antiga é
   substituída (não duplica arquivo).
4. **Given** uma ficha com foto, **When** o usuário aciona "remover", **Then** a foto é apagada
   e a ficha volta ao estado sem foto.
5. **Given** um usuário sem papel Figurino/Superadmin, **When** ele tenta enviar/girar/remover
   pela API, **Then** a ação é recusada (403) e a tela não mostra os controles.

---

### Edge Cases

- Enviar um arquivo vazio ou sem selecionar arquivo → erro amigável, nada é salvo (paridade com
  o comportamento atual da tela antiga).
- Enviar um arquivo de imagem corrompido/ilegível no campo de rotação → operação de rotação
  falha com mensagem amigável, foto original permanece intacta (paridade com o comportamento
  atual).
- Remover uma foto/documento que já está vazio → operação é um no-op seguro (não quebra),
  responde como sucesso ou erro amigável, nunca 500.
- Trocar de foto duas vezes seguidas rapidamente → cada substituição limpa o arquivo anterior;
  não deve acumular arquivos órfãos além do último substituído com sucesso.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE permitir que um usuário CASTING/SUPERADMIN envie, pela tela React
  de perfil de talento, um arquivo para cada um dos quatro campos existentes: foto de rosto,
  foto de corpo inteiro, documento de identidade, CNH.
- **FR-002**: O sistema DEVE aceitar JPG/PNG/WEBP nos campos de foto (rosto, corpo inteiro) e
  JPG/PNG/WEBP/PDF nos campos de documento (documento de identidade, CNH) — mesma regra já
  aplicada na tela antiga.
- **FR-003**: Ao enviar um novo arquivo num campo que já tinha um arquivo, o sistema DEVE
  substituir o arquivo anterior (apagando-o do armazenamento), nunca acumular arquivos órfãos.
- **FR-004**: O sistema DEVE permitir que um usuário CASTING/SUPERADMIN remova um
  arquivo já enviado em qualquer um dos quatro campos do talento, deixando o campo vazio.
- **FR-005**: O sistema DEVE permitir que um usuário FIGURINO/SUPERADMIN envie, pela tela React
  de ficha de figurino, um arquivo de foto (JPG/PNG/WEBP), substituindo a foto anterior se
  houver.
- **FR-006**: O sistema DEVE permitir que um usuário FIGURINO/SUPERADMIN rotacione em 90° a
  foto existente de uma ficha de figurino, persistindo o resultado.
- **FR-007**: O sistema DEVE permitir que um usuário FIGURINO/SUPERADMIN remova a foto de uma
  ficha de figurino, deixando a ficha sem foto.
- **FR-008**: O sistema DEVE recusar (403) qualquer envio, rotação ou remoção de arquivo feita
  por usuário sem o papel exigido (CASTING/SUPERADMIN para talento; FIGURINO/SUPERADMIN para
  figurino) — paridade com as regras já aplicadas na tela antiga.
- **FR-009**: O sistema DEVE rejeitar arquivos fora dos formatos aceitos por campo, com
  mensagem de erro amigável, sem alterar o estado salvo.
- **FR-010**: As telas React de perfil de talento e de ficha de figurino DEVEM refletir o
  resultado de envio/rotação/remoção imediatamente, sem exigir reload manual da página.
- **FR-011**: O comportamento da tela antiga (Jinja) para os mesmos fluxos DEVE permanecer
  idêntico ao de antes desta fatia — mesmo armazenamento, mesmos campos, sem regressão.

### Key Entities

- **Talento (Talent)**: já existente; ganha operação de escrita nos campos de arquivo (foto de
  rosto, foto de corpo inteiro, documento de identidade, CNH) — os campos em si não mudam,
  só passam a ser editáveis pela tela React.
- **Ficha de Figurino (FigurinoSheet)**: já existente; ganha operação de escrita no campo de
  foto (upload, rotação, remoção) pela tela React.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário Casting consegue enviar, substituir e remover qualquer uma das quatro
  fotos/documentos de um talento inteiramente pela tela React, sem abrir a tela antiga.
- **SC-002**: Um usuário Figurino consegue enviar, rotacionar e remover a foto de uma ficha de
  figurino inteiramente pela tela React, sem abrir a tela antiga.
- **SC-003**: 100% dos envios/remoções feitos pela tela React ficam visíveis, sem diferença de
  comportamento, na tela antiga (mesma fonte de dado) — verificado por paridade automatizada.
- **SC-004**: Usuário sem o papel exigido não consegue enviar, rotacionar nem remover nenhum
  arquivo (bloqueado tanto na tela quanto na API).

## Assumptions

- Remover foto/documento é uma capacidade **nova** na tela React que a tela antiga não tinha
  como ação isolada (Jinja só substitui ao enviar um novo arquivo) — esta fatia adiciona
  "remover" nos dois lados (API nova + pequeno ajuste na visão antiga, se necessário para
  paridade) já que faz parte do padrão consolidado na migração de anexos de evento (153).
- Rotação de foto se aplica só à ficha de figurino (é a única entidade com essa operação hoje);
  fotos/documentos de talento não têm rotação na tela antiga e não ganham nesta fatia.
- Tamanho máximo de arquivo e diretório de armazenamento seguem o padrão já configurado no
  sistema (`app/storage.py`), sem mudança nesta fatia.
- Continuam fora do escopo (herdado da spec da 154): impressão de ficha de figurino, sincronização
  com Google Drive, dashboard de avaliações de talentos, portal do próprio talento, importação
  via Google Sheets.
