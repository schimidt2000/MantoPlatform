"""Conversas — WhatsApp (e, na Fase 2, Instagram Direct) dentro da Plataforma (feature 325).

Núcleo puro: nenhum módulo daqui importa ``flask.request``. A configuração chega por
``configuracao.cfg_whatsapp()`` e o HTTP da Meta mora em ``app/integracoes/whatsapp_client.py``.
Plano do CRM próprio: ``docs/PLANO_CRM_PROPRIO.md``.
"""
