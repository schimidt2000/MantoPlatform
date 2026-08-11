import {
  useEffect,
  useId,
  useRef,
  useState,
  type DragEvent,
  type PointerEvent,
  type ReactNode,
} from "react";
import { AnimatePresence, motion, useReducedMotion, type PanInfo } from "framer-motion";
import { ChevronLeft, ChevronRight, ImagePlus, Star, Undo2, X } from "lucide-react";
import { assetUrl } from "@manto/api-client";
import { Badge, cn } from "@manto/ui";
import { attributeAtPoint, viewportPoint } from "../lib/pointerDrag";

/**
 * Atributo que marca a linha de um Personagem como zona de soltura: largar ali uma foto **já
 * salva** faz o personagem adotá-la (`AdminCatalogCharacterPanel`).
 */
export const CATALOG_CHARACTER_DROP_ATTR = "data-catalog-character-drop";

/** Dentro da faixa de 150–350ms do Princípio IX. */
const MOVE_TRANSITION = { duration: 0.24, ease: "easeOut" } as const;

const ACCEPTED_EXTENSIONS = /\.(jpe?g|png|webp)$/i;

/** Foto que já existe no banco — só ela tem id e pode ser adotada por um personagem. */
export interface ExistingPhotoSlot {
  kind: "existing";
  key: string;
  id: number;
  /** URL relativa como veio da API; o `assetUrl()` é aplicado na hora de exibir. */
  url: string;
}

/** Arquivo escolhido agora, ainda não enviado — some se o admin sair sem salvar. */
export interface NewPhotoSlot {
  kind: "new";
  key: string;
  file: File;
  previewUrl: string;
}

export type PhotoSlot = ExistingPhotoSlot | NewPhotoSlot;

export interface RemovedPhoto {
  id: number;
  url: string;
}

export interface CatalogPhotosValue {
  /** Ordem final desejada — o índice 0 é a capa. */
  photos: PhotoSlot[];
  /** Fotos salvas marcadas para remoção; só somem do banco ao salvar (dá para desfazer). */
  removed: RemovedPhoto[];
}

export const EMPTY_PHOTOS_VALUE: CatalogPhotosValue = { photos: [], removed: [] };

export interface CatalogPhotoManagerProps {
  value: CatalogPhotosValue;
  onChange: (next: CatalogPhotosValue) => void;
  /** Ordem de ids como está salva no servidor — só para avisar "alterações não salvas". */
  savedOrder?: number[];
  /** Erro de validação do campo `photos` vindo da API. */
  error?: string;
  /** Soltar uma foto já salva sobre um personagem = adotar. Omitido desliga o gesto. */
  onDropOnCharacter?: (characterId: number, imageId: number) => void;
  /** Personagem sob o ponteiro durante o arraste — quem desenha o realce é o painel. */
  onCharacterHoverChange?: (characterId: number | null) => void;
}

function moveSlot(photos: PhotoSlot[], from: number, to: number): PhotoSlot[] {
  if (from === to || from < 0 || to < 0 || from >= photos.length || to >= photos.length) {
    return photos;
  }
  const next = [...photos];
  const [moved] = next.splice(from, 1);
  next.splice(to, 0, moved);
  return next;
}

/**
 * Grade de fotos do produto: ordem, capa, adição e remoção no mesmo lugar.
 *
 * Três decisões que definem a tela:
 *
 * 1. **A capa não é um campo à parte — é a primeira foto.** O banco já tratava assim
 *    (`CatalogItem.cover_image` é `images[0]`), mas a tela pedia as duas coisas em separado
 *    ("Definir como capa" + setas), então dava para arrastar uma foto para a frente e a capa
 *    continuar sendo outra. Agora "Tornar capa" é só um atalho de "mover para a posição 1".
 * 2. **Fotos novas entram na MESMA grade**, com selo "nova", e podem ser arrastadas para o meio
 *    das antigas — o backend recebe a ordem como tokens (`12,new:0,9`).
 * 3. **Arraste por ponteiro** (o mesmo do quadro de Marketing), e não o HTML5 nativo: funciona
 *    no toque, as vizinhas se reorganizam ao vivo por baixo do dedo e o card volta animado.
 *    As setas ‹ › continuam existindo para teclado e para quem não quer arrastar.
 */
