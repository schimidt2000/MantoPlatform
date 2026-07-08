# Especificação Técnica de Formulário: Pré-Contrato (Pessoa Física / Comum)

Este documento descreve detalhadamente a estrutura, campos, validações e comportamentos do formulário de **Informações para Pré-Contrato** da **Manto Produções**, otimizado para implementação automatizada via LLM (Claude Code).

---

## 1. Diretrizes Gerais de Design e Interface (UI/UX)
- **Tipografia:** Fonte Sans-serif limpa, moderna e altamente legível (ex: Montserrat, Inter ou Roboto).
- **Cores Principais:**
  - **Identidade/Logo:** Roxo Vibrante (títulos secundários e logo) e detalhes em Dourado/Glitter.
  - **Botão Principal:** Verde WhatsApp (`#25D366` ou `#24b33b`), texto branco com ícone do WhatsApp.
  - **Campos de Input:** Borda cinza clara por padrão. Quando focados/ativos, ganham uma borda verde clara (conforme capturas de tela).
  - **Campos Obrigatórios:** Marcados com um asterisco vermelho (`*`) colado ao início do label.
- **Layout:** Disposição vertical e linear (Single Column), com espaçamento generoso entre os blocos (inputs empilhados). Campos de data e hora ficam lado a lado na mesma linha.

---

## 2. Estrutura do Formulário e Campos

### Cabeçalho
- **Título principal:** "INFORMAÇÕES PARA PRÉ CONTRATO" (Caixa alta, negrito, cor escura).
- **Logotipo:** Centralizado, com o texto "MANTO" em roxo e "produções" espaçado logo abaixo, sobreposto por uma espiral dourada abstrata.

---

### SEÇÃO 1: Dados do Contratante

1. **Nome Completo Contratante** `*`
   - **Tipo:** Texto (`input type="text"`)
   - **Obrigatoriedade:** Sim

2. **Endereço completo da contratante** `*`
   - **Tipo:** Texto (`input type="text"`)
   - **Placeholder:** "ENDEREÇO DA CONTRATANTE" (em caixa alta, cinza claro)
   - **Obrigatoriedade:** Sim

3. **CPF** `*`
   - **Tipo:** Texto com máscara (`input type="text"`, máscara: `000.000.000-00`)
   - **Obrigatoriedade:** Sim

4. **e-mail** `*`
   - **Tipo:** E-mail (`input type="email"`)
   - **Obrigatoriedade:** Sim

5. **Número de Whatsapp** `*`
   - **Tipo:** Telefone com seletor de país (`input type="tel"`)
   - **Componente:** Dropdown com bandeira (Padrão: Brasil `+55`) + campo de texto para o número com máscara `(DD) 9XXXX-XXXX`.
   - **Texto de Apoio (Subtexto):** "Esse número será usado para assinar o contrato" (Texto menor, cinza, logo abaixo do input).
   - **Obrigatoriedade:** Sim

6. **Gostaria que a confirmação do evento seja com assessoria? Se sim, digite o telefone**
   - **Tipo:** Telefone com seletor de país (`input type="tel"`, opcional)
   - **Componente:** Mesma estrutura do WhatsApp (Dropdown bandeira `+55` + número).
   - **Obrigatoriedade:** Não (Opcional)

---

### SEÇÃO 2: Dados do Evento

7. **Nome do Aniversariante**
   - **Tipo:** Texto (`input type="text"`)
   - **Obrigatoriedade:** Não

8. **Idade a Completar do Aniversariante**
   - **Tipo:** Texto ou Número (`input type="text"` ou `number`)
   - **Obrigatoriedade:** Não

9. **Tipo de Contratação** `*`
   - **Tipo:** Select / Dropdown customizado
   - **Obrigatoriedade:** Sim
   - **Opções disponíveis:**
     - `Receptivo e Interativo`
     - `Receptivo, Interativo e Show`
     - `Social`

10. **Quantidade de Personagens** `*`
    - **Tipo:** Texto ou Número (`input type="text"`)
    - **Obrigatoriedade:** Sim

