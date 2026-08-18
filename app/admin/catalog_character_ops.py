"""Núcleo de negócio de Personagens filhos de um Tema do catálogo (feature 185).

Funções puras (sem `request`/`render_template`/`flash`), reusadas pelos endpoints de API em
`app/api/admin_catalogo_write.py` — fonte única, sem duplicar regra de negócio (Princípio I).
Reaproveita `CatalogValidationError` de `app.admin.catalog_ops` (mesmo contrato de erro já usado
pelo restante do catálogo) e `_slugify` de `app.catalogo.importer`.
"""

from __future__ import annotations

import os

from app import db
from app.admin.catalog_ops import CatalogValidationError
from app.catalogo.importer import _rewrite_public_url, _slugify
from app.catalogo.media import classify_video_url
from app.models import CatalogCharacter, CatalogItem, CatalogItemImage, FigurinoSheet
from app.storage import copy_file, delete_file, save_file
from app.utils import audit

_ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def unique_character_slug(tema_slug: str, name: str) -> str:
    """Gera um slug único e global para um `CatalogCharacter`, prefixado pelo slug do Tema pai."""
    base = f"{tema_slug}-{_slugify(name)}"
    slug = base
    n = 2
    while CatalogCharacter.query.filter_by(slug=slug).first():
        slug = f"{base}-{n}"
        n += 1
    return slug


def _validate_video_url(video_url: str | None) -> None:
    if video_url and classify_video_url(video_url) is None:
        raise CatalogValidationError(
            "video_url", "URL de vídeo não reconhecida (use Google Drive, MP4 ou Vimeo)."
        )


def _validate_photo_extension(photo_file) -> None:
    if not photo_file or not photo_file.filename:
        return
    ext = os.path.splitext(photo_file.filename)[1].lower()
    if ext not in _ALLOWED_PHOTO_EXTENSIONS:
        raise CatalogValidationError(
            "photo", f"Arquivo não suportado (use JPG, PNG ou WebP): {photo_file.filename}"
        )


def _require_sem_ficha_propria(item: CatalogItem) -> None:
    """Recusa montar elenco num item que já veste ficha própria (fase 1).

    A invariante é: item COM elenco é um tema, e tema não veste figurino — a ficha pertence a
    cada personagem. O outro lado da regra vive em `catalog_ops.set_item_figurino`. Sem esta
    guarda, um item avulso com ficha própria que ganhasse elenco ficaria com duas verdades
    sobre qual figurino ele usa.
    """
    if item.figurino_sheet_id:
        nome = item.figurino_sheet.character_name if item.figurino_sheet else "própria"
        raise CatalogValidationError(
            "item_id",
            f'"{item.name}" é um item avulso com ficha própria ({nome}). Remova a ficha do '
            "item antes de montar um elenco — num tema, a ficha pertence a cada personagem.",
        )


def create_character(
    item: CatalogItem,
    *,
    name: str,
    video_url: str | None,
    figurino_sheet_id: int | None,
    photo_file,
) -> CatalogCharacter:
    """Cria um novo Personagem filho do Tema `item`."""
    _require_sem_ficha_propria(item)
    clean_name = (name or "").strip()
    if not clean_name:
        raise CatalogValidationError("name", "Nome do personagem é obrigatório.")
    _validate_video_url(video_url)
    _validate_photo_extension(photo_file)

    photo_url = None
    if photo_file and photo_file.filename:
        # Mesma subpasta das fotos do Tema — a rota pública `/catalogo/midia/<arquivo>`
        # (app/catalogo/routes.py) só serve de "catalog_photos", nunca de `/uploads` geral.
        photo_url = _rewrite_public_url(save_file(photo_file, "catalog_photos"))

    next_position = len(item.characters)
    character = CatalogCharacter(
        catalog_item_id=item.id,
        name=clean_name,
        slug=unique_character_slug(item.slug, clean_name),
        photo_url=photo_url,
        video_url=(video_url or "").strip() or None,
        figurino_sheet_id=figurino_sheet_id,
        position=next_position,
    )
    db.session.add(character)
    db.session.flush()
    audit(
        "create", "CatalogCharacter", character.id, clean_name,
        f"Personagem criado em '{item.name}'",
    )
    db.session.commit()
    return character


