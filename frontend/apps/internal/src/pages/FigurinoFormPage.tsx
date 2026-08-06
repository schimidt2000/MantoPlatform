import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { Button, Card, CardContent, PageHeader } from "@manto/ui";
import { assetUrl } from "@manto/api-client";
import {
  useCreateFigurinoSheet,
  useDeleteFigurinoSheet,
  useEditFigurinoSheet,
  useFigurinoSheets,
  useRemoveFigurinoPhoto,
  useRotateFigurinoPhoto,
  useUploadFigurinoPhoto,
  type FigurinoPiece,
  type FigurinoSheetItem,
} from "../lib/figurino";
import { useCatalogElencoBusca } from "../lib/catalogoElenco";
import { useLinkCharacterFigurino } from "../lib/adminCatalogo";
import { CharacterAutocomplete } from "../components/CharacterAutocomplete";

/**
 * Vínculo bidirecional Ficha↔Personagem a partir da tela da Ficha (feature 186, US2) — escreve
 * na mesma `CatalogCharacter.figurino_sheet_id` que o lado do catálogo já usa (research.md §4),
 * sem coluna nova.
 */
function FigurinoCatalogLinkField({ sheetId }: { sheetId: number }) {
  const elencoBusca = useCatalogElencoBusca();
  const link = useLinkCharacterFigurino();

  const linkedCharacter = elencoBusca.data?.temas
    .flatMap((tema) => tema.characters.map((c) => ({ ...c, temaName: tema.name })))
    .find((c) => c.figurino_sheet_id === sheetId);

  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-muted">
        Vincular a um Personagem do Catálogo
      </label>
      {linkedCharacter ? (
        <div className="flex items-center justify-between gap-2 rounded-md border border-line bg-panel px-3 py-2 text-sm">
          <span className="text-ink">
            {linkedCharacter.name}{" "}
            <span className="text-muted">— {linkedCharacter.temaName}</span>
          </span>
          <Button
            variant="ghost"
            size="sm"
            loading={link.isPending}
            onClick={() => link.mutate({ characterId: linkedCharacter.id, figurinoSheetId: null })}
          >
            Desvincular
          </Button>
        </div>
      ) : (
        <CharacterAutocomplete
          temas={elencoBusca.data?.temas ?? []}
          placeholder="Buscar personagem do catálogo…"
          onSelect={(selection) =>
            link.mutate({ characterId: selection.character.id, figurinoSheetId: sheetId })
          }
        />
      )}
      {link.isError && (
        <p className="mt-1 text-xs text-red">Não foi possível atualizar o vínculo.</p>
      )}
    </div>
  );
}

/** Foto ainda não enviada, escolhida durante a criação de uma ficha nova — só sobe ao servidor
 * depois que a ficha existe (o endpoint de foto precisa de um `sheetId`), no submit do
 * formulário. */
function NewFigurinoPhotoField({
  file,
  onChange,
}: {
  file: File | null;
  onChange: (file: File | null) => void;
}) {
  const [preview, setPreview] = useState<string | null>(null);

  const handleFile = (f: File | null) => {
    onChange(f);
    setPreview((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return f ? URL.createObjectURL(f) : null;
    });
  };

  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-muted">Foto do figurino</label>
      {preview && (
        <img src={preview} alt="Prévia da foto do figurino" className="mb-2 h-32 w-32 rounded-md object-cover" />
      )}
      <input
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="max-w-[220px] text-xs text-ink"
        onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
        aria-label="Foto do figurino"
      />
      <p className="mt-1 text-xs text-muted">
        JPG, PNG ou WebP. Recomendado: foto do traje completo.
      </p>
      {file && !preview && <p className="mt-1 text-xs text-muted">{file.name}</p>}
    </div>
  );
}

