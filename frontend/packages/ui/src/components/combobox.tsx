import {
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ChevronDown, Loader2, X } from "lucide-react";
import { cn } from "../lib/cn";
import { AvatarThumb, type AvatarThumbShape } from "./avatar-thumb";

export interface ComboboxOption {
  /** Identificador estável da opção — é o que volta em `onChange`. */
  value: string;
  /** Texto principal exibido na lista e no campo depois de selecionado. */
  label: string;
  /** Linha secundária opcional (ex.: telefone do cliente, nome do Tema do personagem). */
  description?: string | null;
  /** URL já resolvida da miniatura (use `assetUrl()` antes de passar). */
  imageUrl?: string | null;
  /** Circular para pessoas, quadrado para figurinos/personagens. */
  imageShape?: AvatarThumbShape;
  /** Placeholder alternativo às iniciais quando não há foto (ex.: `🎭`). */
  fallbackIcon?: ReactNode;
  /**
   * Selo à direita da opção (feature 215) — o estado que precisa ser visto ANTES de escolher,
   * não depois: um talento com evento no mesmo dia, uma ficha já usada. Some quando ausente.
   */
  badge?: ReactNode;
  disabled?: boolean;
}

export interface ComboboxProps {
  options: ComboboxOption[];
  /** Valor selecionado (`option.value`); em `freeSolo`, é o próprio texto digitado. */
  value: string | null;
  /** Recebe o novo valor e a opção correspondente (`null` se o usuário digitou texto livre). */
  onChange: (value: string | null, option: ComboboxOption | null) => void;
  /**
   * Informe para assumir a busca (ex.: fetch remoto). Quando presente, o componente NÃO filtra
   * `options` — a lista recebida já é o resultado. Sem ele, o filtro é local, ignorando acentos.
   */
  onQueryChange?: (query: string) => void;
  /**
   * Observa o texto digitado SEM assumir a busca — o filtro local continua ativo. Existe para
   * quem precisa do termo por fora (ex.: "Solicitar ficha" pré-preenchido, feature 237).
   */
  onInputValueChange?: (text: string) => void;
  /** Exibe spinner e mensagem "Buscando…" enquanto a requisição está em voo (Princípio V). */
  loading?: boolean;
  placeholder?: string;
  emptyMessage?: string;
  /** Dica exibida antes de o usuário digitar o suficiente (ex.: "Digite ao menos 3 letras"). */
  hintMessage?: string;
  disabled?: boolean;
  /** Mostra o "✕" para limpar a seleção. */
  clearable?: boolean;
  /** Marca o campo como inválido (borda vermelha + `aria-invalid`). */
  invalid?: boolean;
  /**
   * Texto livre: o valor é o que o usuário digitou e as opções são apenas sugestões — usado por
   * endereços, onde nem todo destino existe no Google.
   */
  freeSolo?: boolean;
  /** Teto de opções renderizadas no modo de filtro local. */
  maxVisible?: number;
  id?: string;
  name?: string;
  "aria-label"?: string;
  className?: string;
}

/** Marcas de acento decompostas pelo `normalize("NFD")` (bloco Unicode Combining Diacriticals). */
const DIACRITICS = new RegExp("[\\u0300-\\u036f]", "g");

/** Remove acentos e caixa para o filtro local — "José" casa com "jose". */
function normalize(text: string): string {
  return text.normalize("NFD").replace(DIACRITICS, "").toLowerCase();
}

/**
 * Campo de seleção pesquisável com miniatura (feature 195, Princípio X.1/X.2).
 *
 * Substitui `<select>` nativo em qualquer lista que possa passar de 10 itens: o usuário digita
 * para filtrar em tempo real, navega com as setas, confirma com Enter e vê a foto de cada opção
 * (circular para pessoas, quadrada para figurinos) — ou um placeholder de iniciais quando não há
 * foto salva. Funciona com filtro local ou com busca remota (`onQueryChange` + `loading`).
 */