def update_character(
    character: CatalogCharacter,
    *,
    name: str | None = None,
    video_url: str | None = None,
    figurino_sheet_id: int | None = ...,
    position: int | None = None,
    is_active: bool | None = None,
    photo_file=None,
    remove_photo: bool = False,
) -> CatalogCharacter:
    """Edita um Personagem existente. Só aplica os campos explicitamente informados.

    `figurino_sheet_id` usa `...` (Ellipsis) como sentinela de "não alterar", pois `None` é um
    valor válido (desvincular a ficha).
    """
    if name is not None:
        clean_name = name.strip()
        if not clean_name:
            raise CatalogValidationError("name", "Nome do personagem é obrigatório.")
        character.name = clean_name
    if video_url is not None:
        _validate_video_url(video_url)
        character.video_url = video_url.strip() or None
    if figurino_sheet_id is not ...:
        character.figurino_sheet_id = figurino_sheet_id
    if position is not None:
        character.position = position
    if is_active is not None:
        character.is_active = is_active

    _validate_photo_extension(photo_file)
    if remove_photo and character.photo_url:
        delete_file(character.photo_url)
        character.photo_url = None
    if photo_file and photo_file.filename:
        if character.photo_url:
            delete_file(character.photo_url)
        character.photo_url = _rewrite_public_url(save_file(photo_file, "catalog_photos"))

    audit("edit", "CatalogCharacter", character.id, character.name, "Personagem editado")
    db.session.commit()
    return character


def adopt_gallery_photo(character: CatalogCharacter, image: CatalogItemImage) -> CatalogCharacter:
    """Adota uma foto da galeria do Tema como foto do Personagem (drag-and-drop do admin).

    O arquivo é COPIADO (`storage.copy_file`), nunca referenciado: os fluxos de remoção
    (`update_character`, `delete_character`, `catalog_ops.apply_photos`) chamam `delete_file`
    sem saber de compartilhamento — em S3, uma URL compartilhada deixaria o outro lado com
    imagem quebrada. A foto continua na galeria.
    """
    if image.item_id != character.catalog_item_id:
        raise CatalogValidationError(
            "image_id", "A foto precisa pertencer à galeria do mesmo Tema do personagem."
        )

    new_url = copy_file(image.url, "catalog_photos")
    if not new_url:
        raise CatalogValidationError(
            "image_id", "Não foi possível copiar a foto da galeria. Tente novamente."
        )

    if character.photo_url:
        delete_file(character.photo_url)
    character.photo_url = _rewrite_public_url(new_url)

    audit(
        "edit", "CatalogCharacter", character.id, character.name,
        "Foto adotada da galeria do Tema",
    )
    db.session.commit()
    return character


def set_own_item(character: CatalogCharacter, item: CatalogItem | None) -> CatalogCharacter:
    """Define (ou remove, com `None`) a página própria do personagem (feature 209).

    Validações: o item não pode ser o próprio tema pai, não pode já ser página de outro
    personagem (UNIQUE) e não pode ter elenco próprio (um tema com personagens não vira
    personagem de outro tema — a hierarquia tem um nível só, de propósito).
    """
    if item is not None:
        if item.id == character.catalog_item_id:
            raise CatalogValidationError(
                "item_id", "O tema pai do personagem não pode ser a página dele mesmo."
            )
        claimed = CatalogCharacter.query.filter(
            CatalogCharacter.own_item_id == item.id, CatalogCharacter.id != character.id
        ).first()
        if claimed:
            raise CatalogValidationError(
                "item_id", f'Este item já é a página do personagem "{claimed.name}".'
            )
        if item.characters:
            raise CatalogValidationError(
                "item_id", "Um tema com elenco próprio não pode virar página de personagem."
            )
    character.own_item_id = item.id if item else None
    audit(
        "edit", "CatalogCharacter", character.id, character.name,
        f'Página própria: {item.name if item else "removida"}',
    )
    db.session.commit()
    return character


