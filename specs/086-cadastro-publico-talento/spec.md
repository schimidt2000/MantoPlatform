# Feature Specification: Formulário público de cadastro de talento (substituir Google Forms)

**Feature Branch**: `086-cadastro-publico-talento`

**Created**: 2026-06-24

**Status**: Draft

**Input**: "O formulário do Google é ótimo, mas muita gente não tem espaço no Drive e não consegue subir
fotos/documentos. Preciso de um formulário nosso, com as mesmas perguntas, importável no banco de
talentos, com limite de tamanho de arquivos por segurança — algo melhor que o Google Forms. O link
precisa ser acessível a qualquer pessoa, ex.: portal.mantoproducoes.com.br/cadastro."

## Contexto

Hoje o onboarding de talentos usa um **Google Form** cujos uploads vão para o **Google Drive** de quem
preenche — e muita gente **não tem espaço no Drive**, travando o envio de fotos e documentos. A solução
é um **formulário próprio**, público, em **`/cadastro`**, com as **mesmas perguntas** do Google Form,
onde os arquivos são enviados para o **armazenamento da Manto** (não depende do Drive do candidato).
Cada envio cria um talento **pendente** no banco, para revisão/aprovação pela equipe — sem precisar mais
importar planilha. Há **limite de tamanho e tipo** de arquivo por segurança.

A plataforma já possui uma camada de armazenamento (`save_file`) que comprime imagens e grava em disco
(dev) ou em object storage S3/R2 (produção) — portanto os arquivos persistem e ficam acessíveis por URL.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Candidato se cadastra pelo link público (Priority: P1) 🎯 MVP

Como pessoa interessada em trabalhar com a Manto, quero abrir um link público e preencher meus dados e
enviar minhas fotos/documentos **direto pelo formulário**, sem depender do Google Drive.

**Acceptance Scenarios**:

1. **Given** que abro `/cadastro` sem estar logada, **When** a página carrega, **Then** vejo o
   formulário completo (mesmas perguntas do Google Form), organizado em seções, e funcional no celular.
2. **Given** que preencho os campos obrigatórios e anexo as fotos exigidas, **When** envio, **Then**
   meus arquivos são enviados ao armazenamento da Manto e vejo uma **tela de confirmação** de sucesso.
3. **Given** que deixo um campo obrigatório vazio ou anexo um arquivo grande/!tipo inválido, **When**
   tento enviar, **Then** recebo uma mensagem clara e o envio é bloqueado até corrigir.
4. **Given** que envio um arquivo dentro do limite, **When** é uma foto, **Then** ela é aceita e fica
   acessível depois (sem depender do meu Drive).

### User Story 2 - Cadastro vira talento pendente para revisão (Priority: P1)

Como equipe da Manto, quero que cada cadastro enviado apareça como **talento pendente** no banco, para
revisar e aprovar — sem importar planilha.

**Acceptance Scenarios**:

1. **Given** um envio válido, **When** consulto o banco de talentos em "pendentes", **Then** o novo
   talento aparece com os dados e as fotos/documentos preenchidos.
2. **Given** um CPF que **já existe** no banco, **When** alguém tenta se cadastrar com ele, **Then** o
   sistema informa que o CPF já está cadastrado e não cria duplicado.
3. **Given** um talento pendente vindo do formulário, **When** a equipe aprova, **Then** ele passa a
   ativo pelo fluxo de aprovação já existente.

### User Story 3 - Segurança e limites (Priority: P2)

Como responsável pela plataforma, quero que o formulário público seja protegido contra abusos e
arquivos perigosos.

**Acceptance Scenarios**:

1. **Given** o formulário público, **When** alguém envia muitas vezes em sequência, **Then** há
   limitação de taxa para conter spam/abuso.
2. **Given** um upload, **When** o arquivo excede o tamanho permitido ou tem tipo não permitido,
   **Then** é rejeitado com mensagem clara.
3. **Given** os campos de texto, **When** chegam ao banco, **Then** são tratados/sanitizados (sem
   quebrar a exibição interna).

### Edge Cases

- Envio sem fotos obrigatórias → bloqueado com mensagem.
- Conexão lenta no celular → indicação de "enviando…" e prevenção de duplo envio.
- CPF com pontuação → normalizado para dígitos; inválido (<11 dígitos) é rejeitado.
- Altura digitada como "1,75" → convertida para centímetros, como na importação atual.
- Acesso pelo domínio `portal.mantoproducoes.com.br/cadastro` → a página abre (não é redirecionada para
  o login do portal).

## Requirements *(mandatory)*

### Acesso e perguntas

