import type { Config } from "tailwindcss";

// Preset global do design system Manto (feature 173) — fonte única dos tokens do painel
// interno, promovidos de apps/internal/tailwind.config.ts (que por sua vez portou
// app/static/style.css :root). Valores de sidebar/fundo atualizados conforme a spec da
// FASE A (Manto Dark Purple #1f1a30, fundo neutro #f4f5f7).
//
// ATENÇÃO: apps/public NÃO consome este preset — o catálogo público tem identidade
// própria (paleta creme/dourada) com os MESMOS nomes de token; aplicar o preset lá
// mudaria o visual do catálogo (ver research.md §2 da feature 173).
const mantoPreset: Partial<Config> = {
  theme: {
    extend: {
      colors: {
        bg: "#f4f5f7",
        panel: "#ffffff",
        ink: "#1a1a1a",
        // `muted` era #6b6b6b: 4.56:1 sobre `surface-2`, ou seja passava AA raspando e
        // justamente onde mais aparece (cabeçalho da grade da agenda, a 11–12px). #57575e
        // é o mesmo cinza levemente frio, agora com 6.13:1 sobre surface-2 e 7.17:1 sobre
        // panel — continua nitidamente secundário ao `ink` (17.4:1), sem virar preto.
        muted: "#57575e",
        line: "#e5e3ef",
        // `line` (1.27:1 sobre panel) é divisória DECORATIVA. Quando a borda é a única
        // estrutura que o olho tem (grade do calendário, moldura de input/botão outline),
        // a WCAG 1.4.11 exige 3:1 — daí `line-strong`, roxo dessaturado da família do
        // accent: 3.68:1 sobre panel e 3.15:1 sobre surface-2.
        "line-strong": "#8b7fa8",
        surface: "#f4f5f7",
        "surface-2": "#eeecf5",
        accent: {
          DEFAULT: "#544596",
          dark: "#3c316b",
          soft: "rgba(84,69,150,0.10)",
        },
        // O anel translúcido antigo (alpha 0.30) compunha #ccc7e0 = 1.64:1 sobre branco:
        // navegando por teclado não dava para saber onde se estava. Roxo sólido dá 7.87:1;
        // o `ring-offset` nas classes base de Button/Input mantém o desenho leve.
        ring: "#544596",
        // green/blue DEFAULT escurecidos um degrau: no fundo `soft` da própria família
        // (chips de categoria da agenda, Badge) o par antigo dava 4.08:1 e 4.24:1 — abaixo
        // de AA a 11px. Mesma leitura de marca, agora 5.70:1 e 5.49:1.
        green: { DEFAULT: "#12662f", soft: "#d4edda" },
        red: { DEFAULT: "#c0392b", soft: "#fde8e8" },
        blue: { DEFAULT: "#1d4ed8", soft: "#dbeafe" },
        // `gold` é a cor de atenção/futuro do design system — usamos ela no lugar de
        // `amber` (a paleta padrão do Tailwind não combina com o dourado da marca).
        // Os degraus 50/100/500/600 existem para dar a `gold` o mesmo vocabulário
        // numérico de `green`/`blue`/`red` (fundos sutis + bordas vivas), sem mexer em
        // `DEFAULT`/`soft`, que continuam sendo os tokens usados nas telas atuais.
        gold: {
          50: "#fbf6f0",
          100: "#f2e4d2",
          500: "#b1793a",
          600: "#96632d",
          DEFAULT: "#b1793a",
          soft: "rgba(177,121,58,0.12)",
          // `DEFAULT` sobre `soft` dava 3.25:1 — a pior reprovação de texto do sistema.
          // `ink` é o degrau EXCLUSIVO de texto sobre fundo dourado (5.15:1 sobre soft,
          // 5.88:1 sobre panel, 4.70:1 sobre gold-100); `DEFAULT` fica para preenchimento
          // gráfico (estrelas, barras, bordas), onde 3:1 basta.
          ink: "#8a5a28",
        },
        sidebar: {
          bg: "#1f1a30",
          accent: "#f7d897",
        },
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "14px",
        xl: "20px",
      },
      boxShadow: {
        sm: "0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)",
        md: "0 4px 14px rgba(0,0,0,0.07), 0 2px 6px rgba(0,0,0,0.04)",
        lg: "0 12px 32px rgba(0,0,0,0.10), 0 4px 10px rgba(0,0,0,0.05)",
      },
    },
  },
};

export default mantoPreset;