def toggle_own_page(character: CatalogCharacter, enabled: bool) -> CatalogCharacter:
    """Liga/desliga a "Página única" do personagem = `is_active` do item vinculado.

    Desligar tira o item da vitrine e da busca (o personagem segue no elenco do tema);
    ligar devolve. O vínculo `own_item_id` nunca é tocado aqui — é reversível.
    """
    if character.own_item is None:
        raise CatalogValidationError(
            "enabled", "Este personagem não tem página própria vinculada."
        )
    character.own_item.is_active = bool(enabled)
    audit(
        "edit", "CatalogItem", character.own_item.id, character.own_item.name,
        f'Página única do personagem "{character.name}" {"ativada" if enabled else "desativada"}',
    )
    db.session.commit()
    return character


def adopt_item_as_character(tema: CatalogItem, item: CatalogItem) -> CatalogCharacter:
    """Adota um item existente como personagem de um tema (feature 209, caso Coelho→Alice).

    Cria o `CatalogCharacter` no elenco do tema com nome/vídeo do item, foto COPIADA da capa
    (nunca referência — os fluxos de delete não sabem de compartilhamento) e `own_item_id`
    apontando para o item — que segue com página e busca próprias.
    """
    from app.storage import copy_file

    _require_sem_ficha_propria(tema)
    if item.id == tema.id:
        raise CatalogValidationError("item_id", "Um tema não pode ser personagem de si mesmo.")
    if item.characters:
        raise CatalogValidationError(
            "item_id", "Este item tem elenco próprio — é um tema, não um personagem."
        )
    claimed = CatalogCharacter.query.filter_by(own_item_id=item.id).first()
    if claimed:
        raise CatalogValidationError(
            "item_id", f'Este item já é a página do personagem "{claimed.name}".'
        )

    photo_url = None
    cover = item.cover_image
    if cover:
        copied = copy_file(cover.url, "catalog_photos")
        photo_url = _rewrite_public_url(copied) if copied else None

    character = CatalogCharacter(
        catalog_item_id=tema.id,
        name=item.name,
        slug=unique_character_slug(tema.slug, item.name),
        photo_url=photo_url,
        video_url=item.video_url,
        own_item_id=item.id,
        position=len(tema.characters),
    )
    db.session.add(character)
    db.session.flush()
    audit(
        "create", "CatalogCharacter", character.id, character.name,
        f'Item "{item.name}" adotado como personagem de "{tema.name}"',
    )
    db.session.commit()
    return character


def reuse_character(tema: CatalogItem, sheet: FigurinoSheet) -> CatalogCharacter:
    """Põe no elenco de `tema` um personagem que já existe no acervo (feature 235).

    **A identidade de um personagem é a ficha de figurino** — o figurino físico que a Manto tem.
    Duas linhas de `CatalogCharacter` apontando para a mesma ficha são o mesmo personagem em dois
    temas (o caso "Gatuno e Pandy também estão na Gabby Humanizada"). Não existe tabela de
    identidade separada de propósito: a ficha já é a âncora do resto do ERP (elenco do evento,
    alerta de "sem ficha", manutenção, produção), e um terceiro cadastro seria uma segunda
    verdade sobre quem é o personagem.

    Cada aparição continua sendo uma linha própria: nome, foto, vídeo e ordem podem diferir de
    tema para tema, e mexer numa não mexe na outra. O que amarra as duas é a ficha.

    A foto é COPIADA (nunca referenciada) da aparição mais recente ou da própria ficha — os
    fluxos de remoção chamam `delete_file` sem saber de compartilhamento.
    """
    _require_sem_ficha_propria(tema)
    ja_no_tema = CatalogCharacter.query.filter_by(
        catalog_item_id=tema.id, figurino_sheet_id=sheet.id
    ).first()
    if ja_no_tema:
        raise CatalogValidationError(
            "figurino_sheet_id",
            f'"{ja_no_tema.name}" já está no elenco deste tema.',
        )

    # Aparição mais recente: é dela que vêm nome/foto/vídeo já ajustados para o catálogo — a
    # ficha costuma ter o nome do figurino ("Gabby Boneco"), não o nome de cena.
    fonte = (
        CatalogCharacter.query.filter_by(figurino_sheet_id=sheet.id)
        .order_by(CatalogCharacter.id.desc())
        .first()
    )
    nome = (fonte.name if fonte else sheet.character_name).strip()
    origem_foto = fonte.photo_url if fonte and fonte.photo_url else sheet.photo_url
    photo_url = None
    if origem_foto:
        copiada = copy_file(origem_foto, "catalog_photos")
        photo_url = _rewrite_public_url(copiada) if copiada else None

    character = CatalogCharacter(
        catalog_item_id=tema.id,
        name=nome,
        slug=unique_character_slug(tema.slug, nome),
        photo_url=photo_url,
        video_url=fonte.video_url if fonte else None,
        figurino_sheet_id=sheet.id,
        position=len(tema.characters),
    )
    db.session.add(character)
    db.session.flush()
    audit(
        "create", "CatalogCharacter", character.id, nome,
        f'Personagem "{nome}" reaproveitado em "{tema.name}"',
    )
    db.session.commit()
    return character


