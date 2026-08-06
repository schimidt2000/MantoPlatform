import { useCallback, useRef } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Moon, Sun } from "lucide-react";
import { cn } from "../lib/cn";
import { toggleTheme, useTheme } from "../lib/theme";

/** Segundos — 240ms, dentro da faixa de 150–350ms do Princípio IX. */
const DURACAO_MORFAR_S = 0.24;
/** Deslocamento do pino dentro do trilho (w-9 = 36px, pino w-4 = 16px, folga de 2px). */
const PINO_X_LIGADO = 18;
const PINO_X_DESLIGADO = 2;

export interface ThemeSwitchProps {
  /** Classes extras do botão. */
  className?: string;
  /**
   * Superfície onde o switch está apoiado. `escuro` (padrão) usa brancos translúcidos e serve à
   * sidebar, que é escura nos DOIS temas; `claro` usa os tokens semânticos e serve a qualquer
   * painel que inverta com o tema — o header do Portal do Artista, por exemplo.
   */
  tom?: "escuro" | "claro";
  /** Só o ícone, sem rótulo nem trilho — para header apertado (mobile do portal). */
  compacto?: boolean;
}

/** Classes do botão por superfície. Separado para as duas variantes ficarem lado a lado. */
const TOM_CLASSES: Record<"escuro" | "claro", string> = {
  // `white/70` dá 8.75:1 sobre a sidebar nos dois temas, por isso ela não precisa de token.
  escuro:
    "text-white/70 hover:bg-white/5 hover:text-white focus-visible:ring-sidebar-accent focus-visible:ring-offset-sidebar-bg",
  // Tokens semânticos: aqui a superfície inverte junto com o tema, então cor fixa não serve.
  claro:
    "text-muted hover:bg-surface-2 hover:text-ink focus-visible:ring-ring focus-visible:ring-offset-panel",
};

/**
 * Switch de tema claro/escuro com revelar circular a partir do próprio botão.
 *
 * Duas superfícies possíveis via `tom` — ver `TOM_CLASSES`. O padrão `escuro` existe porque o
 * primeiro lugar de uso é o rodapé da sidebar do ERP, que é escura independentemente do tema.
 */
function ThemeSwitch({ className, tom = "escuro", compacto = false }: ThemeSwitchProps) {
  const tema = useTheme();
  const reduzirMovimento = useReducedMotion();
  const botaoRef = useRef<HTMLButtonElement>(null);
  const escuro = tema === "escuro";

  const alternar = useCallback(() => {
    // A origem sai do RETÂNGULO do botão, não do ponteiro: assim o círculo nasce do mesmo lugar
    // quando a troca vem do teclado (Espaço/Enter), onde não há `clientX`/`clientY`.
    const caixa = botaoRef.current?.getBoundingClientRect();
    const origem = caixa
      ? { x: caixa.left + caixa.width / 2, y: caixa.top + caixa.height / 2 }
      : null;
    toggleTheme(origem, reduzirMovimento);
  }, [reduzirMovimento]);

  return (
    <button
      ref={botaoRef}
      type="button"
      role="switch"
      aria-checked={escuro}
      onClick={alternar}
      title={escuro ? "Mudar para o tema claro" : "Mudar para o tema escuro"}
      // `min-h-[44px]` e alvo quadrado no compacto: toque confortável no mobile nos dois casos.
      className={cn(
        "flex min-h-[44px] items-center gap-2.5 rounded-md text-sm font-medium transition-colors",
        compacto ? "w-11 shrink-0 justify-center" : "w-full px-2 py-2",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2",
        TOM_CLASSES[tom],
        className,
      )}
    >
      <span aria-hidden className="relative flex h-4 w-4 shrink-0 items-center justify-center">
        {/* Sol e lua se cruzam girando: os dois ficam absolutos e sobrepostos, então a saída de
            um e a entrada do outro acontecem no MESMO ponto, sem empurrar o rótulo ao lado. */}
        <AnimatePresence initial={false}>
          <motion.span
            key={escuro ? "lua" : "sol"}
            className="absolute inset-0 flex items-center justify-center"
            initial={{ opacity: 0, rotate: reduzirMovimento ? 0 : -90, scale: reduzirMovimento ? 1 : 0.4 }}
            animate={{ opacity: 1, rotate: 0, scale: 1 }}
            exit={{ opacity: 0, rotate: reduzirMovimento ? 0 : 90, scale: reduzirMovimento ? 1 : 0.4 }}
            transition={{ duration: reduzirMovimento ? 0 : DURACAO_MORFAR_S, ease: "easeOut" }}
          >
            {escuro ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
          </motion.span>
        </AnimatePresence>
      </span>

      {!compacto && (
        <>
          <span className="flex-1 text-left">Tema escuro</span>

          <span
            aria-hidden
            className={cn(
              "relative h-5 w-9 shrink-0 rounded-full transition-colors",
              // Ligado usa o acento da própria superfície; desligado, um trilho neutro. No tom
              // claro os brancos não servem: o trilho sumiria contra o painel no tema claro.
              escuro
                ? tom === "escuro"
                  ? "bg-sidebar-accent"
                  : "bg-accent"
                : tom === "escuro"
                  ? "bg-white/25"
                  : "bg-line-strong",
            )}
          >
            <motion.span
              className={cn(
                "absolute top-0.5 h-4 w-4 rounded-full",
                escuro
                  ? tom === "escuro"
                    ? "bg-sidebar-bg"
                    : "bg-on-color"
                  : tom === "escuro"
                    ? "bg-white"
                    : "bg-panel",
              )}
              animate={{ x: escuro ? PINO_X_LIGADO : PINO_X_DESLIGADO }}
              transition={{ duration: reduzirMovimento ? 0 : DURACAO_MORFAR_S, ease: "easeOut" }}
            />
          </span>
        </>
      )}
    </button>
  );
}

export { ThemeSwitch };
