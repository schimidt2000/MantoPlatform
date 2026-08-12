import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { MoreVertical } from "lucide-react";

export interface KebabMenuItem {
  label: string;
  onClick: () => void;
  /** Estilo de alerta (ex.: Excluir) — mesmo padrão de cor usado no resto do app (Princípio V). */
  destructive?: boolean;
  /** Ação indisponível no momento; `title` explica o porquê ao passar o mouse. */
  disabled?: boolean;
  title?: string;
}

interface KebabMenuProps {
  items: KebabMenuItem[];
  label?: string;
  /**
   * Texto do gatilho. Sem ele, o gatilho é o ícone de 3 pontos (uso original em listas);
   * com ele, vira um botão rotulado — o menu "⋯ Ferramentas" do detalhe do evento
   * (feature 190) usa esta forma em vez de um segundo componente de dropdown (Princípio I).
   */
  triggerLabel?: string;
}

/**
 * Painel flutuante do menu. `z-30` é a camada de popover do app (a mesma do `Combobox` de
 * `@manto/ui`) e não pode cair para `z-20`: nesse degrau ele EMPATA com o cromo fixo das
 * páginas — a régua de abas do detalhe do evento é `sticky z-20` — e empate de z-index se
 * decide por ordem no DOM, que a régua vence por vir depois. O sintoma era uma faixa de 62px
 * do menu embaçada pelo `backdrop-blur` da régua. Abaixo de diálogo (z-40/z-50), que cobre tudo.
 *
 * Subir para `z-50` **não** é a saída para o painel que passa da área de conteúdo: ele ficaria
 * legível, mas flutuando por cima da navegação. O lado de abertura é que tem de virar — ver
 * `useLayoutEffect` abaixo.
 */
const PAINEL_CLASSES =
  "absolute z-30 mt-1 min-w-[13rem] rounded-md border border-line bg-panel py-1 shadow-md";

/**
 * Menu de 3 pontos genérico (feature 186, US4) — não existe `DropdownMenu` em `@manto/ui` ainda;
 * implementação enxuta própria, no mesmo espírito de `FilterDropdown` já existente
 * (research.md §7). Fecha ao clicar fora ou Esc.
 */
export function KebabMenu({ items, label = "Mais ações", triggerLabel }: KebabMenuProps) {
  const [open, setOpen] = useState(false);
  // Ancorado à direita por padrão (o uso original é o kebab na última coluna de uma tabela, que
  // tem de crescer para dentro da tela). Vira para a esquerda quando não cabe — ver abaixo.
  const [ancoraDireita, setAncoraDireita] = useState(true);
  const rootRef = useRef<HTMLDivElement>(null);
  const painelRef = useRef<HTMLUListElement>(null);
  const menuId = useId();

  /**
   * Escolhe o lado da abertura medindo o espaço real.
   *
   * Ancorado à direita, o painel cresce para a ESQUERDA. Quando o gatilho está perto do começo
   * do conteúdo, isso o joga para trás da barra lateral — que é `fixed z-40` contra os `z-30`
   * daqui, então o pedaço que passa não sai da tela: some, e o texto aparece cortado no meio da
   * palavra. Foi o que aconteceu com "⋯ Ferramentas" do detalhe do evento: em telas onde o
   * cabeçalho quebra a linha, o botão vai para o início da linha e 61px do menu sumiam. Em tela
   * larga o cabeçalho não quebra, o botão fica à direita e nada disso aparece — daí o bug só
   * existir "na tela dos outros".
   *
   * O limite não é a borda da janela: é a borda da área de conteúdo (`<main>`, que o AppLayout
   * empurra com `lg:pl-64`). Ler do DOM em vez de repetir os 256px evita que isto e o layout
   * saiam de sincronia.
   *
   * `useLayoutEffect` (e não `useEffect`) porque a troca precisa acontecer antes da pintura;
   * senão o menu aparece do lado errado por um quadro e pula.
   */
  useLayoutEffect(() => {
    if (!open) return;
    const raiz = rootRef.current;
    const painel = painelRef.current;
    if (!raiz || !painel) return;

    const gatilho = raiz.getBoundingClientRect();
    const largura = painel.offsetWidth;
    const limiteEsquerdo = raiz.closest("main")?.getBoundingClientRect().left ?? 0;
    const limiteDireito = document.documentElement.clientWidth;

    const cabeAEsquerda = gatilho.right - largura >= limiteEsquerdo;
    const cabeADireita = gatilho.left + largura <= limiteDireito;
    // Sem espaço dos dois lados, fica no padrão: encolher o menu esconderia item, e no maior
    // menu do app (10 itens) o que se perde à esquerda é sempre menos do que à direita.
    setAncoraDireita(cabeAEsquerda || !cabeADireita);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function handleClick(event: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        aria-label={label}
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen((o) => !o)}
        className={
          triggerLabel
            ? "flex h-9 items-center gap-1.5 rounded-md border border-line px-3 text-sm text-ink hover:bg-surface-2"
            : "flex h-8 w-8 items-center justify-center rounded-md text-muted hover:bg-surface-2 hover:text-ink"
        }
      >
        <MoreVertical className="h-4 w-4" aria-hidden="true" />
        {triggerLabel}
      </button>
      {open && (
        <ul
          ref={painelRef}
          id={menuId}
          role="menu"
          className={`${PAINEL_CLASSES} ${ancoraDireita ? "right-0" : "left-0"}`}
        >
          {items.map((item) => (
            <li key={item.label} role="none">
              <button
                type="button"
                role="menuitem"
                disabled={item.disabled}
                title={item.title}
                onClick={() => {
                  setOpen(false);
                  item.onClick();
                }}
                className={`block w-full px-3 py-2 text-left text-sm hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-45 disabled:hover:bg-transparent ${
                  item.destructive ? "text-red" : "text-ink"
                }`}
              >
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