- **FR-001**: A página `/cadastro` MUST ser **pública** (sem login), acessível inclusive em
  `portal.mantoproducoes.com.br/cadastro`.
- **FR-002**: O formulário MUST conter as **mesmas perguntas** do Google Form atual: nome completo, nome
  artístico, telefone, e-mail, data de nascimento, CPF, RG, gênero, raça, idiomas, habilidades, altura,
  manequim superior/inferior, número do sapato, passaporte/visto, chave PIX (+ tipo + secundária), já
  trabalhou com a Manto, onde conheceu a Manto, dados do carro (opcional), CNH (vencimento + arquivo,
  opcional), foto do rosto, foto de corpo inteiro e foto de documento.
- **FR-003**: Os campos obrigatórios MUST ser claramente sinalizados; no mínimo **nome** e **CPF
  válido** são obrigatórios (regra mínima já usada na importação), além das fotos essenciais.

### Upload e armazenamento

- **FR-004**: Os arquivos MUST ser enviados para o **armazenamento da Manto** (não para o Drive do
  candidato) e ficar acessíveis por URL depois do envio.
- **FR-005**: Cada arquivo MUST ter **limite de tamanho** e **tipos permitidos** (imagens para fotos;
  imagem ou PDF para documentos); envios fora disso são rejeitados com mensagem clara.
- **FR-006**: As imagens enviadas MUST ser otimizadas/comprimidas no armazenamento (como o restante da
  plataforma), reduzindo espaço sem perder usabilidade.

### Importação no banco

- **FR-007**: Cada envio válido MUST criar um **talento pendente** (`status` pendente) no banco, com
  origem identificável como cadastro público, sem necessidade de importar planilha.
- **FR-008**: O sistema MUST impedir **CPF duplicado**, informando o candidato sem criar registro novo.
- **FR-009**: Os talentos do formulário MUST entrar no **mesmo fluxo de aprovação** já existente
  (pendente → ativo).

### Segurança

- **FR-010**: O endpoint público MUST ter **limitação de taxa** para conter spam/abuso.
- **FR-011**: O formulário MUST ter proteção básica anti-bot (ex.: campo armadilha/honeypot) e
  prevenção de **duplo envio**.
- **FR-012**: Entradas de texto MUST ser tratadas para não quebrar a exibição interna nem permitir
  conteúdo perigoso.

## Success Criteria *(mandatory)*

- **SC-001**: Uma pessoa sem conta consegue concluir o cadastro com fotos pelo celular em menos de 5
  minutos, sem usar o Google Drive.
- **SC-002**: 100% dos envios válidos viram talento **pendente** com os arquivos acessíveis.
- **SC-003**: CPF duplicado nunca gera registro novo.
- **SC-004**: Arquivos acima do limite/!tipo são rejeitados em 100% dos casos com mensagem clara.
- **SC-005**: O link funciona publicamente (incluindo no domínio do portal) sem exigir login.

## Key Entities

- **Talento (cadastro público)**: mesmo registro de Talento já existente; criado com `status` pendente e
  origem "cadastro público". Campos preenchidos a partir das respostas; fotos/documentos guardados como
  URLs do armazenamento da Manto.

## Assumptions

- **Mesmas perguntas = campos atuais de Talento** (derivados do mapeamento de importação do Google Form):
  básicos, medidas, passaporte/visto, PIX, carro, CNH, fotos (rosto, corpo, documento). Campos de carro
  e CNH são opcionais.
- **Status inicial = pendente**: novos cadastros entram para revisão/aprovação (não ativos
  imediatamente), dando controle à equipe. Origem registrada como cadastro público.
- **Limites de arquivo** (padrão, ajustável depois): fotos até ~8 MB cada; documentos até ~10 MB;
  tipos: JPG/PNG/WEBP para fotos, e também PDF para documentos. O teto global de requisição da
  plataforma permanece como hoje.
- **Armazenamento**: usa a camada existente (`save_file`) — disco em dev, S3/R2 em produção; isso já
  resolve a dependência do Drive e a persistência dos arquivos.
- **Subdomínio**: `portal.mantoproducoes.com.br/cadastro` deve abrir o formulário; a regra de
  roteamento do domínio do portal precisa liberar `/cadastro` (hoje ela manda tudo para o login do
  portal). O apontamento DNS do subdomínio é tarefa de infraestrutura, fora do código.
- **Sem captcha de terceiros por ora**: proteção via limitação de taxa + honeypot; captcha pode ser
  adicionado depois se houver abuso.
- **Aprovação**: reaproveita o fluxo/visão de "pendentes" já existente no banco de talentos; esta
  feature não redesenha a aprovação.