/** Foto da ficha de figurino (feature 155) — envio, girar e remover. */
function FigurinoPhotoField({ sheetId, photoUrl }: { sheetId: number; photoUrl: string | null }) {
  const upload = useUploadFigurinoPhoto();
  const remove = useRemoveFigurinoPhoto();
  const rotate = useRotateFigurinoPhoto();
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);

  const handleFile = (file: File | null) => {
    if (!file) return;
    setPreview(URL.createObjectURL(file));
    upload.mutate(
      { id: sheetId, file },
      { onSettled: () => inputRef.current && (inputRef.current.value = "") },
    );
  };

  const displayUrl = preview ?? assetUrl(photoUrl ?? undefined);
  const busy = upload.isPending || remove.isPending || rotate.isPending;

  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-muted">Foto</label>
      {displayUrl ? (
        <img src={displayUrl} alt="Foto do figurino" className="mb-2 h-32 w-32 rounded-md object-cover" />
      ) : (
        <p className="mb-2 text-sm text-muted">Nenhuma foto enviada.</p>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="max-w-[170px] text-xs text-ink"
          onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
          aria-label="Enviar foto"
        />
        {photoUrl && (
          <>
            <Button
              variant="ghost"
              size="sm"
              loading={rotate.isPending}
              disabled={busy}
              onClick={() => rotate.mutate({ id: sheetId, direction: "cw" })}
            >
              Girar
            </Button>
            <Button
              variant="ghost"
              size="sm"
              loading={remove.isPending}
              disabled={busy}
              onClick={() => {
                if (window.confirm("Remover a foto?")) {
                  setPreview(null);
                  remove.mutate(sheetId);
                }
              }}
            >
              Remover
            </Button>
          </>
        )}
      </div>
      {(upload.isError || rotate.isError) && (
        <p className="mt-1 text-xs text-red">Formato não aceito ou falha ao processar a foto.</p>
      )}
    </div>
  );
}

/** Editor de tags em chips (feature 183) — adicionar via Enter/vírgula, remover com ✕. */
function TagsField({ tags, onChange }: { tags: string[]; onChange: (tags: string[]) => void }) {
  const [draft, setDraft] = useState("");

  const addTag = () => {
    const name = draft.trim();
    if (!name) return;
    if (!tags.some((t) => t.toLowerCase() === name.toLowerCase())) {
      onChange([...tags, name]);
    }
    setDraft("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTag();
    }
  };

  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-muted">Tags</label>
      <div className="flex flex-wrap gap-1.5">
        {tags.map((tag) => (
          <span
            key={tag}
            className="flex items-center gap-1 rounded-full bg-accent-soft px-2 py-0.5 text-xs text-accent-dark"
          >
            {tag}
            <button
              type="button"
              onClick={() => onChange(tags.filter((t) => t !== tag))}
              aria-label={`Remover tag ${tag}`}
              className="hover:opacity-70"
            >
              ✕
            </button>
          </span>
        ))}
      </div>
      <input
        className="mt-1.5 h-9 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink"
        placeholder="Digite e pressione Enter…"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={addTag}
        aria-label="Adicionar tag"
      />
    </div>
  );
}

