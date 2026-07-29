import { useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Download, Pencil, Trash2 } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  cn,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  FileUpload,
  Input,
  PageHeader,
  Skeleton,
} from "@manto/ui";
import { ApiRequestError, assetUrl } from "@manto/api-client";
import {
  useAcervo3D,
  useCreateAcervoItem,
  useDeleteAcervoItem,
  useUpdateAcervoItem,
  type Acervo3DItem,
} from "../lib/impressoes3d";

const PHOTO_ACCEPT = "image/jpeg,image/png";
const MODEL_ACCEPT = ".zip,.stl,.3mf";
const MAX_UPLOAD_MB = 50;
const MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024;

/** Mensagem de erro de um campo específico devolvida pela API (400 com `fields`). */
function fieldError(error: unknown, field: string): string | undefined {
  return error instanceof ApiRequestError ? error.fields?.[field] : undefined;
}

/** Mensagem geral amigável de um erro de mutação. */
function generalError(error: unknown): string | undefined {
  if (!error) return undefined;
  return error instanceof Error ? error.message : "Não foi possível concluir a operação.";
}

interface AcervoFormProps {
  /** Peça em edição; ausente = formulário de cadastro. */
  item?: Acervo3DItem;
  /** Chamado após a API confirmar o salvamento. */
  onSaved?: () => void;
  /** Informe para exibir o botão "Cancelar" (usado no Dialog de edição). */
  onCancel?: () => void;
}

/**
 * Formulário da peça — "Foto de Preview (JPG/PNG)" e **um ou mais** "Arquivos 3D".
 *
 * Serve cadastro e edição. Na edição os arquivos 3D são **cumulativos**: os novos se somam aos
 * já salvos, e remover é explícito (o servidor recusa deixar a peça sem nenhum arquivo).
 */
function AcervoForm({ item, onSaved, onCancel }: AcervoFormProps) {
  const isEdit = item !== undefined;
  const [name, setName] = useState(item?.name ?? "");
  const [photo, setPhoto] = useState<File | null>(null);
  const [modelFiles, setModelFiles] = useState<File[]>([]);
  const [removeFileIds, setRemoveFileIds] = useState<number[]>([]);
  const modelInputRef = useRef<HTMLInputElement>(null);
  const create = useCreateAcervoItem();
  const update = useUpdateAcervoItem();
  const mutation = isEdit ? update : create;
  const error = mutation.error;

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const input = { name: name.trim(), photo, files: modelFiles, removeFileIds };
    // O formulário NUNCA é limpo em caso de erro (Princípio V) — a limpeza é o `onSaved` do
    // chamador, que remonta este componente por `key` (o `FileUpload` guarda o nome do arquivo
    // em estado interno, então zerar o estado daqui não apagaria o que ele mostra).
    if (isEdit) {
      update.mutate({ id: item.id, input }, { onSuccess: () => onSaved?.() });
      return;
    }
    create.mutate(input, { onSuccess: () => onSaved?.() });
  }

  /** Arquivos já salvos que sobrariam depois de aplicar as remoções marcadas. */
  const keptFiles = (item?.files ?? []).filter((f) => !removeFileIds.includes(f.id));

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <label className="block">
        <span className="mb-1 block text-sm text-muted">
          Nome da peça <span className="text-red">*</span>
        </span>
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Ex.: Chaveiro Homem-Aranha"
          aria-invalid={Boolean(fieldError(error, "name"))}
          aria-label="Nome da peça"
        />
        {fieldError(error, "name") && (
          <p className="mt-1 text-sm text-red" role="alert">
            {fieldError(error, "name")}
          </p>
        )}
      </label>

      <div className="grid gap-3 sm:grid-cols-2">
        <FileUpload
          label="Foto de Preview (JPG/PNG)"
          accept={PHOTO_ACCEPT}
          maxSizeBytes={MAX_UPLOAD_BYTES}
          required={!isEdit}
          error={fieldError(error, "photo")}
          onChange={setPhoto}
          existingUrl={isEdit ? assetUrl(item.photo_url) : undefined}
          existingLabel="Foto atual"
        />

        <div>
          <span className="mb-1 block text-sm text-muted">
            Arquivos 3D (.stl, .3mf, .zip){!isEdit && <span className="text-red"> *</span>}
          </span>
          <div
            className={cn(
              "space-y-2 rounded-md border border-line bg-panel p-2",
              fieldError(error, "files") && "border-red ring-2 ring-red/30",
            )}
          >
            {isEdit && item.files.length > 0 && (
              <ul className="divide-y divide-line">
                {item.files.map((saved) => {
                  const marked = removeFileIds.includes(saved.id);
                  return (
                    <li key={saved.id} className="flex items-center gap-2 py-1.5">
                      <a
                        href={assetUrl(saved.file_path)}
                        download
                        className={cn(
                          "min-w-0 flex-1 truncate text-sm text-blue underline",
                          marked && "text-muted line-through no-underline",
                        )}
                      >
                        {saved.original_name ?? `Arquivo ${saved.position + 1}`}
                      </a>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        aria-label={
                          marked
                            ? `Manter ${saved.original_name ?? "arquivo"}`
                            : `Remover ${saved.original_name ?? "arquivo"}`
                        }
                        onClick={() =>
                          setRemoveFileIds((prev) =>
                            marked ? prev.filter((id) => id !== saved.id) : [...prev, saved.id],
                          )
                        }
                      >
                        {marked ? "Desfazer" : "✕"}
                      </Button>
                    </li>
                  );
                })}
              </ul>
            )}

            <input
              ref={modelInputRef}
              type="file"
              multiple
              accept={MODEL_ACCEPT}
              className="w-full text-sm text-ink"
              aria-label="Adicionar arquivos 3D"
              onChange={(e) => setModelFiles(Array.from(e.target.files ?? []))}
            />
            <p className="text-xs text-muted">
              {modelFiles.length > 0
                ? `${modelFiles.length} arquivo(s) a enviar: ${modelFiles
                    .map((f) => f.name)
                    .join(", ")}`
                : isEdit
                  ? `${keptFiles.length} arquivo(s) salvos — escolha novos para acrescentar.`
                  : `Pode enviar vários de uma vez (máx. ${MAX_UPLOAD_MB} MB cada).`}
            </p>
          </div>
          {fieldError(error, "files") && (
            <p className="mt-1 text-sm text-red" role="alert">
              {fieldError(error, "files")}
            </p>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" loading={mutation.isPending}>
          {isEdit ? "Salvar alterações" : "Cadastrar peça"}
        </Button>
        {onCancel && (
          <Button type="button" variant="ghost" onClick={onCancel}>
            Cancelar
          </Button>
        )}
      </div>
      {/* Erro geral só quando NÃO há campo culpado — senão a mensagem apareceria duplicada. */}
      {error &&
        !fieldError(error, "name") &&
        !fieldError(error, "photo") &&
        !fieldError(error, "files") && (
          <p className="text-sm text-red" role="alert">
            {generalError(error)}
          </p>
        )}
    </form>
  );
}

