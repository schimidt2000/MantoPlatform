import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ExternalLink, FolderOpen, Trash2, X } from "lucide-react";
import {
  AvatarThumb,
  Badge,
  Button,
  Combobox,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  Input,
  type ComboboxOption,
} from "@manto/ui";
import { ApiRequestError, assetUrl } from "@manto/api-client";
import {
  MARKETING_STATUS_ICONS,
  MARKETING_STATUS_LABELS,
  MARKETING_STATUSES,
  REVIEW_SPACE_STATUS_LABELS,
  REVIEW_SPACE_STATUS_TONES,
  useCreateMarketingPost,
  useCreateReviewSpace,
  useDeleteMarketingPost,
  useMarketingOptions,
  useUpdateMarketingPost,
  type MarketingAssigneeRef,
  type MarketingCatalogItemRef,
  type MarketingPost,
  type MarketingStatus,
  type SaveMarketingPostInput,
} from "../lib/marketing";

const INPUT_CLASS = "h-11 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";
const LABEL_CLASS = "mb-1 block text-xs font-medium text-muted";

/** Mensagem de erro de um campo específico devolvida pela API (400 com `fields`). */
function fieldError(error: unknown, field: string): string | undefined {
  return error instanceof ApiRequestError ? error.fields?.[field] : undefined;
}

/** Opções do Combobox de Temas — miniatura **quadrada** do personagem (Princípio X.2). */
function temaOptions(temas: MarketingCatalogItemRef[]): ComboboxOption[] {
  return temas.map((tema) => ({
    value: String(tema.id),
    label: tema.name,
    imageUrl: assetUrl(tema.cover_url) ?? null,
    imageShape: "square" as const,
    fallbackIcon: "🎭",
  }));
}

/**
 * Múltiplos Temas por postagem (ex.: um Reels que junta "15 Anos" e "Debutante" no mesmo vídeo):
 * o `Combobox` de busca some cada Tema já escolhido de suas próprias opções e devolve a
 * seleção pra virar um chip removível abaixo — o `Combobox` em si continua single-select, é a
 * composição que vira multi-select (nenhum componente do design system precisou mudar).
 */
function TemasMultiSelect({
  temas,
  loading,
  selectedIds,
  invalid,
  onChange,
}: {
  temas: MarketingCatalogItemRef[];
  loading: boolean;
  selectedIds: string[];
  invalid: boolean;
  /**
   * Recebe um *updater* (como o setter do `useState`), nunca o array final direto: o Combobox
   * dispara `onChange` mais de uma vez por seleção (StrictMode/dev), e calcular a partir do
   * `selectedIds` fechado no closure perderia a seleção anterior se as chamadas duplicadas
   * carregarem um valor desatualizado. Aplicar sobre o estado anterior (`prev`) é imune a isso.
   */
  onChange: (updater: (prev: string[]) => string[]) => void;
}) {
  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);
  const selectedTemas = temas.filter((tema) => selectedSet.has(String(tema.id)));
  const availableOptions = temaOptions(temas.filter((tema) => !selectedSet.has(String(tema.id))));

  return (
    <div className="space-y-2">
      <Combobox
        // Remonta a cada mudança de seleção: o filtro de exclusão troca a *identidade* da lista de
        // opções (não só o conteúdo), e o Combobox guarda estado interno de navegação por teclado
        // (`activeIndex`) que precisa zerar junto — mais simples e robusto que depender só do
        // `useMemo` interno dele reagir à referência nova do array a cada seleção.
        key={selectedIds.join(",")}
        aria-label="Buscar Tema do catálogo"
        placeholder="🔍 Buscar Tema do catálogo…"
        emptyMessage="Nenhum Tema encontrado."
        options={availableOptions}
        loading={loading}
        value={null}
        invalid={invalid}
        onChange={(next) => {
          if (!next) return;
          onChange((prev) => (prev.includes(next) ? prev : [...prev, next]));
        }}
      />
      {selectedTemas.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selectedTemas.map((tema) => (
            <span
              key={tema.id}
              className="flex items-center gap-1.5 rounded-full border border-line bg-surface-2 py-1 pl-1 pr-2 text-xs text-ink"
            >
              <AvatarThumb
                src={assetUrl(tema.cover_url)}
                name={tema.name}
                shape="square"
                size="sm"
                fallbackIcon="🎭"
              />
              {tema.name}
              <button
                type="button"
                onClick={() => {
                  const id = String(tema.id);
                  onChange((prev) => prev.filter((existing) => existing !== id));
                }}
                aria-label={`Remover Tema ${tema.name}`}
                className="ml-0.5 flex h-4 w-4 items-center justify-center rounded-full text-muted hover:bg-line hover:text-ink"
              >
                <X className="h-3 w-3" aria-hidden="true" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/** Opções do Combobox de responsáveis — miniatura **circular** de pessoa (Princípio X.2). */
function usuarioOptions(usuarios: MarketingAssigneeRef[]): ComboboxOption[] {
  return usuarios.map((usuario) => ({
    value: String(usuario.id),
    label: usuario.name,
    imageUrl: assetUrl(usuario.photo_url) ?? null,
    imageShape: "circle" as const,
  }));
}

/** Campo com rótulo e mensagem de erro da API por baixo — padrão dos formulários do projeto. */
function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className={LABEL_CLASS}>{label}</span>
      {children}
      {error && (
        <span className="mt-1 block text-sm text-red" role="alert">
          {error}
        </span>
      )}
    </label>
  );
}

/**
 * Botão do acervo bruto no Google Drive — visualmente distinto (contorno dourado + ícone de
 * pasta), porque é o atalho que a equipe mais usa no dia da produção. Abre em outra aba.
 */
function DriveButton({ url }: { url: string }) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noreferrer noopener"
      className="flex items-center justify-center gap-2 rounded-md border border-gold/60 bg-gold-soft px-3 py-2.5 text-sm font-semibold text-gold transition-colors hover:bg-gold/20"
    >
      <FolderOpen className="h-4 w-4" aria-hidden="true" />
      Abrir Acervo de Mídia no Drive
      <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
    </a>
  );
}

