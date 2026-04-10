"""Application-wide constants.

Centralises role name strings so they are defined once and imported
everywhere. Using the class attributes (e.g. ``RoleName.SUPERADMIN``)
means a typo becomes an ``AttributeError`` at import time instead of a
silent authorisation bypass at runtime.
"""


class RoleName:
    SUPERADMIN = "SUPERADMIN"
    CASTING    = "CASTING"
    FIGURINO   = "FIGURINO"
    COMERCIAL  = "COMERCIAL"
    FINANCEIRO = "FINANCEIRO"
    ENSAIO     = "ENSAIO"
