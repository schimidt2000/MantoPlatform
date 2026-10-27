import { useState } from "react";
import { useLocation } from "react-router-dom";
import { estaComoAppInstalado } from "@manto/ui";

/** Posição da entrada atual DESTE documento (o React Router grava `idx`; 0 = a primeira). */
function idxAtual(): number {
  return (window.history.state as { idx?: number } | null)?.idx ?? 0;
}

/** Páginas do catálogo que NÃO são catálogo: loja, cadastro, formulários, avaliação, NFC. */
const FORA_DO_CATALOGO = ["/v", "/cadastro", "/f/", "/avaliar", "/nfc"];

/**
 * "← Voltar ao sistema" (feature 320). Com o sistema aberto como app (ícone na Tela de Início do
 * iPhone), o item "Catálogo" do menu abre o catálogo NA MESMA JANELA — sem barra de navegador, esta
 * faixa é o único caminho de volta. A cliente no navegador comum nunca vê a faixa.
 */
export function VoltarAoSistema() {
  const { pathname } = useLocation();
  // O modo da janela não muda com ela aberta: lê uma vez. E só aparece se houver de onde a pessoa
  // veio antes do catálogo — a cliente que salvou o catálogo na Tela de Início abre direto nele
  // (histórico vazio) e não tem "sistema" para voltar.
  const [comoApp] = useState(
    () => estaComoAppInstalado() && window.history.length > idxAtual() + 1,
  );
  if (!comoApp) return null;
  if (FORA_DO_CATALOGO.some((prefixo) => pathname === prefixo || pathname.startsWith(prefixo.endsWith("/") ? prefixo : `${prefixo}/`))) {
    return null;
  }

  return (
    <div className="sticky top-0 z-40 border-b border-line bg-panel/95 px-4 backdrop-blur">
      <button
        type="button"
        onClick={() => {
          // `idx` é a posição que o React Router grava em cada entrada DESTE documento (0 = a
          // página do catálogo que abriu primeiro). Recuar idx + 1 pula tudo o que a pessoa
          // navegou dentro do catálogo e cai na tela do sistema de onde ela veio.
          const idx = idxAtual();
          if (window.history.length > idx + 1) window.history.go(-(idx + 1));
          else window.location.assign("/");
        }}
        className="flex min-h-11 items-center text-sm font-semibold text-accent-dark"
      >
        ← Voltar ao sistema
      </button>
    </div>
  );
}
