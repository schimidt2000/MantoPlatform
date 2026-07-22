import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { Button, Card, CardContent } from "@manto/ui";
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
} from "../lib/figurino";

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

  const [characterName, setCharacterName] = useState("");
  const [pieces, setPieces] = useState<FigurinoPiece[]>([{ name: "", qty: 1 }]);
  const [notes, setNotes] = useState("");
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (isEdit && sheet && !loaded) {
      setCharacterName(sheet.character_name);
      setPieces(sheet.pieces.length > 0 ? sheet.pieces : [{ name: "", qty: 1 }]);
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
    const body = { character_name: characterName.trim(), pieces: cleanPieces, notes };
    if (isEdit && sheetId) {
      edit.mutate({ id: sheetId, ...body }, { onSuccess: () => navigate("/figurinos") });
    } else {
      create.mutate(body, { onSuccess: () => navigate("/figurinos") });
    }
  };

  if (isEdit && list.isLoading) {
    return <div className="mx-auto max-w-xl p-6 text-sm text-muted">Carregando…</div>;
  }

  return (
    <div className="mx-auto max-w-xl space-y-4 p-4 sm:p-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/figurinos">‹ Figurino</Link>
      </Button>
      <h1 className="text-2xl font-semibold text-ink">
        {isEdit ? `Editar — ${sheet?.character_name ?? ""}` : "Nova ficha de figurino"}
      </h1>

      <Card>
        <CardContent className="space-y-4 p-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-muted">Nome do personagem</label>
            <input
              className="h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink"
              value={characterName}
              onChange={(e) => setCharacterName(e.target.value)}
              aria-label="Nome do personagem"
            />
          </div>

          <div>
            <div className="mb-1 flex items-center justify-between">
              <label className="text-xs font-medium text-muted">Peças</label>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setPieces((ps) => [...ps, { name: "", qty: 1 }])}
              >
                + Adicionar peça
              </Button>
            </div>
            <div className="space-y-2">
              {pieces.map((p, i) => (
                <div key={i} className="flex items-center gap-2">
                  <input
                    type="number"
                    min={1}
                    className="h-9 w-16 rounded-md border border-line bg-panel px-2 text-sm text-ink"
                    value={p.qty}
                    onChange={(e) => updatePiece(i, { qty: Math.max(1, Number(e.target.value) || 1) })}
                    aria-label="Quantidade"
                  />
                  <input
                    className="h-9 flex-1 rounded-md border border-line bg-panel px-2 text-sm text-ink"
                    placeholder="Nome da peça"
                    value={p.name}
                    onChange={(e) => updatePiece(i, { name: e.target.value })}
                    aria-label="Nome da peça"
                  />
                  <Button variant="ghost" size="sm" onClick={() => removePiece(i)} aria-label="Remover peça">
                    ✕
                  </Button>
                </div>
              ))}
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-muted">Notas</label>
            <textarea
              className="min-h-20 w-full rounded-md border border-line bg-panel p-2 text-sm text-ink"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>

          {isEdit && sheetId && (
            <FigurinoPhotoField sheetId={sheetId} photoUrl={sheet?.photo_url ?? null} />
          )}

          {mutation.isError && (
            <p className="text-sm text-red">Não foi possível salvar a ficha.</p>
          )}

          <div className="flex items-center justify-between gap-2 border-t border-line pt-4">
            <div className="flex gap-2">
              <Button loading={mutation.isPending} disabled={!characterName.trim()} onClick={submit}>
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
