# Especificação Técnica de Formulário: Contrato Corporativo (Pessoa Jurídica)

Este documento descreve detalhadamente a estrutura, campos, validações e comportamentos do formulário de **Contrato Corporativo / Informações da Empresa** da **Manto Produções**, otimizado para implementação automatizada via LLM (Claude Code).

---

## 1. Diretrizes Gerais de Design e Interface (UI/UX)
- **Tipografia:** Fonte Sans-serif limpa, moderna e altamente legível (ex: Montserrat, Inter ou Roboto).
- **Estilo Visual:** Design limpo, empilhado verticalmente (coluna única) com amplo espaçamento entre elementos para facilitar o preenchimento.
- **Campos Ativos:** Quando focados/ativos, os inputs ganham uma borda verde clara.
- **Campos Obrigatórios:** Marcados com um asterisco vermelho (`*`) colado ao início do label.

---

## 2. Estrutura do Formulário e Campos

### SEÇÃO 1: Informações da Empresa
*Título em destaque: "Informações da Empresa" (Negrito, tamanho de cabeçalho principal).*

1. **Razão Social** `*`
   - **Tipo:** Texto (`input type="text"`)
   - **Obrigatoriedade:** Sim

2. **CNPJ** `*`
   - **Tipo:** Texto com máscara (`input type="text"`, máscara: `00.000.000/0001-00`)
   - **Obrigatoriedade:** Sim

3. **Representante Legal** `*`
   - **Tipo:** Texto (`input type="text"`)
   - **Obrigatoriedade:** Sim

4. **E-mail** `*`
   - **Tipo:** E-mail (`input type="email"`)
   - **Placeholder:** "E-mail da empresa" (em cinza claro, caixa baixa com a inicial maiúscula)
   - **Obrigatoriedade:** Sim

5. **Telefone** `*`
   - **Tipo:** Telefone com seletor de país (`input type="tel"`)
   - **Componente:** Dropdown com bandeira (Padrão: Brasil `+55`) + campo de número com máscara.
   - **Texto de Apoio (Subtexto):** "Telefone da empresa" (Texto menor, cinza, logo abaixo do input).
   - **Obrigatoriedade:** Sim

6. **Endereço** `*`
   - **Tipo:** Texto (`input type="text"`)
   - **Placeholder:** "Endereço da empresa" (em cinza claro)
   - **Obrigatoriedade:** Sim

---

### SEÇÃO 2: Dados do Responsável pelo Preenchimento
*Título em destaque: "Dados do Responsável pelo Preenchimento" (Negrito, tamanho igual ao da primeira seção).*

7. **Nome Completo** `*`
   - **Tipo:** Texto (`input type="text"`)
   - **Placeholder:** "Nome Completo do Responsável pelo Preenchimento" (em cinza claro)
   - **Obrigatoriedade:** Sim

8. **CPF** `*`
   - **Tipo:** Texto com máscara (`input type="text"`, máscara: `000.000.000-00`)
   - **Placeholder:** "CPF do Responsável pelo Preenchimento" (em cinza claro)
   - **Obrigatoriedade:** Sim

9. **Número de Whatsapp** `*`
   - **Tipo:** Telefone com seletor de país (`input type="tel"`)
   - **Componente:** Dropdown com bandeira (Padrão: Brasil `+55`) + campo de número com máscara.
   - **Texto de Apoio (Subtexto):** "Esse WhatsApp receberá o contrato para assinatura e também os contatos futuros da empresa para confirmações" (Texto menor, cinza, logo abaixo do input).
   - **Obrigatoriedade:** Sim

---

### SEÇÃO 3: Dados do Evento Corporativo

10. **Data do Evento** `*`
    - **Tipo:** Linha composta (dois campos lado a lado):
      - **Data:** Input de data (`input type="date"`), placeholder/label interno: "Selecionar data" com ícone de calendário à direita.
      - **Hora:** Input de hora (`input type="time"`), placeholder/label interno: "Hora" com ícone de relógio à direita.
    - **Obrigatoriedade:** Sim (Ambos)

11. **Endereço completo do evento** `*`
    - **Tipo:** Texto (`input type="text"`)
    - **Placeholder:** "CEP, Número, Cidade e Estado" (em cinza claro)
    - **Obrigatoriedade:** Sim

12. **Período De Contratação** `*`
    - **Tipo:** Texto (`input type="text"`)
    - **Obrigatoriedade:** Sim

13. **Briefing do Evento** `*`
    - **Tipo:** Input de texto ou Área de texto (`input type="text"` ou `textarea`)
    - **Texto de Apoio (Subtexto):** "Descrever detalhadamente como deve acontecer a ação" (Texto menor, cinza, logo abaixo do input).
    - **Obrigatoriedade:** Sim

---

### SEÇÃO 4: Condições de Pagamento

14. **Forma de Pagamento** `*`
    - **Tipo:** Select / Dropdown customizado (ganha borda verde clara quando aberto, possui uma lupa ou ícone de seta à direita).
    - **Obrigatoriedade:** Sim
    - **Opções disponíveis:**
      - `À vista antecipado`
      - `Em 2x`
      - `Faturado`
      - `Boleto`
      - `Outros`

15. **Descreva Outros**
    - **Tipo:** Texto (`input type="text"`)
    - **Obrigatoriedade:** Não (Opcional por padrão, ativa-se ou torna-se obrigatório via regra condicional se a opção `Outros` for selecionada acima).

---

### Rodapé / Ação Comercial

- **Botão Enviar:**
  - **Texto:** "Enviar no WhatsApp"
  - **Estilo:** Botão retangular verde vibrante, cantos arredondados, contendo o ícone oficial do WhatsApp alinhado à esquerda do texto.
  - **Comportamento:** Valida todos os campos obrigatórios marcados com `*`. Ao disparar, compila todas as informações estruturadas da empresa, do responsável e do briefing em um bloco de texto legível e redireciona o usuário para o link da API do WhatsApp.