export function Combobox({
  options,
  value,
  onChange,
  onQueryChange,
  onInputValueChange,
  loading = false,
  placeholder = "Buscar…",
  emptyMessage = "Nenhum resultado encontrado.",
  hintMessage,
  disabled = false,
  clearable = true,
  invalid = false,
  freeSolo = false,
  maxVisible = 30,
  id,
  name,
  "aria-label": ariaLabel,
  className,
}: ComboboxProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const activeItemRef = useRef<HTMLLIElement | null>(null);
  const listId = useId();
  const reduceMotion = useReducedMotion();

  const selected = useMemo(
    () => (freeSolo ? null : (options.find((o) => o.value === value) ?? null)),
    [options, value, freeSolo],
  );

  const visible = useMemo(() => {
    if (onQueryChange) return options.slice(0, maxVisible);
    const term = normalize(query.trim());
    if (!term) return options.slice(0, maxVisible);
    return options
      .filter(
        (o) =>
          normalize(o.label).includes(term) ||
          (o.description ? normalize(o.description).includes(term) : false),
      )
      .slice(0, maxVisible);
  }, [options, query, onQueryChange, maxVisible]);

  // Fecha ao clicar fora — mesmo padrão do `FilterDropdown` do design system.
  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [open]);

  // Reset em duas etapas para não depender da identidade do array `options` (que o chamador pode
  // recriar a cada render): a busca volta ao topo, e a lista encolhendo só reancora o destaque.
  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  useEffect(() => {
    setActiveIndex((i) => (i >= visible.length ? 0 : i));
  }, [visible.length]);

  useEffect(() => {
    if (open) activeItemRef.current?.scrollIntoView({ block: "nearest" });
  }, [activeIndex, open]);

  const updateQuery = useCallback(
    (text: string) => {
      setQuery(text);
      onQueryChange?.(text);
      onInputValueChange?.(text);
      if (freeSolo) onChange(text, null);
    },
    [onQueryChange, onInputValueChange, onChange, freeSolo],
  );

  const openList = useCallback(() => {
    if (disabled) return;
    setOpen(true);
  }, [disabled]);

  const select = useCallback(
    (option: ComboboxOption) => {
      if (option.disabled) return;
      onChange(freeSolo ? option.label : option.value, option);
      setQuery(freeSolo ? option.label : "");
      if (freeSolo) onQueryChange?.(option.label);
      setOpen(false);
      inputRef.current?.blur();
    },
    [onChange, onQueryChange, freeSolo],
  );

  const clear = useCallback(() => {
    onChange(freeSolo ? "" : null, null);
    setQuery("");
    onQueryChange?.("");
    setOpen(false);
  }, [onChange, onQueryChange, freeSolo]);

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!open) {
        openList();
        return;
      }
      if (visible.length === 0) return;
      const delta = e.key === "ArrowDown" ? 1 : -1;
      setActiveIndex((i) => (i + delta + visible.length) % visible.length);
      return;
    }
    if (e.key === "Enter") {
      if (open && visible[activeIndex]) {
        e.preventDefault();
        select(visible[activeIndex]);
      }
      return;
    }
    if (e.key === "Escape") {
      if (open) {
        e.preventDefault();
        setOpen(false);
      }
      return;
    }
    if (e.key === "Tab") setOpen(false);
  }

  // Fora do modo texto livre o campo mostra o rótulo selecionado quando fechado, e o que está
  // sendo digitado quando aberto — o rótulo vira placeholder para não sumir da vista.
  const inputValue = freeSolo ? (value ?? "") : open ? query : (selected?.label ?? "");
  const inputPlaceholder = freeSolo ? placeholder : (selected?.label ?? placeholder);
  const thumb = freeSolo ? null : selected;
  const showClear = clearable && !disabled && Boolean(freeSolo ? value : selected);

  return (
    <div ref={rootRef} className={cn("relative", className)}>
      <div
        className={cn(
          "flex h-11 w-full items-center gap-2 rounded-md border bg-panel pl-3 pr-2 text-sm text-ink",
          "focus-within:ring-2 focus-within:ring-ring",
          invalid ? "border-red ring-red/30" : "border-line",
          disabled && "cursor-not-allowed opacity-60",
        )}
      >
        {thumb && (
          <AvatarThumb
            src={thumb.imageUrl}
            name={thumb.label}
            shape={thumb.imageShape ?? "circle"}
            size="sm"
            fallbackIcon={thumb.fallbackIcon}
          />
        )}
        <input
          ref={inputRef}
          id={id}
          name={name}
          type="text"
          role="combobox"
          autoComplete="off"
          aria-label={ariaLabel}
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-invalid={invalid || undefined}
          aria-activedescendant={open && visible[activeIndex] ? `${listId}-${activeIndex}` : undefined}
          disabled={disabled}
          value={inputValue}
          placeholder={inputPlaceholder}
          onChange={(e) => {
            updateQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={openList}
          onClick={openList}
          onKeyDown={handleKeyDown}
          className={cn(
            "min-w-0 flex-1 bg-transparent py-2 outline-none placeholder:text-muted",
            "disabled:cursor-not-allowed",
          )}
        />
        {loading && <Loader2 className="h-4 w-4 flex-none animate-spin text-muted" aria-hidden="true" />}
        {showClear && !loading && (
          <button
            type="button"
            onClick={clear}
            aria-label="Limpar seleção"
            className="flex h-6 w-6 flex-none items-center justify-center rounded text-muted hover:bg-surface-2 hover:text-ink"
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        )}
        <ChevronDown
          className={cn("h-4 w-4 flex-none text-muted transition-transform", open && "rotate-180")}
          aria-hidden="true"
        />
      </div>

      <AnimatePresence>
        {open && (
          <motion.ul
            id={listId}
            role="listbox"
            initial={reduceMotion ? false : { opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -4 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            className="absolute z-30 mt-1 max-h-72 w-full overflow-y-auto rounded-md border border-line bg-panel py-1 shadow-lg"
          >
            {loading && (
              <li className="flex items-center gap-2 px-3 py-2 text-sm text-muted">
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                Buscando…
              </li>
            )}
            {!loading && visible.length === 0 && (
              <li className="px-3 py-2 text-sm text-muted">{hintMessage ?? emptyMessage}</li>
            )}
            {!loading &&
              visible.map((option, index) => {
                const isActive = index === activeIndex;
                const isSelected = !freeSolo && option.value === value;
                return (
                  <li
                    key={option.value}
                    id={`${listId}-${index}`}
                    role="option"
                    aria-selected={isSelected}
                    ref={isActive ? activeItemRef : undefined}
                  >
                    <button
                      type="button"
                      disabled={option.disabled}
                      // preventDefault evita o input perder o foco antes de o clique registrar
                      onMouseDown={(e) => e.preventDefault()}
                      onMouseEnter={() => setActiveIndex(index)}
                      onClick={() => select(option)}
                      className={cn(
                        "flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm text-ink",
                        "disabled:cursor-not-allowed disabled:opacity-50",
                        isActive && "bg-surface-2",
                        isSelected && "font-semibold",
                      )}
                    >
                      <AvatarThumb
                        src={option.imageUrl}
                        name={option.label}
                        shape={option.imageShape ?? "circle"}
                        size="md"
                        fallbackIcon={option.fallbackIcon}
                      />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate">{option.label}</span>
                        {option.description && (
                          <span className="block truncate text-xs text-muted">{option.description}</span>
                        )}
                      </span>
                      {option.badge && <span className="flex-none">{option.badge}</span>}
                    </button>
                  </li>
                );
              })}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  );
}