interface AcervoCardProps {
  item: Acervo3DItem;
  onEdit: () => void;
  onDelete: () => void;
}

/** Card de uma peça do acervo: foto grande, nome, contagem de usos e ações. */
function AcervoCard({ item, onEdit, onDelete }: AcervoCardProps) {
  const update = useUpdateAcervoItem();
  return (
    <Card className={item.is_active ? undefined : "opacity-60"}>
      <CardContent className="space-y-2 p-3">
        <img
          src={assetUrl(item.photo_url)}
          alt={item.name}
          loading="lazy"
          className="aspect-square w-full rounded-md object-cover"
        />
        <div className="flex items-start justify-between gap-2">
          <span className="min-w-0 flex-1 truncate font-medium text-ink">{item.name}</span>
          {!item.is_active && <Badge tone="neutral">Inativa</Badge>}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={item.usage_count > 0 ? "accent" : "neutral"}>
            {item.usage_count === 1 ? "1 uso em evento" : `${item.usage_count} usos em eventos`}
          </Badge>
          <Badge tone="neutral">
            {item.files.length === 1 ? "1 arquivo 3D" : `${item.files.length} arquivos 3D`}
          </Badge>
        </div>
        <ul className="space-y-0.5">
          {item.files.map((modelFile) => (
            <li key={modelFile.id}>
              <a
                href={assetUrl(modelFile.file_path)}
                download
                className="flex items-center gap-1.5 truncate text-sm text-blue hover:underline"
              >
                <Download className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                <span className="truncate">
                  {modelFile.original_name ?? `Arquivo ${modelFile.position + 1}`}
                </span>
              </a>
            </li>
          ))}
        </ul>
        <div className="flex flex-wrap items-center gap-1.5">
          <Button variant="ghost" size="sm" onClick={onEdit} aria-label={`Editar ${item.name}`}>
            <Pencil className="h-4 w-4" aria-hidden="true" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            loading={update.isPending}
            onClick={() => update.mutate({ id: item.id, input: { isActive: !item.is_active } })}
          >
            {item.is_active ? "Inativar" : "Reativar"}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={onDelete}
            aria-label={`Excluir ${item.name}`}
          >
            <Trash2 className="h-4 w-4 text-red" aria-hidden="true" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Acervo 3D (`/3d/acervo`) — catálogo dos modelos base do Artista 3D (feature 200).
 *
 * Grade de cards com a foto de preview (é por ela que a peça é escolhida no evento — Princípio
 * X.2), a contagem de quantas vezes o modelo já foi usado em eventos e o download de cada
 * arquivo 3D. O cadastro pede a foto e **um ou mais** arquivos (feature 201).
 */
export function Acervo3DPage() {
  const reduceMotion = useReducedMotion();
  const query = useAcervo3D();
  const remove = useDeleteAcervoItem();
  const [editing, setEditing] = useState<Acervo3DItem | null>(null);
  const [deleting, setDeleting] = useState<Acervo3DItem | null>(null);
  // Remonta o formulário de cadastro após cada sucesso: o `FileUpload` do design system guarda o
  // nome do arquivo escolhido em estado interno, e sem trocar a `key` ele continuaria exibindo o
  // arquivo da peça anterior como se ainda estivesse selecionado.
  const [formKey, setFormKey] = useState(0);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Acervo 3D"
        subtitle="Modelos base disponíveis para vincular como presente nos eventos."
        className="mb-0"
      />

      <Card>
        <CardContent className="p-4">
          <div className="mb-3 flex items-center justify-between gap-2">
            <h2 className="text-[11px] font-bold uppercase tracking-[0.07em] text-muted">
              Cadastrar nova peça
            </h2>
            {savedAt !== null && <span className="text-sm text-green">Peça salva.</span>}
          </div>
          <AcervoForm
            key={formKey}
            onSaved={() => {
              setFormKey((k) => k + 1);
              setSavedAt(Date.now());
            }}
          />
        </CardContent>
      </Card>

      {query.isLoading && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-64 w-full" />
          ))}
        </div>
      )}
      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o Acervo 3D.
        </div>
      )}
      {query.data && query.data.items.length === 0 && (
        <p className="text-sm text-muted">
          Nenhuma peça cadastrada ainda. Use o formulário acima para começar.
        </p>
      )}

      {query.data && query.data.items.length > 0 && (
        <motion.div
          className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.22, ease: "easeOut" }}
        >
          <AnimatePresence initial={false}>
            {query.data.items.map((item) => (
              <motion.div
                key={item.id}
                layout={!reduceMotion}
                exit={reduceMotion ? undefined : { opacity: 0, scale: 0.96 }}
                transition={{ duration: 0.18, ease: "easeOut" }}
              >
                <AcervoCard
                  item={item}
                  onEdit={() => setEditing(item)}
                  onDelete={() => setDeleting(item)}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </motion.div>
      )}

      <Dialog open={editing !== null} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent open={editing !== null} className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Editar peça</DialogTitle>
            <DialogDescription>
              Deixe um arquivo em branco para manter o que já está salvo.
            </DialogDescription>
          </DialogHeader>
          {editing && (
            <AcervoForm
              key={editing.id}
              item={editing}
              onSaved={() => setEditing(null)}
              onCancel={() => setEditing(null)}
            />
          )}
        </DialogContent>
      </Dialog>

      <Dialog
        open={deleting !== null}
        onOpenChange={(open) => {
          if (!open) {
            setDeleting(null);
            remove.reset();
          }
        }}
      >
        <DialogContent open={deleting !== null}>
          <DialogHeader>
            <DialogTitle>Excluir peça do Acervo</DialogTitle>
            <DialogDescription>
              A peça “{deleting?.name}” e seus arquivos serão apagados definitivamente. Peças já
              usadas em eventos não podem ser excluídas — inative-as.
            </DialogDescription>
          </DialogHeader>
          {remove.isError && (
            <p className="mb-3 text-sm text-red" role="alert">
              {generalError(remove.error)}
            </p>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleting(null)} disabled={remove.isPending}>
              Cancelar
            </Button>
            <Button
              className="bg-red hover:bg-red/90"
              loading={remove.isPending}
              onClick={() =>
                deleting &&
                remove.mutate(deleting.id, { onSuccess: () => setDeleting(null) })
              }
            >
              Excluir
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