export function CatalogPhotoManager({
  value,
  onChange,
  savedOrder,
  error,
  onDropOnCharacter,
  onCharacterHoverChange,
}: CatalogPhotoManagerProps) {
  const { photos, removed } = value;
  const reduceMotion = useReducedMotion();
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const gridRef = useRef<HTMLUListElement>(null);
  const newKeyCounter = useRef(0);
  const objectUrls = useRef<string[]>([]);
  /** Caixas das células da grade em coordenadas de página, medidas no início do arraste. */
  const cellBoxes = useRef<{ left: number; top: number; right: number; bottom: number }[]>([]);

  const [draggingKey, setDraggingKey] = useState<string | null>(null);
  const [fileDropActive, setFileDropActive] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState("");

  // Os blobs de preview vivem enquanto a tela existir; sem isto cada troca de arquivo vazaria
  // um object URL até o reload.
  useEffect(() => {
    const urls = objectUrls.current;
    return () => urls.forEach((url) => URL.revokeObjectURL(url));
  }, []);

  const existingIds = photos.filter((p): p is ExistingPhotoSlot => p.kind === "existing").map((p) => p.id);
  const hasUnsavedChanges =
    savedOrder !== undefined &&
    (removed.length > 0 ||
      photos.some((p) => p.kind === "new") ||
      existingIds.join(",") !== savedOrder.join(","));

  function commit(photosNext: PhotoSlot[], removedNext: RemovedPhoto[] = removed) {
    onChange({ photos: photosNext, removed: removedNext });
  }

  function move(from: number, to: number) {
    const clamped = Math.max(0, Math.min(photos.length - 1, to));
    if (clamped === from) return;
    commit(moveSlot(photos, from, clamped));
    setAnnouncement(
      clamped === 0
        ? `Foto movida para a posição 1 de ${photos.length} — agora é a capa.`
        : `Foto movida para a posição ${clamped + 1} de ${photos.length}.`,
    );
  }

  function addFiles(fileList: FileList | File[] | null) {
    const chosen = Array.from(fileList ?? []);
    if (chosen.length === 0) return;
    const rejected = chosen.filter((file) => !ACCEPTED_EXTENSIONS.test(file.name));
    const accepted = chosen.filter((file) => ACCEPTED_EXTENSIONS.test(file.name));
    setLocalError(
      rejected.length > 0
        ? `Arquivo(s) não suportado(s) (use JPG, PNG ou WebP): ${rejected.map((f) => f.name).join(", ")}`
        : null,
    );
    if (accepted.length === 0) return;
    const slots: NewPhotoSlot[] = accepted.map((file) => {
      const previewUrl = URL.createObjectURL(file);
      objectUrls.current.push(previewUrl);
      newKeyCounter.current += 1;
      return { kind: "new", key: `new-${newKeyCounter.current}`, file, previewUrl };
    });
    commit([...photos, ...slots]);
    setAnnouncement(
      accepted.length === 1 ? "1 foto adicionada ao fim da grade." : `${accepted.length} fotos adicionadas ao fim da grade.`,
    );
  }

  function removeAt(index: number) {
    const slot = photos[index];
    const photosNext = photos.filter((_, i) => i !== index);
    if (slot.kind === "existing") {
      commit(photosNext, [...removed, { id: slot.id, url: slot.url }]);
      setAnnouncement("Foto marcada para remoção. Dá para desfazer antes de salvar.");
      return;
    }
    URL.revokeObjectURL(slot.previewUrl);
    objectUrls.current = objectUrls.current.filter((url) => url !== slot.previewUrl);
    commit(photosNext);
    setAnnouncement("Foto nova descartada.");
  }

  function restore(photoId: number) {
    const target = removed.find((r) => r.id === photoId);
    if (!target) return;
    const slot: ExistingPhotoSlot = {
      kind: "existing",
      key: `img-${target.id}`,
      id: target.id,
      url: target.url,
    };
    commit([...photos, slot], removed.filter((r) => r.id !== photoId));
    setAnnouncement("Remoção desfeita — a foto voltou para o fim da grade.");
  }

  /**
   * Mede as células da grade UMA vez, quando o arraste começa.
   *
   * As posições das células não mudam durante o arraste (a grade tem sempre o mesmo número de
   * espaços) — o que muda é qual foto ocupa cada uma. Perguntar "que célula está sob o ponteiro"
   * a esta régua fixa é o que mantém a reordenação estável: o `onDrag` do Framer dispara a cada
   * quadro, e medir as vizinhas ao vivo leria caixas no meio da animação de troca, fazendo a
   * foto oscilar entre dois lugares.
   */
  function snapshotCells() {
    const cells = Array.from(gridRef.current?.children ?? []).slice(0, photos.length);
    cellBoxes.current = cells.map((cell) => {
      const box = cell.getBoundingClientRect();
      return {
        left: box.left + window.scrollX,
        top: box.top + window.scrollY,
        right: box.right + window.scrollX,
        bottom: box.bottom + window.scrollY,
      };
    });
  }

  /** Reordena ao vivo por baixo do ponteiro e avisa o painel de personagens sobre o alvo. */
  function handleDrag(
    event: MouseEvent | TouchEvent | globalThis.PointerEvent,
    info: PanInfo,
    slot: PhotoSlot,
  ) {
    const point = viewportPoint(event, info);
    // Só foto já salva tem id no servidor; a nova ainda não existe para ser adotada.
    const character =
      slot.kind === "existing" ? attributeAtPoint(CATALOG_CHARACTER_DROP_ATTR, point.x, point.y) : null;
    onCharacterHoverChange?.(character === null ? null : Number(character));
    if (character !== null) return;
    // `info.point` é coordenada de página — a mesma régua das caixas medidas em `snapshotCells`.
    const to = cellBoxes.current.findIndex(
      (box) =>
        info.point.x >= box.left &&
        info.point.x <= box.right &&
        info.point.y >= box.top &&
        info.point.y <= box.bottom,
    );
    const from = photos.findIndex((p) => p.key === slot.key);
    if (to < 0 || from < 0 || to === from) return;
    commit(moveSlot(photos, from, to));
  }

  function handleDragEnd(event: MouseEvent | TouchEvent | globalThis.PointerEvent, info: PanInfo, slot: PhotoSlot) {
    const point = viewportPoint(event, info);
    const characterId =
      slot.kind === "existing" && onDropOnCharacter
        ? attributeAtPoint(CATALOG_CHARACTER_DROP_ATTR, point.x, point.y)
        : null;
    setDraggingKey(null);
    onCharacterHoverChange?.(null);
    if (characterId !== null && slot.kind === "existing") {
      onDropOnCharacter?.(Number(characterId), slot.id);
    } else {
      setAnnouncement(`Foto na posição ${photos.findIndex((p) => p.key === slot.key) + 1} de ${photos.length}.`);
    }
  }

  /** Arrastar arquivos do desktop para dentro da grade (evento nativo, não é o arraste do card). */
  function handleFileDragOver(event: DragEvent<HTMLDivElement>) {
    if (!event.dataTransfer.types.includes("Files")) return;
    event.preventDefault();
    setFileDropActive(true);
  }

  function handleFileDrop(event: DragEvent<HTMLDivElement>) {
    if (!event.dataTransfer.types.includes("Files")) return;
    event.preventDefault();
    setFileDropActive(false);
    addFiles(event.dataTransfer.files);
  }

  /** Impede que o clique num botão da barra de ações vire o começo de um arraste. */
  function stopDragStart(event: PointerEvent) {
    event.stopPropagation();
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-muted">
          A <strong className="font-semibold text-ink">primeira foto é a capa</strong> da vitrine.
          Arraste para reordenar — ou use ‹ › em cada foto.
        </p>
        {hasUnsavedChanges && <Badge tone="gold">alterações não salvas</Badge>}
      </div>

      {(error || localError) && (
        <p className="text-xs text-red" role="alert">
          {error ?? localError}
        </p>
      )}

      <div
        className={cn(
          "rounded-lg border border-dashed p-2 transition-colors",
          fileDropActive ? "border-accent bg-accent-soft" : "border-transparent",
        )}
        onDragOver={handleFileDragOver}
        onDragLeave={() => setFileDropActive(false)}
        onDrop={handleFileDrop}
      >
        <ul
          ref={gridRef}
          className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5"
          // Enquanto um card está sendo arrastado o dedo não pode rolar a página junto, senão
          // no toque o gesto vira rolagem e a foto nunca sai do lugar.
          style={draggingKey ? { touchAction: "none" } : undefined}
        >
          <AnimatePresence initial={false} mode="popLayout">
            {photos.map((slot, index) => (
              <motion.li
                key={slot.key}
                layout={!reduceMotion}
                transition={MOVE_TRANSITION}
                exit={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.9 }}
                drag
                dragSnapToOrigin
                dragElastic={0.08}
                dragMomentum={false}
                whileDrag={{ scale: 1.05, zIndex: 30, boxShadow: "0 14px 32px rgb(0 0 0 / 0.32)" }}
                onDragStart={() => {
                  snapshotCells();
                  setDraggingKey(slot.key);
                }}
                onDrag={(event, info) => handleDrag(event, info, slot)}
                onDragEnd={(event, info) => handleDragEnd(event, info, slot)}
                data-catalog-photo-slot={index}
                // `pointer-events: none` no card que está sendo arrastado é o que faz o
                // hit-test funcionar: ele vai por cima de tudo (`whileDrag` sobe o z-index),
                // então sem isso `elementsFromPoint` devolveria SEMPRE ele mesmo e o alvo
                // debaixo do ponteiro (outra foto, ou um personagem) nunca seria encontrado.
                // O gesto continua vivo porque o Framer escuta o ponteiro na `window`.
                style={draggingKey === slot.key ? { pointerEvents: "none" } : undefined}
                className={cn("group relative", draggingKey === slot.key && "cursor-grabbing")}
              >
                <div
                  className={cn(
                    "relative aspect-square cursor-grab select-none overflow-hidden rounded-lg border bg-surface-2 active:cursor-grabbing",
                    index === 0 ? "border-gold ring-1 ring-gold" : "border-line",
                  )}
                >
                  <img
                    src={slot.kind === "existing" ? assetUrl(slot.url) : slot.previewUrl}
                    alt=""
                    draggable={false}
                    className="pointer-events-none h-full w-full object-cover"
                  />

                  {/* Selo de ordem. Preto/branco fixos (e não os tokens de tema): o fundo aqui é
                      a foto do cliente, que não muda com o tema claro/escuro. */}
                  {index === 0 ? (
                    <span className="absolute left-1.5 top-1.5 inline-flex items-center gap-1 rounded-full bg-gold px-2 py-0.5 text-[10px] font-bold text-on-gold shadow-sm">
                      <Star className="h-3 w-3 fill-current" aria-hidden="true" />
                      CAPA
                    </span>
                  ) : (
                    <span className="absolute left-1.5 top-1.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-black/60 px-1.5 text-[10px] font-bold text-white">
                      {index + 1}
                    </span>
                  )}
                  {slot.kind === "new" && (
                    <span className="absolute right-1.5 top-1.5 rounded-full bg-accent px-2 py-0.5 text-[10px] font-bold text-on-color">
                      nova
                    </span>
                  )}

                  {/* Barra de ações: invisível até o mouse/foco chegar, sempre visível no toque
                      (onde não existe hover) e escondida em todas as fotos durante um arraste —
                      senão ela acende na foto que estiver passando por baixo do card. */}
                  <div
                    className={cn(
                      "absolute inset-x-0 bottom-0 flex items-center justify-center gap-1 bg-gradient-to-t from-black/75 to-transparent px-1 pb-1.5 pt-6 transition-opacity duration-200",
                      draggingKey
                        ? "opacity-0"
                        : "opacity-100 sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100",
                    )}
                  >
                    <PhotoAction
                      label={`Mover a foto ${index + 1} para trás`}
                      disabled={index === 0}
                      onPointerDown={stopDragStart}
                      onClick={() => move(index, index - 1)}
                    >
                      <ChevronLeft className="h-4 w-4" aria-hidden="true" />
                    </PhotoAction>
                    <PhotoAction
                      label={`Mover a foto ${index + 1} para a frente`}
                      disabled={index === photos.length - 1}
                      onPointerDown={stopDragStart}
                      onClick={() => move(index, index + 1)}
                    >
                      <ChevronRight className="h-4 w-4" aria-hidden="true" />
                    </PhotoAction>
                    <PhotoAction
                      label={`Tornar a foto ${index + 1} a capa`}
                      disabled={index === 0}
                      onPointerDown={stopDragStart}
                      onClick={() => move(index, 0)}
                    >
                      <Star className="h-4 w-4" aria-hidden="true" />
                    </PhotoAction>
                    <PhotoAction
                      label={`Remover a foto ${index + 1}`}
                      tone="danger"
                      onPointerDown={stopDragStart}
                      onClick={() => removeAt(index)}
                    >
                      <X className="h-4 w-4" aria-hidden="true" />
                    </PhotoAction>
                  </div>
                </div>
              </motion.li>
            ))}

            <motion.li key="add-tile" layout={!reduceMotion} transition={MOVE_TRANSITION}>
              <label
                htmlFor={inputId}
                className="flex aspect-square cursor-pointer flex-col items-center justify-center gap-1.5 rounded-lg border-2 border-dashed border-line text-muted transition-colors hover:border-accent hover:bg-accent-soft hover:text-accent focus-within:border-accent"
              >
                <ImagePlus className="h-6 w-6" aria-hidden="true" />
                <span className="px-2 text-center text-xs font-medium">
                  {photos.length === 0 ? "Escolher fotos" : "Adicionar fotos"}
                </span>
                <span className="px-2 text-center text-[10px]">ou arraste arquivos aqui</span>
              </label>
            </motion.li>
          </AnimatePresence>
        </ul>
      </div>

      <input
        ref={inputRef}
        id={inputId}
        type="file"
        multiple
        accept="image/jpeg,image/png,image/webp"
        className="sr-only"
        onChange={(event) => {
          addFiles(event.target.files);
          // Zera o input para que escolher o MESMO arquivo de novo dispare `change` outra vez.
          if (inputRef.current) inputRef.current.value = "";
        }}
      />

      {removed.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 rounded-md border border-line bg-red-soft px-2 py-2">
          <span className="text-xs font-medium text-red">
            {removed.length === 1
              ? "1 foto será removida ao salvar:"
              : `${removed.length} fotos serão removidas ao salvar:`}
          </span>
          {removed.map((photo) => (
            <button
              key={photo.id}
              type="button"
              className="group relative h-9 w-9 overflow-hidden rounded border border-line"
              onClick={() => restore(photo.id)}
              aria-label="Desfazer a remoção desta foto"
              title="Desfazer a remoção desta foto"
            >
              <img src={assetUrl(photo.url)} alt="" className="h-full w-full object-cover opacity-50" />
              <span className="absolute inset-0 flex items-center justify-center bg-black/40 text-white">
                <Undo2 className="h-4 w-4" aria-hidden="true" />
              </span>
            </button>
          ))}
        </div>
      )}

      <p className="sr-only" role="status" aria-live="polite">
        {announcement}
      </p>
    </div>
  );
}

/** Botão redondo da barra de ações sobre a foto — alvo de 28px, contraste sobre a imagem. */
function PhotoAction({
  label,
  disabled = false,
  tone = "default",
  onPointerDown,
  onClick,
  children,
}: {
  label: string;
  disabled?: boolean;
  tone?: "default" | "danger";
  onPointerDown: (event: PointerEvent) => void;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onPointerDown={onPointerDown}
      onClick={onClick}
      className={cn(
        "inline-flex h-7 w-7 items-center justify-center rounded-md text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white disabled:opacity-30",
        tone === "danger" ? "bg-black/55 hover:bg-red" : "bg-black/55 hover:bg-black/85",
      )}
    >
      {children}
    </button>
  );
}
