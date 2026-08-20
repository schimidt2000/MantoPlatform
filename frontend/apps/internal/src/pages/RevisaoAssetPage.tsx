import { useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ApiRequestError, assetUrl } from "@manto/api-client";
import { Button, Card, CardContent, CardHeader, CardTitle, Skeleton } from "@manto/ui";
import {
  useAddRevisaoComment,
  useDeleteComment,
  useDeleteRevisaoAsset,
  useFinalizeRevisaoAsset,
  useReplaceRevisaoAsset,
  useRevisaoAsset,
  useRevisaoComments,
  useToggleResolveComment,
  useUpdateAssetStatus,
  type AddCommentInput,
} from "../lib/revisao";
import { UploadProgressBar } from "../components/UploadProgressBar";
import {
  CommentFeed,
  NewCommentForm,
  StatusBadge,
  VersionSelector,
  VideoPlayer,
  formatTimecode,
  type VideoPlayerHandle,
} from "../components/revisao";

export function RevisaoAssetPage() {
  const params = useParams<{ spaceId: string; assetId: string }>();
  const spaceId = Number(params.spaceId);
  const assetId = Number(params.assetId);
  const [searchParams] = useSearchParams();
  const version = searchParams.get("v") ? Number(searchParams.get("v")) : undefined;
  const navigate = useNavigate();

  const query = useRevisaoAsset(spaceId, assetId, version);
  const commentsQuery = useRevisaoComments(assetId, version);
  const addComment = useAddRevisaoComment(assetId);
  const toggleResolve = useToggleResolveComment(assetId);
  const deleteComment = useDeleteComment(assetId);
  const deleteAsset = useDeleteRevisaoAsset();
  const replaceAsset = useReplaceRevisaoAsset(assetId);
  const finalizeAsset = useFinalizeRevisaoAsset(assetId);
  const updateStatus = useUpdateAssetStatus(assetId);

  const [commentBody, setCommentBody] = useState("");
  const [pageNumber, setPageNumber] = useState("1");
  const mediaRef = useRef<HTMLAudioElement>(null);
  const playerRef = useRef<VideoPlayerHandle>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const [imageClick, setImageClick] = useState<{ x: number; y: number } | null>(null);
  const [replaceError, setReplaceError] = useState<string | null>(null);
  const [replaceProgress, setReplaceProgress] = useState<number | null>(null);
  const reduceMotion = useReducedMotion();

  if (query.isLoading) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
        <Skeleton className="h-80 w-full" />
      </div>
    );
  }

  if (query.isError || !query.data) {
    return (
      <div className="mx-auto max-w-3xl p-4 sm:p-6">
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar o material.
        </div>
      </div>
    );
  }

  const { asset, can_manage, viewing_version, version_file, history, space_title } = query.data;
  const isReadOnly = viewing_version !== null;
  const displayUrl = isReadOnly ? version_file?.file_url : asset.file_url;
  const url = assetUrl(displayUrl ?? undefined);
  const isVideo = asset.media_type === "video";
  const comments = commentsQuery.data ?? [];
  const commentTimecodes = comments
    .map((c) => c.timecode)
    .filter((t): t is number => t != null);

  const submitNonVideoComment = () => {
    if (!commentBody.trim()) return;
    const input: AddCommentInput = { body: commentBody };
    if (asset.media_type === "audio") {
      input.timecode = mediaRef.current?.currentTime ?? 0;
    } else if (asset.media_type === "pdf") {
      input.page = Number(pageNumber) || 1;
    } else if (asset.media_type === "image" && imageClick) {
      input.pos_x = imageClick.x;
      input.pos_y = imageClick.y;
    }
    addComment.mutate(input, { onSuccess: () => setCommentBody("") });
  };

  return (
    <div className="mx-auto max-w-[1600px] space-y-4 p-4 sm:p-6">
      <Button asChild variant="ghost" size="sm">
        <Link to={`/revisao/${spaceId}`}>‹ {space_title}</Link>
      </Button>

      <header className="space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-ink">{asset.original_name}</h1>
            <p className="text-sm text-muted">
              Versão {viewing_version ?? asset.version}
              {isReadOnly && " (somente leitura)"}
            </p>
          </div>
          {can_manage && !isReadOnly && (
            <Button
              variant="outline"
              size="sm"
              loading={deleteAsset.isPending}
              onClick={() => {
                if (window.confirm("Excluir este material?")) {
                  deleteAsset.mutate(asset.id, { onSuccess: () => navigate(`/revisao/${spaceId}`) });
                }
              }}
            >
              Excluir material
            </Button>
          )}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <AnimatePresence mode="wait">
            <motion.div
              key={asset.status}
              initial={reduceMotion ? undefined : { opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reduceMotion ? undefined : { opacity: 0, y: 4 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
            >
              <StatusBadge
                status={asset.status}
                canManage={can_manage && !isReadOnly}
                isPending={updateStatus.isPending}
                onChange={(status) => updateStatus.mutate(status)}
              />
            </motion.div>
          </AnimatePresence>
          <VersionSelector
            spaceId={spaceId}
            assetId={assetId}
            currentVersion={asset.version}
            viewingVersion={viewing_version}
            history={history}
          />
        </div>
      </header>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[7fr_3fr]">
        {/* Coluna principal: player/mídia */}
        <AnimatePresence mode="wait">
          <motion.div
            className="min-w-0"
            key={url ?? "sem-arquivo"}
            initial={reduceMotion ? undefined : { opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={reduceMotion ? undefined : { opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
          >
            <Card>
              <CardContent className="p-3">
                {!url && <p className="text-sm text-muted">Arquivo não disponível (finalizado).</p>}
                {url && isVideo && <VideoPlayer key={url} ref={playerRef} url={url} markers={commentTimecodes} />}
                {url && asset.media_type === "audio" && (
                  <audio ref={mediaRef} src={url} controls className="w-full" />
                )}
                {url && asset.media_type === "image" && (
                  <img
                    ref={imgRef}
                    src={url}
                    alt={asset.original_name}
                    className="w-full cursor-crosshair rounded-md"
                    onClick={(e) => {
                      const rect = e.currentTarget.getBoundingClientRect();
                      setImageClick({
                        x: (e.clientX - rect.left) / rect.width,
                        y: (e.clientY - rect.top) / rect.height,
                      });
                    }}
                  />
                )}
                {url && asset.media_type === "pdf" && (
                  <a href={url} target="_blank" rel="noopener noreferrer" className="text-blue underline">
                    Abrir PDF em nova aba
                  </a>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </AnimatePresence>

        {/* Coluna lateral: novo comentário, feed, gerenciamento */}
        <div className="space-y-4">
          {!isReadOnly && (
            <Card>
              <CardHeader>
                <CardTitle>Novo comentário</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {isVideo ? (
                  <NewCommentForm
                    playerRef={playerRef}
                    isPending={addComment.isPending}
                    onSubmit={(body, timecode) =>
                      addComment.mutate({ body, timecode }, { onSuccess: () => undefined })
                    }
                  />
                ) : (
                  <>
                    {asset.media_type === "audio" && (
                      <p className="text-xs text-muted">
                        Será ancorado no ponto atual do player (pause e ajuste antes de comentar).
                      </p>
                    )}
                    {asset.media_type === "pdf" && (
                      <div className="flex items-center gap-2">
                        <label className="text-xs text-muted">Página</label>
                        <input
                          type="number"
                          min={1}
                          className="h-8 w-20 rounded-md border border-line bg-panel px-2 text-sm text-ink"
                          value={pageNumber}
                          onChange={(e) => setPageNumber(e.target.value)}
                        />
                      </div>
                    )}
                    {asset.media_type === "image" && (
                      <p className="text-xs text-muted">
                        {imageClick
                          ? `Ponto marcado: ${(imageClick.x * 100).toFixed(0)}%, ${(imageClick.y * 100).toFixed(0)}%`
                          : "Clique na imagem para marcar o ponto do comentário."}
                      </p>
                    )}
                    <textarea
                      className="min-h-16 w-full rounded-md border border-line bg-panel p-2 text-sm text-ink"
                      placeholder="Escreva um comentário…"
                      value={commentBody}
                      onChange={(e) => setCommentBody(e.target.value)}
                    />
                    <Button size="sm" loading={addComment.isPending} onClick={submitNonVideoComment}>
                      Comentar
                    </Button>
                  </>
                )}
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Comentários</CardTitle>
            </CardHeader>
            <CardContent>
              {commentsQuery.isLoading && <Skeleton className="h-24 w-full" />}
              {commentsQuery.data && isVideo && (
                <CommentFeed
                  comments={comments}
                  onSeek={(time) => playerRef.current?.seekTo(time)}
                  onToggleResolve={(id) => toggleResolve.mutate(id)}
                  onDelete={(id) => deleteComment.mutate(id)}
                  togglePending={toggleResolve.isPending}
                  deletePending={deleteComment.isPending}
                />
              )}
              {commentsQuery.data && !isVideo && comments.length === 0 && (
                <p className="text-sm text-muted">Nenhum comentário nesta versão.</p>
              )}
              {commentsQuery.data && !isVideo && comments.length > 0 && (
                <ul className="divide-y divide-line">
                  {comments.map((c) => (
                    <li key={c.id} className="space-y-1 py-2">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-medium text-ink">{c.author}</span>
                        <span className="text-xs text-muted">
                          {c.timecode != null && formatTimecode(c.timecode)}
                          {c.page != null && `pág. ${c.page}`}
                          {c.pos_x != null && `${(c.pos_x * 100).toFixed(0)}%,${(c.pos_y! * 100).toFixed(0)}%`}
                        </span>
                      </div>
                      <p className={`text-sm ${c.resolved ? "text-muted line-through" : "text-ink"}`}>{c.body}</p>
                      {c.resolved && c.resolved_by_name && (
                        <p className="text-xs text-green">
                          Concluído por {c.resolved_by_name} em {c.resolved_at}
                        </p>
                      )}
                      <div className="flex gap-2">
                        {c.can_resolve && (
                          <Button
                            variant="ghost"
                            size="sm"
                            loading={toggleResolve.isPending}
                            onClick={() => toggleResolve.mutate(c.id)}
                          >
                            {c.resolved ? "Reabrir" : "Concluir"}
                          </Button>
                        )}
                        {c.can_delete && (
                          <Button
                            variant="ghost"
                            size="sm"
                            loading={deleteComment.isPending}
                            onClick={() => {
                              if (window.confirm("Excluir este comentário?")) deleteComment.mutate(c.id);
                            }}
                          >
                            Excluir
                          </Button>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          {can_manage && !isReadOnly && (
            <Card>
              <CardHeader>
                <CardTitle>Gerenciar material</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-muted">
                    Enviar nova versão (mesmo tipo: {asset.media_type})
                  </label>
                  <input
                    type="file"
                    className="text-sm text-ink"
                    disabled={replaceAsset.isPending}
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      e.target.value = "";
                      if (!file) return;
                      setReplaceError(null);
                      setReplaceProgress(0);
                      replaceAsset.mutate(
                        { file, onProgress: setReplaceProgress },
                        {
                          onSettled: () => setReplaceProgress(null),
                          onError: (err) =>
                            setReplaceError(
                              err instanceof ApiRequestError ? err.message : "Falha ao substituir.",
                            ),
                        },
                      );
                    }}
                  />
                  <UploadProgressBar
                    fraction={replaceAsset.isPending ? replaceProgress : null}
                  />
                  {replaceError && <p className="mt-1 text-xs text-red">{replaceError}</p>}
                </div>
                {asset.is_available && (
                  <Button
                    variant="outline"
                    size="sm"
                    loading={finalizeAsset.isPending}
                    onClick={() => {
                      if (window.confirm("Finalizar este material? Os arquivos serão removidos do armazenamento.")) {
                        finalizeAsset.mutate();
                      }
                    }}
                  >
                    Finalizar material
                  </Button>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
