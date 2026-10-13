"""Cria a campanha "Uma chamada com o Papai Noel" em RASCUNHO (feature 304).

O botão "Nova campanha" do painel não cria nada (fica no esqueleto — `docs/05`), então a primeira
campanha da loja nasce por aqui, com tudo o que é texto já escrito: apresentação, termos, WhatsApp
da empresa, capa (o pôster vertical das artes de marketing, versionado ao lado deste arquivo) e o
endereço curto `/papai-noel` — o que vai no story fica `alo.mantoproducoes.com.br/papai-noel`.

O que é DECISÃO DO TIME fica de fora de propósito: preços (nascem R$ 0,00), capacidade de vídeos
(0), horários e peças 3D. A publicação recusa preço zero (304), então a campanha não vai ao ar de
graça por esquecimento. O FAQ nasce vazio: a página da campanha mostra o FAQ da loja
(`frontend/apps/public/src/lib/lojaTema.ts`), uma fonte só.

Idempotente: se a campanha já existe (pelo endereço `papai-noel`), não cria outra nem mexe nela.

Uso (local):
    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONPATH = (Get-Location).Path
    .venv\\Scripts\\python.exe specs\\304-loja-natal-papai-noel\\criar_campanha_noel.py            # só mostra
    .venv\\Scripts\\python.exe specs\\304-loja-natal-papai-noel\\criar_campanha_noel.py --execute  # grava

Produção (Shell do `manto-backend` no Render, depois do deploy da 304):
    MANTO_SEM_THREADS=1 python specs/304-loja-natal-papai-noel/criar_campanha_noel.py --execute
"""

import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if "sqlite" in os.environ.get("DATABASE_URL", "sqlite"):
    sys.exit("ERRO: DATABASE_URL não aponta para um Postgres — nada foi feito.")

from werkzeug.datastructures import FileStorage  # noqa: E402

from app import create_app, db  # noqa: E402
from app.api.virtuais_write import CAMPAIGN_COVER_SUBFOLDER  # noqa: E402
from app.marketing import virtuais_ops as ops  # noqa: E402
from app.models import CatalogCharacter, VirtualCampaign  # noqa: E402
from app.storage import save_file  # noqa: E402

SLUG = "papai-noel"
PERSONAGEM = "Papai Noel"
TITULO = "Uma chamada com o Papai Noel"
CAPA = Path(__file__).with_name("capa_papai_noel.jpg")
#: O mesmo WhatsApp dos formulários públicos (`app/formularios/formularios_ops.py`).
WHATSAPP = "5511970570577"

APRESENTACAO = (
    "Neste Natal, o Papai Noel tira uns minutinhos da oficina para falar com a sua criança.\n\n"
    "Na chamada ao vivo, ele liga por vídeo no horário que você escolher, chama pelo nome, "
    "pergunta como foi o ano — e a criança pode mostrar a cartinha para ele ler na hora.\n\n"
    "Prefere sem hora marcada? O Papai Noel grava um vídeo só para a sua criança, com o recado "
    "que você pedir."
)

# Rascunho para o time revisar antes de publicar: não promete prazo nem número que o sistema não
# controla. O que é mecânica do sistema (a chamada tem 10 minutos e o horário seguinte é de outra
# família) está dito; a remarcação fica como tentativa, porque depende da agenda.
TERMOS = (
    "A chamada dura 10 minutos e começa no horário marcado. Se vocês entrarem atrasados, ela "
    "termina no mesmo horário: logo depois o Papai Noel fala com outra criança. "
    "Não vai conseguir no dia? Avise pelo WhatsApp o quanto antes — tentamos remarcar dentro da "
    "agenda disponível. O vídeo gravado é entregue na página do pedido, dentro do prazo indicado "
    "na reserva."
)


def _salvar_capa() -> str:
    """Grava a capa pelo mesmo `save_file` do upload do painel e devolve a URL PÚBLICA.

    Mesma reescrita de `app/api/virtuais_write.py:_cover_url`: `/uploads/*` exige login de staff,
    e a família abriria a landing sem capa.
    """
    with CAPA.open("rb") as arquivo:
        salvo = save_file(
            FileStorage(stream=arquivo, filename=CAPA.name, content_type="image/jpeg"),
            CAMPAIGN_COVER_SUBFOLDER,
        )
    if salvo.startswith(f"/uploads/{CAMPAIGN_COVER_SUBFOLDER}/"):
        return f"/catalogo/midia/campanhas/{salvo.rsplit('/', 1)[-1]}"
    return salvo


def main(executar: bool) -> int:
    app = create_app()
    with app.app_context():
        existente = VirtualCampaign.query.filter_by(slug=SLUG).first()
        if existente is not None:
            print(
                f"Já existe: campanha {existente.id} '{existente.title}' "
                f"({existente.status}). Nada feito."
            )
            return 0

        personagens = CatalogCharacter.query.filter(
            db.func.lower(CatalogCharacter.name) == PERSONAGEM.lower(),
            CatalogCharacter.is_active.is_(True),
        ).all()
        if len(personagens) != 1:
            ids = ", ".join(f"{p.id}" for p in personagens) or "nenhum"
            print(f"ERRO: esperava 1 personagem ativo '{PERSONAGEM}' no catálogo, achei: {ids}.")
            return 1
        personagem = personagens[0]

        if not CAPA.exists():
            print(f"ERRO: capa não encontrada em {CAPA}.")
            return 1

        print(f"Personagem: {personagem.id} '{personagem.name}'")
        print(f"Título: {TITULO}  ·  endereço: /v/{SLUG}")
        print(f"Capa: {CAPA.name} ({CAPA.stat().st_size // 1024} KB)")
        if not executar:
            print("Simulação — rode com --execute para gravar.")
            return 0

        campanha = ops.criar_campanha(
            catalog_character_id=personagem.id,
            title=TITULO,
            price_live=0,
            price_recorded=0,
            price_gift=0,
            recorded_capacity=0,
            recorded_delivery_days=7,
            intro_html=APRESENTACAO,
            tolerance_terms=TERMOS,
            faq=[],
            cover_url=_salvar_capa(),
            whatsapp_phone=WHATSAPP,
        )
        # O slug nasce do título ("uma-chamada-com-o-papai-noel") e a tela não edita slug. O curto
        # é o que cabe num story; `existente` acima garante que ele está livre.
        campanha.slug = SLUG
        db.session.commit()
        print(f"Criada: campanha {campanha.id} em rascunho → /v/{campanha.slug}")
        print("Falta o time: preços, capacidade de vídeos, horários e (se quiser) peças 3D.")
        return 0


if __name__ == "__main__":
    sys.exit(main("--execute" in sys.argv))
