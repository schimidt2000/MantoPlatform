import { useState } from "react";
import { assetUrl, ApiRequestError } from "@manto/api-client";
import { Card, CardContent, CardHeader, CardTitle, FileUpload, Button } from "@manto/ui";
import { useCurrentTalent } from "../lib/portalAuth";
import { useDocumentUpload, usePhotoUpload } from "../lib/portalProfile";

const PHOTO_ACCEPT = "image/jpeg,image/png,image/webp";
const PHOTO_MAX = 8 * 1024 * 1024;
const DOC_ACCEPT = "image/jpeg,image/png,image/webp,application/pdf";
const DOC_MAX = 10 * 1024 * 1024;

export function PortalFotosDocumentosPage() {
  const { data: talent } = useCurrentTalent();
  const photoUpload = usePhotoUpload();
  const documentUpload = useDocumentUpload();

  const [faceError, setFaceError] = useState<string | undefined>();
  const [fullError, setFullError] = useState<string | undefined>();
  const [cnhError, setCnhError] = useState<string | undefined>();
  const [cnhSent, setCnhSent] = useState(false);
  const [docError, setDocError] = useState<string | undefined>();
  const [docSent, setDocSent] = useState(false);

  function handlePhoto(kind: "face" | "full", file: File | null) {
    if (kind === "face") setFaceError(undefined);
    else setFullError(undefined);
    if (!file) return;

    photoUpload.mutate(
      { kind, file },
      {
        onError: (err) => {
          const message = err instanceof ApiRequestError ? err.message : "Falha no envio.";
          if (kind === "face") setFaceError(message);
          else setFullError(message);
        },
      },
    );
  }

  function handleDocument(kind: "cnh" | "doc", file: File | null) {
    const setError = kind === "cnh" ? setCnhError : setDocError;
    const setSent = kind === "cnh" ? setCnhSent : setDocSent;
    setError(undefined);
    setSent(false);
    if (!file) return;

    documentUpload.mutate(
      { kind, file },
      {
        onSuccess: () => setSent(true),
        onError: (err) => {
          setError(err instanceof ApiRequestError ? err.message : "Falha no envio.");
        },
      },
    );
  }

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-lg font-semibold text-ink">Fotos e Documentos</h1>

      <Card>
        <CardHeader>
          <CardTitle>Foto de rosto</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {talent?.photo_face_url && (
            <img
              src={assetUrl(talent.photo_face_url)}
              alt="Foto de rosto atual"
              className="h-32 w-32 rounded-md object-cover"
            />
          )}
          <FileUpload
            label="Nova foto de rosto"
            accept={PHOTO_ACCEPT}
            maxSizeBytes={PHOTO_MAX}
            error={faceError}
            onChange={(file) => {
              handlePhoto("face", file);
            }}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Foto de corpo inteiro</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {talent?.photo_full_url && (
            <img
              src={assetUrl(talent.photo_full_url)}
              alt="Foto de corpo inteiro atual"
              className="h-40 w-32 rounded-md object-cover"
            />
          )}
          <FileUpload
            label="Nova foto de corpo inteiro"
            accept={PHOTO_ACCEPT}
            maxSizeBytes={PHOTO_MAX}
            error={fullError}
            onChange={(file) => {
              handlePhoto("full", file);
            }}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Foto do documento (RG, CPF ou CNH)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <FileUpload
            label="Nova foto do documento (imagem ou PDF)"
            accept={DOC_ACCEPT}
            maxSizeBytes={DOC_MAX}
            error={docError}
            onChange={(file) => {
              handleDocument("doc", file);
            }}
          />
          {docSent && <p className="text-sm text-green">Documento enviado com sucesso.</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Arquivo da CNH</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <FileUpload
            label="Novo arquivo da CNH (imagem ou PDF)"
            accept={DOC_ACCEPT}
            maxSizeBytes={DOC_MAX}
            error={cnhError}
            onChange={(file) => {
              handleDocument("cnh", file);
            }}
          />
          {cnhSent && <p className="text-sm text-green">CNH enviada com sucesso.</p>}
        </CardContent>
      </Card>

      {(photoUpload.isPending || documentUpload.isPending) && (
        <Button disabled loading className="w-full">
          Enviando...
        </Button>
      )}
    </div>
  );
}
