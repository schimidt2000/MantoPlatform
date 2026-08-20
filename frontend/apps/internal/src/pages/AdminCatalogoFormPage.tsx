import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { ApiRequestError } from "@manto/api-client";
import { Button, Card, CardContent, CardHeader, CardTitle, Skeleton } from "@manto/ui";
import {
  useAdminCatalogo,
  useAdminCatalogoItem,
  useAdoptGalleryPhoto,
  useCatalogTagSuggestions,
  useCreateCatalogItem,
  useCreateCategory,
  useUpdateCatalogItem,
} from "../lib/adminCatalogo";
import { ChipInput } from "../components/ChipInput";
import { AdminCatalogCharacterPanel } from "../components/AdminCatalogCharacterPanel";
import {
  CatalogPhotoManager,
  EMPTY_PHOTOS_VALUE,
  type CatalogPhotosValue,
  type NewPhotoSlot,
} from "../components/CatalogPhotoManager";
import { RichTextEditor } from "../components/RichTextEditor";

const LABEL = "mb-1 block text-xs font-medium text-muted";
const INPUT = "h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

export function AdminCatalogoFormPage() {
  const params = useParams<{ id?: string }>();
  const id = params.id ? Number(params.id) : undefined;
  const isEdit = id !== undefined;
  const navigate = useNavigate();
  const location = useLocation();
  // Chegou aqui direto do "Criar produto" — mostra o aviso apontando o painel de elenco/fichas.
  // Derivado do location a CADA render (não num useState inicial): a rota /novo e esta usam o
  // mesmo elemento no Router, então o componente não remonta na navegação pós-criação.
  const [avisoDispensado, setAvisoDispensado] = useState(false);
  useEffect(() => setAvisoDispensado(false), [location.key]);
  const recemCriado =
    !avisoDispensado && Boolean((location.state as { recemCriado?: boolean } | null)?.recemCriado);

  const categoriesQuery = useAdminCatalogo({});
  const itemQuery = useAdminCatalogoItem(id);
  const tagSuggestionsQuery = useCatalogTagSuggestions();
  const createItem = useCreateCatalogItem();
  const updateItem = useUpdateCatalogItem(id ?? 0);
  const createCategory = useCreateCategory();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [tagsList, setTagsList] = useState<string[]>([]);
  const [videoUrl, setVideoUrl] = useState("");
  const [categoryIds, setCategoryIds] = useState<number[]>([]);
  const [newCategoryName, setNewCategoryName] = useState("");
  const [photosValue, setPhotosValue] = useState<CatalogPhotosValue>(EMPTY_PHOTOS_VALUE);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  // Adoção de foto por arraste (foto da galeria → personagem). Mora aqui, e não no painel,
  // porque quem detecta o alvo é o card arrastado da grade de fotos: o painel só recebe qual
  // personagem está sob o ponteiro para desenhar o realce.
  const adoptPhoto = useAdoptGalleryPhoto(id ?? 0);
  const [photoDropTargetId, setPhotoDropTargetId] = useState<number | null>(null);
  const [photoDropError, setPhotoDropError] = useState<string | null>(null);

  // Hidrata o formulário UMA vez por produto. Sem o guard, qualquer mutação do painel de
  // personagens (adotar foto por drag, criar/excluir/reordenar) invalida
  // ["admin-catalogo", id], o refetch troca `itemQuery.data` e este efeito RESETAVA nome,
  // descrição, fotos e tags — descartando tudo que o admin tinha editado sem salvar.
  const hydratedIdRef = useRef<number | null>(null);
  useEffect(() => {
    if (!itemQuery.data || hydratedIdRef.current === itemQuery.data.id) return;
    hydratedIdRef.current = itemQuery.data.id;
    setName(itemQuery.data.name);
    setDescription(itemQuery.data.description);
    setTagsList(itemQuery.data.tags);
    setVideoUrl(itemQuery.data.video_url ?? "");
    setCategoryIds(itemQuery.data.category_ids);
    setPhotosValue({
      photos: itemQuery.data.images.map((img) => ({
        kind: "existing" as const,
        key: `img-${img.id}`,
        id: img.id,
        url: img.url,
      })),
      removed: [],
    });
  }, [itemQuery.data]);

  const toggleCategory = (catId: number) =>
    setCategoryIds((prev) =>
      prev.includes(catId) ? prev.filter((c) => c !== catId) : [...prev, catId],
    );

  /**
   * Soltar uma foto já salva sobre um personagem faz ele adotá-la como foto própria.
   *
   * O `confirm` sai do handler por `setTimeout`: ele roda dentro do `pointerup` que encerra o
   * arraste, e um diálogo síncrono ali congelaria o card no meio da animação de volta.
   */
  const handleDropOnCharacter = (characterId: number, imageId: number) => {
    const character = itemQuery.data?.characters.find((c) => c.id === characterId);
    if (!character) return;
    setTimeout(() => {
      if (
        character.photo_url &&
        !window.confirm(`Substituir a foto atual de "${character.name}" pela foto arrastada?`)
      ) {
        return;
      }
      setPhotoDropError(null);
      adoptPhoto.mutate(
        { characterId, imageId },
        {
          onError: (err) => {
            if (err instanceof ApiRequestError) setPhotoDropError(err.message);
          },
        },
      );
    }, 0);
  };

  const handleSubmit = () => {
    setFieldErrors({});
    // A ordem vai como tokens: id da foto já salva, ou `new:<i>` apontando para o i-ésimo
    // arquivo de `newPhotos` — é o que permite uma foto nova cair no meio das antigas.
    const newSlots = photosValue.photos.filter((p): p is NewPhotoSlot => p.kind === "new");
    const input = {
      name,
      description,
      tags: tagsList.join(", "),
      videoUrl,
      categoryIds,
      newPhotos: newSlots.map((slot) => slot.file),
      removePhotoIds: photosValue.removed.map((photo) => photo.id),
      photoOrder: photosValue.photos.map((slot) =>
        slot.kind === "existing" ? String(slot.id) : `new:${newSlots.indexOf(slot)}`,
      ),
    };
    const mutation = isEdit ? updateItem : createItem;
    mutation.mutate(input, {
      onSuccess: (saved) => {
        if (isEdit) {
          navigate("/admin/catalogo");
          return;
        }
        // Criação aterrissa na EDIÇÃO do produto recém-criado (feature 254): é onde vivem o
        // elenco e o vínculo com ficha de figurino — antes era preciso saber voltar à lista e
        // reabrir o produto para conseguir vincular qualquer coisa.
        navigate(`/admin/catalogo/${saved.id}/editar`, { state: { recemCriado: true } });
      },
      onError: (err) => {
        if (err instanceof ApiRequestError && err.fields) setFieldErrors(err.fields);
      },
    });
  };

  const saving = createItem.isPending || updateItem.isPending;
  const saveError = createItem.isError || updateItem.isError;

  if (isEdit && itemQuery.isLoading) {
    return (
      <div className="mx-auto max-w-5xl space-y-4 p-4 sm:p-6">
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-4 sm:p-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/admin/catalogo">‹ Catálogo</Link>
      </Button>

      <header>
        <h1 className="text-2xl font-semibold text-ink">
          {isEdit ? "Editar produto" : "Novo produto"}
        </h1>
      </header>

      {recemCriado && (
        <div
          className="flex items-start justify-between gap-3 rounded-md border border-accent bg-accent-soft px-4 py-3 text-sm text-accent-dark"
          role="status"
        >
          <p>
            Produto criado. Agora monte o elenco e vincule as fichas de figurino no painel{" "}
            <strong>Personagens</strong>, mais abaixo — ou volte ao catálogo se este produto não
            tem elenco.
          </p>
          <button
            type="button"
            className="shrink-0 text-xs underline"
            onClick={() => {
              setAvisoDispensado(true);
              navigate(location.pathname, { replace: true });
            }}
          >
            Entendi
          </button>
        </div>
      )}

      {/* Dados leva o dobro da largura (tem editor de texto rico); categorias é só uma lista de
          chips, cabe na coluna estreita ao lado em vez de virar mais um bloco na pilha. */}
      <div className="grid items-start gap-4 [&>*]:min-w-0 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle>Dados</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <label className={LABEL} htmlFor="catalog-item-name">
              Nome
            </label>
            <input
              id="catalog-item-name"
              className={INPUT}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            {fieldErrors.name && <p className="mt-1 text-xs text-red">{fieldErrors.name}</p>}
          </div>
          <div>
            <label className={LABEL}>Descrição</label>
            {/* Rich-text natural (negrito/itálico/parágrafo); o valor persistido continua
                HTML em `short_description_html` — o backend sanitiza (nh3). */}
            <RichTextEditor
              value={description}
              onChange={setDescription}
              ariaLabel="Descrição do produto"
            />
          </div>
          <div>
            <label className={LABEL}>Tags</label>
            <ChipInput
              value={tagsList}
              onChange={setTagsList}
              suggestions={tagSuggestionsQuery.data?.tags ?? []}
              placeholder="Digite e pressione Enter ou vírgula…"
              ariaLabel="Tags"
            />
          </div>
          <div>
            <label className={LABEL}>URL de vídeo (Drive/MP4/Vimeo)</label>
            <input
              className={INPUT}
              value={videoUrl}
              onChange={(e) => setVideoUrl(e.target.value)}
              placeholder="https://..."
            />
            {fieldErrors.video_url && (
              <p className="mt-1 text-xs text-red">{fieldErrors.video_url}</p>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Categorias</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {categoriesQuery.data && (
            <div className="flex flex-wrap gap-1.5">
              {categoriesQuery.data.categories.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  className={`rounded-md border px-2 py-1 text-xs ${categoryIds.includes(c.id) ? "border-accent bg-accent-soft text-accent-dark" : "border-line text-ink"}`}
                  onClick={() => toggleCategory(c.id)}
                >
                  {c.name}
                </button>
              ))}
            </div>
          )}
          <div className="flex gap-2">
            <input
              className={INPUT}
              placeholder="Nova categoria…"
              value={newCategoryName}
              onChange={(e) => setNewCategoryName(e.target.value)}
            />
            <Button
              variant="outline"
              size="sm"
              loading={createCategory.isPending}
              onClick={() =>
                createCategory.mutate(newCategoryName, {
                  onSuccess: (cat) => {
                    setCategoryIds((prev) => [...prev, cat.id]);
                    setNewCategoryName("");
                    categoriesQuery.refetch();
                  },
                })
              }
            >
              Adicionar
            </Button>
          </div>
        </CardContent>
      </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Fotos</CardTitle>
        </CardHeader>
        <CardContent>
          <CatalogPhotoManager
            value={photosValue}
            onChange={setPhotosValue}
            savedOrder={itemQuery.data?.images.map((img) => img.id)}
            error={fieldErrors.photos}
            onDropOnCharacter={isEdit ? handleDropOnCharacter : undefined}
            onCharacterHoverChange={setPhotoDropTargetId}
          />
        </CardContent>
      </Card>

      {isEdit && id !== undefined && (
        <AdminCatalogCharacterPanel
          itemId={id}
          characters={itemQuery.data?.characters ?? []}
          photoDropTargetId={photoDropTargetId}
          adoptingCharacterId={
            adoptPhoto.isPending ? (adoptPhoto.variables?.characterId ?? null) : null
          }
          photoDropError={photoDropError}
          itemFigurinoSheetId={itemQuery.data?.figurino_sheet_id ?? null}
        />
      )}

      <Button loading={saving} onClick={handleSubmit}>
        {isEdit ? "Salvar alterações" : "Criar produto"}
      </Button>
      {saveError && !Object.keys(fieldErrors).length && (
        <p className="text-sm text-red">Não foi possível salvar o produto.</p>
      )}
    </div>
  );
}