def list_catalog_characters() -> dict:
    """Personagens do catálogo agrupados por identidade, com em quantos temas cada um aparece.

    Uma linha por personagem, não por aparição: a chave é a ficha (`ficha-<id>`) e, para quem
    ainda não tem ficha, o próprio registro (`char-<id>`) — que aparece marcado como pendência,
    porque sem ficha não dá para dizer que dois personagens de temas diferentes são o mesmo.

    Não lista as 616 fichas do acervo: isto é o elenco **do catálogo**. O caminho para trazer uma
    ficha ainda não usada é `reuse_character`, e o total de fichas fora do catálogo vai em
    `totais` como medida de progresso.

    Tema e aparição são coisas diferentes e a estrutura reflete isso: "Astronauta 1" e
    "Astronauta 2" são duas aparições da MESMA ficha dentro de um tema só (dois performers do
    mesmo figurino no mesmo show) — o que é exatamente onde a quantidade de figurinos iguais
    passa a importar.
    """
    from app.figurino.producao_ops import alertas_por_ficha

    characters = CatalogCharacter.query.all()
    temas = {t.id: t for t in CatalogItem.query.all()}
    sheets = {s.id: s for s in FigurinoSheet.query.all()}
    alertas = alertas_por_ficha()

    grupos: dict[str, dict] = {}
    for c in sorted(characters, key=lambda c: (c.catalog_item_id, c.position)):
        sheet = sheets.get(c.figurino_sheet_id) if c.figurino_sheet_id else None
        key = f"ficha-{sheet.id}" if sheet else f"char-{c.id}"
        grupo = grupos.setdefault(
            key,
            {
                "key": key,
                "name": c.name,
                "photo_url": c.photo_url,
                "figurino_sheet_id": sheet.id if sheet else None,
                "figurino_sheet_name": sheet.character_name if sheet else None,
                "quantidade_figurinos": sheet.quantity if sheet else None,
                "manutencao": alertas.get(sheet.id) if sheet else None,
                "temas": [],
                "_por_tema": {},
            },
        )
        if not grupo["photo_url"]:
            grupo["photo_url"] = c.photo_url
        tema = temas.get(c.catalog_item_id)
        entrada = grupo["_por_tema"].get(c.catalog_item_id)
        if entrada is None:
            entrada = {
                "tema_id": c.catalog_item_id,
                "tema_name": tema.name if tema else "—",
                "is_avulso": False,
                "aparicoes": [],
            }
            grupo["_por_tema"][c.catalog_item_id] = entrada
            grupo["temas"].append(entrada)
        entrada["aparicoes"].append(
            {"character_id": c.id, "character_name": c.name, "is_active": c.is_active}
        )

    # Itens AVULSOS com ficha própria (fase 1) entram como aparição também: sem isto, os 12
    # personagens que a migration tirou de "elenco de si mesmo" sumiriam desta tela — ela é a
    # resposta de "onde este personagem aparece", e um avulso É um lugar onde ele aparece.
    for item in temas.values():
        if item.characters or not item.figurino_sheet_id:
            continue
        sheet = sheets.get(item.figurino_sheet_id)
        if sheet is None:
            continue
        key = f"ficha-{sheet.id}"
        grupo = grupos.setdefault(
            key,
            {
                "key": key,
                "name": item.name,
                "photo_url": item.cover_image.url if item.cover_image else None,
                "figurino_sheet_id": sheet.id,
                "figurino_sheet_name": sheet.character_name,
                "quantidade_figurinos": sheet.quantity,
                "manutencao": alertas.get(sheet.id),
                "temas": [],
                "_por_tema": {},
            },
        )
        if not grupo["photo_url"] and item.cover_image:
            grupo["photo_url"] = item.cover_image.url
        entrada = {
            "tema_id": item.id,
            "tema_name": item.name,
            # A tela distingue "está no elenco do tema X" de "é a página avulsa X".
            "is_avulso": True,
            "aparicoes": [
                {"character_id": None, "character_name": item.name, "is_active": item.is_active}
            ],
        }
        grupo["_por_tema"][item.id] = entrada
        grupo["temas"].append(entrada)

    personagens = sorted(grupos.values(), key=lambda g: g["name"].lower())
    for grupo in personagens:
        grupo.pop("_por_tema")
        grupo["total_aparicoes"] = sum(len(t["aparicoes"]) for t in grupo["temas"])

    com_ficha = [g for g in personagens if g["figurino_sheet_id"]]
    return {
        "personagens": personagens,
        "totais": {
            "personagens": len(personagens),
            "aparicoes": sum(g["total_aparicoes"] for g in personagens),
            "com_ficha": len(com_ficha),
            "sem_ficha": len(personagens) - len(com_ficha),
            "em_varios_temas": sum(1 for g in personagens if len(g["temas"]) > 1),
            # Quanto do acervo de figurino ainda não virou personagem de nenhum tema — a medida
            # de progresso que a tela existe para mostrar.
            "fichas_fora_do_catalogo": len(sheets) - len({g["figurino_sheet_id"] for g in com_ficha}),
        },
    }