/**
 * Ponte com o módulo de Revisão de Mídia (feature 088).
 *
 * Sem espaço vinculado, o botão **cria** o espaço com o título do post (um clique, sem sair da
 * tela) e a interface passa a oferecer o caminho contrário: um botão grande **"Ir para Revisão"**.
 */
function ReviewBridge({ post }: { post: MarketingPost }) {
  const createReview = useCreateReviewSpace();

  if (post.review_space_id) {
    const space = post.review_space;
    return (
      <div className="space-y-2 rounded-md border border-blue/40 bg-blue-soft/40 p-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-semibold text-ink">Espaço de revisão vinculado</span>
          {space && (
            <Badge tone={REVIEW_SPACE_STATUS_TONES[space.status]}>
              {REVIEW_SPACE_STATUS_LABELS[space.status].toUpperCase()}
            </Badge>
          )}
        </div>
        {space && (
          <p className="text-xs text-muted">
            {space.asset_count} material(is) · {space.approved_count} aprovado(s)
          </p>
        )}
        <Button asChild size="lg" className="w-full">
          <Link to={`/revisao/${post.review_space_id}`}>Ir para Revisão →</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-2 rounded-md border border-line bg-surface-2/60 p-3">
      <p className="text-xs text-muted">
        Nenhum espaço de revisão ainda. Criar um espaço leva o material desta postagem para o fluxo
        de aprovação com comentários e versões.
      </p>
      <Button
        variant="outline"
        className="w-full"
        loading={createReview.isPending}
        onClick={() => createReview.mutate(post.id)}
      >
        Criar Espaço de Revisão
      </Button>
      {createReview.isError && (
        <p className="text-sm text-red" role="alert">
          {createReview.error instanceof Error
            ? createReview.error.message
            : "Não foi possível criar o espaço de revisão."}
        </p>
      )}
    </div>
  );
}

interface MarketingPostFormProps {
  /** Postagem em edição; ausente = formulário de criação. */
  post?: MarketingPost;
  /** Status inicial de um card novo (a coluna em que o usuário clicou em "+"). */
  initialStatus?: MarketingStatus;
  onSaved: () => void;
  onCancel: () => void;
}

/**
 * Formulário da postagem — serve criação e edição.
 *
 * O estado NUNCA é limpo por erro de validação (Princípio V): o `fields` do 400 vira mensagem no
 * campo exato e o que foi digitado continua ali. A limpeza é o remount por `key` feito pelo
 * Dialog.
 */
function MarketingPostForm({ post, initialStatus, onSaved, onCancel }: MarketingPostFormProps) {
  const isEdit = post !== undefined;
  const options = useMarketingOptions();
  const create = useCreateMarketingPost();
  const update = useUpdateMarketingPost();
  const mutation = isEdit ? update : create;
  const error = mutation.error;

  const [title, setTitle] = useState(post?.title ?? "");
  const [status, setStatus] = useState<MarketingStatus>(post?.status ?? initialStatus ?? "ideia");
  const [deadline, setDeadline] = useState(post?.deadline_date ?? "");
  const [publishDate, setPublishDate] = useState(post?.publish_date ?? "");
  const [platform, setPlatform] = useState(post?.platform ?? "");
  const [driveUrl, setDriveUrl] = useState(post?.drive_folder_url ?? "");
  const [permalink, setPermalink] = useState(post?.permalink ?? "");
  const [notes, setNotes] = useState(post?.notes ?? "");
  const [temaIds, setTemaIds] = useState<string[]>(
    (post?.catalog_item_ids ?? []).map((id) => String(id)),
  );
  const [assigneeId, setAssigneeId] = useState<string | null>(
    post?.assignee_id ? String(post.assignee_id) : null,
  );

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const input: SaveMarketingPostInput = {
      title: title.trim(),
      status,
      deadline_date: deadline || null,
      publish_date: publishDate || null,
      platform: platform || null,
      drive_folder_url: driveUrl.trim() || null,
      permalink: permalink.trim() || null,
      notes: notes.trim() || null,
      assignee_id: assigneeId ? Number(assigneeId) : null,
      catalog_item_ids: temaIds.map(Number),
    };
    if (isEdit) {
      update.mutate({ id: post.id, input }, { onSuccess: onSaved });
      return;
    }
    create.mutate(input, { onSuccess: onSaved });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <Field label="Título da postagem *" error={fieldError(error, "title")}>
        <Input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Ex.: Reels — bastidores da festa de 15 anos"
          aria-invalid={Boolean(fieldError(error, "title"))}
          aria-label="Título da postagem"
        />
      </Field>

      <Field label="Temas do catálogo" error={fieldError(error, "catalog_item_ids")}>
        <TemasMultiSelect
          temas={options.data?.temas ?? []}
          loading={options.isLoading}
          selectedIds={temaIds}
          invalid={Boolean(fieldError(error, "catalog_item_ids"))}
          onChange={setTemaIds}
        />
      </Field>

      <Field label="Responsável" error={fieldError(error, "assignee_id")}>
        <Combobox
          aria-label="Buscar responsável"
          placeholder="🔍 Buscar responsável…"
          emptyMessage="Nenhum usuário encontrado."
          options={usuarioOptions(options.data?.usuarios ?? [])}
          loading={options.isLoading}
          value={assigneeId}
          invalid={Boolean(fieldError(error, "assignee_id"))}
          onChange={(next) => setAssigneeId(next)}
        />
      </Field>

      <div className="grid gap-3 sm:grid-cols-2">
        {/* 6 e 7 opções: `<select>` nativo é legítimo aqui (limite do Princípio X.1 é 10). */}
        <Field label="Status" error={fieldError(error, "status")}>
          <select
            className={INPUT_CLASS}
            value={status}
            onChange={(e) => setStatus(e.target.value as MarketingStatus)}
            aria-label="Status da postagem"
          >
            {MARKETING_STATUSES.map((option) => (
              <option key={option} value={option}>
                {MARKETING_STATUS_ICONS[option]} {MARKETING_STATUS_LABELS[option]}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Plataforma" error={fieldError(error, "platform")}>
          <select
            className={INPUT_CLASS}
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            aria-label="Plataforma de publicação"
          >
            <option value="">Sem plataforma definida</option>
            {(options.data?.plataformas ?? []).map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Prazo de entrega" error={fieldError(error, "deadline_date")}>
          <input
            type="date"
            className={INPUT_CLASS}
            value={deadline}
            onChange={(e) => setDeadline(e.target.value)}
            aria-label="Prazo de entrega"
          />
        </Field>
        <Field label="Data de publicação" error={fieldError(error, "publish_date")}>
          <input
            type="date"
            className={INPUT_CLASS}
            value={publishDate}
            onChange={(e) => setPublishDate(e.target.value)}
            aria-label="Data de publicação"
          />
        </Field>
      </div>

      {/* Feature 256: é por este link que o auditor de marketing casa o card com as métricas
          reais do export da Meta. Publicar sem link não bloqueia — só avisa. */}
      <Field label="Link do post publicado" error={fieldError(error, "permalink")}>
        <Input
          type="url"
          value={permalink}
          onChange={(e) => setPermalink(e.target.value)}
          placeholder="https://www.instagram.com/p/…"
          aria-invalid={Boolean(fieldError(error, "permalink"))}
          aria-label="Link do post publicado"
          className={status === "publicado" && !permalink.trim() ? "border-gold focus-visible:ring-gold" : undefined}
        />
        {status === "publicado" && !permalink.trim() && (
          <span className="mt-1 block text-[11px] text-gold-ink">
            Cole o link do post para o relatório semanal reconhecer esta publicação.
          </span>
        )}
      </Field>

      <Field label="Pasta do acervo no Google Drive" error={fieldError(error, "drive_folder_url")}>
        <Input
          value={driveUrl}
          onChange={(e) => setDriveUrl(e.target.value)}
          placeholder="https://drive.google.com/…"
          aria-invalid={Boolean(fieldError(error, "drive_folder_url"))}
          aria-label="Link da pasta do Google Drive"
        />
      </Field>

      {post?.drive_folder_url && <DriveButton url={post.drive_folder_url} />}

      <Field label="Observações" error={fieldError(error, "notes")}>
        <textarea
          className="min-h-[80px] w-full rounded-md border border-line bg-panel p-2 text-sm text-ink"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Roteiro, referências, trilha…"
          aria-label="Observações da postagem"
        />
      </Field>

      {post && <ReviewBridge post={post} />}

      <div className="flex flex-wrap items-center justify-end gap-2 pt-1">
        {mutation.isError && !fieldError(error, "title") && (
          <span className="mr-auto text-sm text-red" role="alert">
            {error instanceof Error ? error.message : "Não foi possível salvar a postagem."}
          </span>
        )}
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancelar
        </Button>
        <Button type="submit" loading={mutation.isPending}>
          {isEdit ? "Salvar alterações" : "Criar postagem"}
        </Button>
      </div>
    </form>
  );
}

export interface MarketingPostDialogProps {
  /** Postagem em edição; `null` com `open` = criação. */
  post: MarketingPost | null;
  open: boolean;
  /** Coluna de origem do "+" — pré-seleciona o status do card novo. */
  initialStatus?: MarketingStatus;
  onClose: () => void;
}

/**
 * Card de Postagem (Dialog de edição) da feature 204.
 *
 * Concentra o planejamento (título, Tema, responsável, prazos, plataforma), o atalho para o
 * acervo bruto no Drive e as duas pontes com o resto do sistema: o Tema do catálogo (`Combobox`
 * visual) e o espaço de Revisão de Mídia.
 */
export function MarketingPostDialog({
  post,
  open,
  initialStatus,
  onClose,
}: MarketingPostDialogProps) {
  const deletePost = useDeleteMarketingPost();
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  function handleDelete() {
    if (!post) return;
    deletePost.mutate(post.id, { onSuccess: onClose });
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent open={open} className="max-h-[90vh] max-w-xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{post ? "Editar postagem" : "Nova postagem"}</DialogTitle>
          <DialogDescription>
            {post ? (
              <span className="flex flex-wrap items-center gap-2">
                {post.catalog_items.map((item) => (
                  <span key={item.id} className="flex items-center gap-1.5">
                    <AvatarThumb
                      src={assetUrl(item.cover_url)}
                      name={item.name}
                      shape="square"
                      size="sm"
                      fallbackIcon="🎭"
                    />
                    {item.name}
                  </span>
                ))}
                <span>
                  {MARKETING_STATUS_ICONS[post.status]} {MARKETING_STATUS_LABELS[post.status]}
                </span>
              </span>
            ) : (
              "Planeje a postagem e vincule os Temas, o responsável e o espaço de revisão."
            )}
          </DialogDescription>
        </DialogHeader>

        {/* `key` remonta o formulário ao trocar de card — é o que zera o estado sem `useEffect`. */}
        <MarketingPostForm
          key={post?.id ?? "novo"}
          post={post ?? undefined}
          initialStatus={initialStatus}
          onSaved={onClose}
          onCancel={onClose}
        />

        {post && (
          <div className="mt-4 border-t border-line pt-3">
            {/* Confirmação em duas etapas dentro do próprio Dialog (Princípio V — ação
                destrutiva confirmada): abrir um segundo Dialog aninhado só para isto seria
                mais frágil e não acrescenta nada. */}
            {confirmingDelete ? (
              <div className="flex flex-wrap items-center gap-2">
                <span className="mr-auto text-sm text-ink">
                  Excluir “{post.title}”? Não é possível desfazer.
                </span>
                <Button variant="ghost" size="sm" onClick={() => setConfirmingDelete(false)}>
                  Cancelar
                </Button>
                <Button
                  size="sm"
                  // Botão destrutivo: `on-color` porque o vermelho clareia para #ff6b6b no
                  // tema escuro e o branco por cima cai para 2.78:1.
                  className="bg-red text-on-color hover:bg-red/90"
                  loading={deletePost.isPending}
                  onClick={handleDelete}
                >
                  Excluir definitivamente
                </Button>
              </div>
            ) : (
              <Button
                variant="ghost"
                size="sm"
                className="text-red hover:bg-red-soft"
                onClick={() => setConfirmingDelete(true)}
              >
                <Trash2 className="h-4 w-4" aria-hidden="true" />
                Excluir postagem
              </Button>
            )}
            {deletePost.isError && (
              <p className="mt-1 text-sm text-red" role="alert">
                Não foi possível excluir a postagem.
              </p>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
