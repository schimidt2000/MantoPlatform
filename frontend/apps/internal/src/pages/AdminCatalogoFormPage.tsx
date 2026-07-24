import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiRequestError, assetUrl } from "@manto/api-client";
import { Button, Card, CardContent, CardHeader, CardTitle, Skeleton } from "@manto/ui";
import {
  useAdminCatalogo,
  useAdminCatalogoItem,
  useCatalogTagSuggestions,
  useCreateCatalogItem,
  useCreateCategory,
  useUpdateCatalogItem,
  type CatalogImage,
} from "../lib/adminCatalogo";
import { ChipInput } from "../components/ChipInput";
import { AdminCatalogCharacterPanel } from "../components/AdminCatalogCharacterPanel";

const LABEL = "mb-1 block text-xs font-medium text-muted";
const INPUT = "h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

interface ExistingPhoto extends CatalogImage {
  markedForRemoval: boolean;
}

export function AdminCatalogoFormPage() {
  const params = useParams<{ id?: string }>();
  const id = params.id ? Number(params.id) : undefined;
  const isEdit = id !== undefined;
  const navigate = useNavigate();

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
  const [existingPhotos, setExistingPhotos] = useState<ExistingPhoto[]>([]);
  const [newPhotos, setNewPhotos] = useState<File[]>([]);
  const [coverPhotoId, setCoverPhotoId] = useState<number | undefined>(undefined);
  const [newPhotoCoverIndex, setNewPhotoCoverIndex] = useState<number | undefined>(undefined);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (itemQuery.data) {
      setName(itemQuery.data.name);
      setDescription(itemQuery.data.description);
      setTagsList(itemQuery.data.tags);
      setVideoUrl(itemQuery.data.video_url ?? "");
      setCategoryIds(itemQuery.data.category_ids);
      setExistingPhotos(
        itemQuery.data.images.map((img) => ({ ...img, markedForRemoval: false })),
      );
    }
  }, [itemQuery.data]);

  const toggleCategory = (catId: number) =>
    setCategoryIds((prev) =>
      prev.includes(catId) ? prev.filter((c) => c !== catId) : [...prev, catId],
    );

  const visibleExisting = existingPhotos.filter((p) => !p.markedForRemoval);

  const moveExistingPhoto = (index: number, direction: -1 | 1) => {
    setExistingPhotos((prev) => {
      const visible = prev.filter((p) => !p.markedForRemoval);
      const target = index + direction;
      if (target < 0 || target >= visible.length) return prev;
      const a = visible[index];
      const b = visible[target];
      const swapped = prev.map((p) => {
        if (p.id === a.id) return { ...p, position: b.position };
        if (p.id === b.id) return { ...p, position: a.position };
        return p;
      });
      return swapped;
    });
  };

  const removeExistingPhoto = (photoId: number) =>
    setExistingPhotos((prev) =>
      prev.map((p) => (p.id === photoId ? { ...p, markedForRemoval: true } : p)),
    );

  const handleSubmit = () => {
    setFieldErrors({});
    const orderedExisting = [...visibleExisting].sort((a, b) => a.position - b.position);
    const input = {
      name,
      description,
      tags: tagsList.join(", "),
      videoUrl,
      categoryIds,
      newPhotos,
      removePhotoIds: existingPhotos.filter((p) => p.markedForRemoval).map((p) => p.id),
      photoOrder: orderedExisting.map((p) => p.id),
      coverPhotoId,
      newPhotoCoverIndex,
    };
    const mutation = isEdit ? updateItem : createItem;
    mutation.mutate(input, {
      onSuccess: () => navigate("/admin/catalogo"),
      onError: (err) => {
        if (err instanceof ApiRequestError && err.fields) setFieldErrors(err.fields);
      },
    });
  };

  const saving = createItem.isPending || updateItem.isPending;
  const saveError = createItem.isError || updateItem.isError;

  if (isEdit && itemQuery.isLoading) {
    return (
      <div className="mx-auto max-w-2xl space-y-4 p-4 sm:p-6">
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4 p-4 sm:p-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/admin/catalogo">‹ Catálogo</Link>
      </Button>

      <header>
        <h1 className="text-2xl font-semibold text-ink">
          {isEdit ? "Editar produto" : "Novo produto"}
        </h1>
      </header>

      <Card>
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
            <textarea
              className="min-h-20 w-full rounded-md border border-line bg-panel p-2 text-sm text-ink"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
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

      <Card>
        <CardHeader>
          <CardTitle>Fotos</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {fieldErrors.photos && <p className="text-xs text-red">{fieldErrors.photos}</p>}
          {visibleExisting.length > 0 && (
            <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
              {[...visibleExisting]
                .sort((a, b) => a.position - b.position)
                .map((photo, idx) => (
                  <div key={photo.id} className="space-y-1">
                    <div className="relative aspect-square overflow-hidden rounded-md bg-surface-2">
                      <img
                        src={assetUrl(photo.url)}
                        alt=""
                        className="h-full w-full object-cover"
                      />
                    </div>
                    <div className="flex items-center justify-between gap-1 text-xs">
                      <label className="flex items-center gap-1 text-ink">
                        <input
                          type="radio"
                          name="cover"
                          checked={coverPhotoId === photo.id}
                          onChange={() => {
                            setCoverPhotoId(photo.id);
                            setNewPhotoCoverIndex(undefined);
                          }}
                        />
                        capa
                      </label>
                      <div className="flex gap-1">
                        <button
                          type="button"
                          className="text-muted disabled:opacity-30"
                          disabled={idx === 0}
                          onClick={() => moveExistingPhoto(idx, -1)}
                        >
                          ‹
                        </button>
                        <button
                          type="button"
                          className="text-muted disabled:opacity-30"
                          disabled={idx === visibleExisting.length - 1}
                          onClick={() => moveExistingPhoto(idx, 1)}
                        >
                          ›
                        </button>
                        <button
                          type="button"
                          className="text-red"
                          onClick={() => removeExistingPhoto(photo.id)}
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          )}

          <div>
            <label className={LABEL}>Adicionar fotos novas</label>
            <input
              type="file"
              multiple
              accept="image/jpeg,image/png,image/webp"
              className="text-sm text-ink"
              onChange={(e) => setNewPhotos(Array.from(e.target.files ?? []))}
            />
          </div>

          {newPhotos.length > 0 && (
            <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
              {newPhotos.map((file, idx) => (
                <div key={idx} className="space-y-1">
                  <div className="aspect-square overflow-hidden rounded-md bg-surface-2">
                    <img
                      src={URL.createObjectURL(file)}
                      alt=""
                      className="h-full w-full object-cover"
                    />
                  </div>
                  <label className="flex items-center gap-1 text-xs text-ink">
                    <input
                      type="radio"
                      name="cover"
                      checked={newPhotoCoverIndex === idx}
                      onChange={() => {
                        setNewPhotoCoverIndex(idx);
                        setCoverPhotoId(undefined);
                      }}
                    />
                    capa (nova)
                  </label>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {isEdit && id !== undefined && (
        <AdminCatalogCharacterPanel itemId={id} characters={itemQuery.data?.characters ?? []} />
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
