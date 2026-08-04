"""Clientes de serviços externos (feature 205).

Cada módulo aqui isola o contrato de UM fornecedor. A regra é que o resto do sistema nunca precise
saber como o fornecedor fala: unidades, formatos e modos de erro são traduzidos na fronteira.

Nada aqui importa Flask — são funções puras de integração, testáveis sem HTTP.
"""