11. **Quais personagens?** `*`
    - **Tipo:** Texto (`input type="text"`)
    - **Obrigatoriedade:** Sim

12. **Tema do Evento** `*`
    - **Tipo:** Texto (`input type="text"`)
    - **Obrigatoriedade:** Sim

13. **Data do Evento** `*`
    - **Tipo:** Linha dupla/composta contendo:
      - **Data:** Input de data (`input type="date"`), placeholder/label interno: "Selecionar data" com ícone de calendário à direita.
      - **Hora:** Input de hora (`input type="time"`), placeholder/label interno: "Hora" com ícone de relógio à direita.
    - **Obrigatoriedade:** Sim (Ambos os campos)

14. **Período De Contratação** `*`
    - **Tipo:** Texto (`input type="text"`, ex: para especificar a duração ou turno)
    - **Obrigatoriedade:** Sim

---

### SEÇÃO 3: Endereço do Evento
*Subtítulo em destaque: "Endereço do Evento" (Negrito, tamanho maior do que os labels comuns).*

15. **Espaço Escolhido para o Evento** `*`
    - **Tipo:** Botões de Rádio (`input type="radio"`) empilhados verticalmente.
    - **Obrigatoriedade:** Sim
    - **Opções:**
      - `[ ] Residência`
      - `[ ] Buffet`
      - `[ ] Salão de Festas`
      - `[ ] Outro`

16. **CEP** `*`
    - **Tipo:** Texto com máscara (`input type="text"`, máscara: `00000-000`)
    - **Obrigatoriedade:** Sim
    - **Comportamento recomendado:** Auto-preenchimento de Logradouro, Bairro, Cidade e Estado via API (ex: ViaCEP) após digitação.

17. **Logradouro** `*`
    - **Tipo:** Texto (`input type="text"`)
    - **Placeholder:** "Nome da Rua ou Avenida" (cinza claro)
    - **Obrigatoriedade:** Sim

18. **Número** `*`
    - **Tipo:** Texto/Número (`input type="text"`)
    - **Obrigatoriedade:** Sim

19. **Complemento**
    - **Tipo:** Texto (`input type="text"`)
    - **Obrigatoriedade:** Não

20. **Bairro** `*`
    - **Tipo:** Texto (`input type="text"`)
    - **Obrigatoriedade:** Sim

21. **Cidade** `*`
    - **Tipo:** Texto (`input type="text"`)
    - **Obrigatoriedade:** Sim

22. **Estado** `*`
    - **Tipo:** Texto ou Select (`input type="text"`)
    - **Obrigatoriedade:** Sim

---

### SEÇÃO 4: Pagamento e Observações

23. **Forma de Pagamento** `*`
    - **Tipo:** Select / Dropdown customizado
    - **Obrigatoriedade:** Sim
    - **Opções disponíveis:**
      - `À vista`
      - `Em 2x no PIX (50% no ato + 50% em até 2 dias antes do evento)`
      - `Cartão de Crédito (em até 3x com acréscimo de 15%)`
      - `Outros`

24. **Descreva Outros**
    - **Tipo:** Texto (`input type="text"`)
    - **Lógica Condicional:** Este campo aparece ou torna-se obrigatório apenas se a opção `Outros` for selecionada no campo "Forma de Pagamento".

25. **Observações Contratuais**
    - **Tipo:** Área de texto ou Input longo (`textarea` ou `input type="text"`)
    - **Obrigatoriedade:** Não

---

### Rodapé / Ação Comercial

- **Botão Enviar:**
  - **Texto:** "Enviar no WhatsApp"
  - **Estilo:** Botão retangular verde, cantos levemente arredondados, com o ícone oficial do WhatsApp alinhado à esquerda do texto.
  - **Comportamento esperado:** Valida todos os campos obrigatórios. Ao clicar, gera uma mensagem formatada contendo todas as respostas do formulário e abre o link do WhatsApp (`api.whatsapp.com/send?phone=...&text=...`) direcionado para o número de atendimento da empresa.