export function FigurinoFormPage() {
  const params = useParams<{ id: string }>();
  const isEdit = Boolean(params.id);
  const sheetId = isEdit ? Number(params.id) : null;
  const navigate = useNavigate();

  const list = useFigurinoSheets();
  const sheet = sheetId ? list.data?.items.find((s) => s.id === sheetId) : undefined;

  const create = useCreateFigurinoSheet();
  const edit = useEditFigurinoSheet();
  const del = useDeleteFigurinoSheet();
  const uploadPhoto = useUploadFigurinoPhoto();

  const [characterName, setCharacterName] = useState("");
  const [pieces, setPieces] = useState<FigurinoPiece[]>([{ name: "", qty: 1 }]);
  const [tags, setTags] = useState<string[]>([]);
  const [notes, setNotes] = useState("");
  const [newPhoto, setNewPhoto] = useState<File | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (isEdit && sheet && !loaded) {
      setCharacterName(sheet.character_name);
      setPieces(sheet.pieces.length > 0 ? sheet.pieces : [{ name: "", qty: 1 }]);
      setTags(sheet.tags);
      setNotes(sheet.notes ?? "");
      setLoaded(true);
    }
  }, [isEdit, sheet, loaded]);

  const mutation = isEdit ? edit : create;

  const updatePiece = (i: number, patch: Partial<FigurinoPiece>) =>
    setPieces((ps) => ps.map((p, idx) => (idx === i ? { ...p, ...patch } : p)));

  const removePiece = (i: number) => setPieces((ps) => ps.filter((_, idx) => idx !== i));

  const submit = () => {
    if (!characterName.trim()) return;
    const cleanPieces = pieces.filter((p) => p.name.trim());
    const body = { character_name: characterName.trim(), pieces: cleanPieces, notes, tags };
    if (isEdit && sheetId) {
      edit.mutate({ id: sheetId, ...body }, { onSuccess: () => navigate("/figurinos") });
    } else {
      create.mutate(body, {
        onSuccess: (created: FigurinoSheetItem) => {
          if (newPhoto) {
            // Endpoint de foto exige uma ficha já existente — sobe logo após criar, e leva
            // para a edição (não a lista) para o usuário confirmar que a foto foi salva.
            uploadPhoto.mutate(
              { id: created.id, file: newPhoto },
              { onSettled: () => navigate(`/figurinos/${created.id}/edit`) },
            );
          } else {
            navigate("/figurinos");
          }
        },
      });
    }
  };

  if (isEdit && list.isLoading) {
    return <div className="mx-auto max-w-5xl p-6 text-sm text-muted">Carregando…</div>;
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-4 sm:p-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/figurinos">‹ Figurino</Link>
      </Button>
      <PageHeader
        title={isEdit ? `Editar — ${sheet?.character_name ?? ""}` : "Nova ficha de figurino"}
      />

      <Card>
        <CardContent className="space-y-4 p-4">
          {/* Identificação da ficha à esquerda, checklist de peças à direita: a lista de peças
              cresce sem empurrar foto, tags e observações para baixo da dobra. */}
          <div className="grid items-start gap-6 [&>*]:min-w-0 lg:grid-cols-2">
          <div className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-muted">
              Nome do personagem <span className="text-red">*</span>
            </label>
            <input
              className="h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink"
              placeholder="Ex: Palhaço, Fada, Cantor, DJ"
              value={characterName}
              onChange={(e) => setCharacterName(e.target.value)}
              aria-label="Nome do personagem"
            />
          </div>

          {isEdit && sheetId ? (
            <FigurinoPhotoField sheetId={sheetId} photoUrl={sheet?.photo_url ?? null} />
          ) : (
            <NewFigurinoPhotoField file={newPhoto} onChange={setNewPhoto} />
          )}

          <TagsField tags={tags} onChange={setTags} />

          <div>
            <label className="mb-1 block text-xs font-medium text-muted">Observações</label>
            <textarea
              className="min-h-20 w-full rounded-md border border-line bg-panel p-2 text-sm text-ink"
              placeholder="Instruções especiais, cuidados com as peças, etc."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>

          {isEdit && sheetId && <FigurinoCatalogLinkField sheetId={sheetId} />}
          </div>

          <div>
            <div className="mb-1 flex items-center justify-between">
              <label className="text-xs font-medium text-muted">Peças do figurino</label>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setPieces((ps) => [...ps, { name: "", qty: 1 }])}
              >
                + Adicionar peça
              </Button>
            </div>
            <p className="mb-2 text-xs text-muted">
              Cada peça vira um item da checklist de retirada/devolução.
            </p>
            <div className="mb-1 flex items-center gap-2 text-[11px] font-medium uppercase text-muted">
              <span className="w-16 text-center">Qtd</span>
              <span className="flex-1">Descrição da peça</span>
              <span className="w-9" aria-hidden="true" />
            </div>
            <div className="space-y-2">
              {pieces.map((p, i) => (
                <div key={i} className="flex items-center gap-2">
                  <input
                    type="number"
                    min={1}
                    className="h-9 w-16 rounded-md border border-line bg-panel px-2 text-center text-sm text-ink"
                    value={p.qty}
                    onChange={(e) => updatePiece(i, { qty: Math.max(1, Number(e.target.value) || 1) })}
                    aria-label="Quantidade"
                  />
                  <input
                    className="h-9 flex-1 rounded-md border border-line bg-panel px-2 text-sm text-ink"
                    placeholder="Ex: Blazer azul, Calça preta, Sapato Oxford..."
                    value={p.name}
                    onChange={(e) => updatePiece(i, { name: e.target.value })}
                    aria-label="Descrição da peça"
                  />
                  <Button variant="ghost" size="sm" onClick={() => removePiece(i)} aria-label="Remover peça">
                    ✕
                  </Button>
                </div>
              ))}
            </div>
          </div>
          </div>

          {mutation.isError && (
            <p className="text-sm text-red">Não foi possível salvar a ficha.</p>
          )}

          <div className="flex items-center justify-between gap-2 border-t border-line pt-4">
            <div className="flex gap-2">
              <Button
                loading={mutation.isPending || uploadPhoto.isPending}
                disabled={!characterName.trim()}
                onClick={submit}
              >
                {isEdit ? "Salvar" : "Criar ficha"}
              </Button>
              <Button asChild variant="outline">
                <Link to="/figurinos">Cancelar</Link>
              </Button>
            </div>
            {isEdit && sheetId && (
              <Button
                variant="ghost"
                loading={del.isPending}
                onClick={() => {
                  if (window.confirm(`Excluir a ficha de "${sheet?.character_name}"?`)) {
                    del.mutate(sheetId, { onSuccess: () => navigate("/figurinos") });
                  }
                }}
              >
                Excluir
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