def delete_character(character: CatalogCharacter) -> None:
    """Exclui definitivamente um Personagem, removendo sua foto do storage."""
    name = character.name
    character_id = character.id
    if character.photo_url:
        delete_file(character.photo_url)
    db.session.delete(character)
    audit("delete", "CatalogCharacter", character_id, name, "Personagem excluído")
    db.session.commit()


def move_characters(character_ids: list[int], target_item: CatalogItem) -> int:
    """Realoca em massa uma lista de Personagens para serem filhos de `target_item` (feature 186).

    Reatribui `catalog_item_id` numa única transação — ou tudo aplica, ou nada aplica. A posição
    de cada Personagem movido é recalculada para o final da lista de filhos de `target_item`, na
    ordem em que os `character_ids` foram informados.

    Args:
        character_ids: ids dos `CatalogCharacter` a mover.
        target_item: Tema de destino (já deve estar carregado/validado pelo chamador).

    Returns:
        Quantidade de Personagens efetivamente movidos.

    Raises:
        CatalogValidationError: `character_ids` vazio ou contém um id inexistente.
    """
    _require_sem_ficha_propria(target_item)
    if not character_ids:
        raise CatalogValidationError("character_ids", "Selecione ao menos um personagem.")

    characters = CatalogCharacter.query.filter(CatalogCharacter.id.in_(character_ids)).all()
    if len(characters) != len(set(character_ids)):
        raise CatalogValidationError("character_ids", "Um ou mais personagens não foram encontrados.")

    next_position = len(target_item.characters)
    by_id = {c.id: c for c in characters}
    for offset, char_id in enumerate(character_ids):
        character = by_id[char_id]
        character.catalog_item_id = target_item.id
        character.position = next_position + offset
        audit(
            "edit", "CatalogCharacter", character.id, character.name,
            f"Personagem realocado para '{target_item.name}'",
        )
    db.session.commit()
    return len(characters)
