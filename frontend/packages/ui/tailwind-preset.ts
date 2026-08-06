import type { Config } from "tailwindcss";

// Preset global do design system Manto (feature 173) — fonte única dos tokens do painel
// interno, promovidos de apps/internal/tailwind.config.ts (que por sua vez portou
// app/static/style.css :root).
//
// Desde o dark mode os VALORES não moram mais aqui: cada token aponta para uma variável CSS
// declarada em `src/theme.css` (dois conjuntos: `:root` claro e `:root.dark` escuro). Os NOMES
// de token são os mesmos de antes, então nenhuma tela precisou trocar de classe.
//
// ATENÇÃO: apps/public NÃO consome este preset — o catálogo público tem identidade
// própria (paleta creme/dourada) com os MESMOS nomes de token; aplicar o preset lá
// mudaria o visual do catálogo (ver research.md §2 da feature 173).

/** Argumentos que o Tailwind passa para um valor de cor em forma de função. */
type ArgsAlfa = { opacityValue?: string; opacityVariable?: string };

/**
 * Token de cor opaco: canal RGB na variável + `<alpha-value>` para o Tailwind injetar o
 * modificador de opacidade (`bg-panel/70`, `border-line/60`) sem perder o tema.
 */
const cor = (token: string): string => `rgb(var(--c-${token}) / <alpha-value>)`;

/**
 * Token que JÁ nasce translúcido (`accent-soft`, `gold-soft`). A opacidade padrão muda de tema
 * (0.10 no claro, 0.16 no escuro), então ela vive numa variável própria `--a-<token>`; um
 * modificador explícito (`bg-gold-soft/40`) continua sobrescrevendo, exatamente como o rgba()
 * fixo fazia antes. O `opacityVariable` distingue os dois casos: o Tailwind só o passa quando
 * NÃO há modificador na classe.
 */
const corTranslucida =
  (token: string) =>
  ({ opacityValue, opacityVariable }: ArgsAlfa): string => {
    const usaPadrao = opacityVariable !== undefined || opacityValue === undefined;
    const alfa = usaPadrao ? `var(--a-${token})` : opacityValue;
    return `rgb(var(--c-${token}) / ${alfa})`;
  };

const cores = {
  bg: cor("bg"),
  panel: cor("panel"),
  ink: cor("ink"),
  muted: cor("muted"),
  line: cor("line"),
  "line-strong": cor("line-strong"),
  surface: cor("surface"),
  "surface-2": cor("surface-2"),
  accent: {
    DEFAULT: cor("accent"),
    dark: cor("accent-dark"),
    soft: corTranslucida("accent-soft"),
  },
  ring: cor("ring"),
  // Tinta que vai SOBRE preenchimento saturado (`bg-accent text-on-color`). Existe porque no
  // tema escuro as matizes clareiam e o branco reprova AA em todas elas — ver theme.css.
  "on-color": cor("on-color"),
  // Tinta sobre o dourado SÓLIDO (`bg-gold text-on-gold`). Separado de `on-color` porque o
  // dourado é a única matiz clara TAMBÉM no tema claro: lá `on-color` é branco e daria 3.71:1.
  "on-gold": cor("on-gold"),
  // O degrau `-50` é fundo de LINHA DE TABELA (mais fraco que `soft`, que é fundo de chip);
  // dá a `green`/`red`/`blue` o mesmo vocabulário que `gold` já tinha.
  green: { DEFAULT: cor("green"), soft: cor("green-soft"), 50: cor("green-50") },
  red: { DEFAULT: cor("red"), soft: cor("red-soft"), 50: cor("red-50") },
  blue: { DEFAULT: cor("blue"), soft: cor("blue-soft"), 50: cor("blue-50") },
  // Moldura escura do player de vídeo — escura nos DOIS temas (o vídeo é que tem que ser a
  // coisa clara da caixa). Sem ela o player usava `bg-ink`, que INVERTE no tema escuro.
  media: cor("media"),
  // `gold` é a cor de atenção/futuro do design system — usamos ela no lugar de `amber` (a
  // paleta padrão do Tailwind não combina com o dourado da marca). Os degraus 50/100/500/600
  // dão a `gold` o mesmo vocabulário numérico de `green`/`blue`/`red`.
  gold: {
    50: cor("gold-50"),
    100: cor("gold-100"),
    500: cor("gold"),
    600: cor("gold-600"),
    DEFAULT: cor("gold"),
    soft: corTranslucida("gold-soft"),
    // Degrau EXCLUSIVO de texto sobre fundo dourado SOFT/50/100; `DEFAULT` fica para
    // preenchimento gráfico (estrelas, barras, bordas), onde 3:1 basta.
    ink: cor("gold-ink"),
  },
  sidebar: {
    // A sidebar é escura NOS DOIS temas — mas por motivos opostos, e isso é uma decisão, não
    // uma herança: no tema claro ela é a âncora escura contra a página clara; no tema escuro
    // repetir o #1f1a30 original a faria sumir (1.14:1 contra o fundo #121016). Então no
    // escuro ela sobe de nível em vez de descer (#2a2438, 1.27:1 ACIMA do fundo), ganha uma
    // costura de 1px (`sidebar-line`) e mantém identidade de "chrome" separada do conteúdo.
    // Clarear até os 3:1 exigiria um cinza ~#5a5170, que viraria uma barra lavada — o oposto
    // do "escuro com cores vivas" pedido.
    bg: cor("sidebar-bg"),
    accent: cor("sidebar-accent"),
    line: cor("sidebar-line"),
  },
};

const mantoPreset: Partial<Config> = {
  // Estratégia de CLASSE (e não `media`): o usuário escolhe o tema no app, e a escolha é
  // carimbada no <html> por um script inline no index.html antes do primeiro paint.
  darkMode: "class",
  theme: {
    extend: {
      // O cast existe porque os tokens translúcidos são FUNÇÕES (contrato oficial do Tailwind
      // para opacidade dinâmica), enquanto o tipo `RecursiveKeyValuePair` só admite string.
      colors: cores as unknown as Record<string, string>,
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "14px",
        xl: "20px",
      },
      // As sombras também trocam de tema: preto a 6% é invisível sobre fundo escuro, e sem
      // elas menu/modal flutuante perde a aresta (panel x bg é só 1.08:1 nos dois temas).
      boxShadow: {
        sm: "var(--sombra-sm)",
        md: "var(--sombra-md)",
        lg: "var(--sombra-lg)",
      },
    },
  },
};

export default mantoPreset;
