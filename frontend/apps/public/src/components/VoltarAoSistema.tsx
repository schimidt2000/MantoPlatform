import { useState } from "react";
import { useLocation } from "react-router-dom";
import { estaComoAppInstalado } from "@manto/ui";

/** Páginas do catálogo que NÃO são catálogo: loja, cadastro, formulários, avaliação, NFC. */
const FORA_DO_CATALOGO = ["/v", "/cadastro", "/f/", "/avaliar", "/nfc"];

/**
 * "← Voltar ao sistema" (feature 320). Com o sistema aberto como app (ícone na Tela de Início do
 * iPhone), o item "Catálogo" do menu abre o catálogo NA MESMA JANELA — sem barra de navegador, esta
 * faixa é o único caminho de volta. A cliente no navegador comum nunca vê a faixa.
 */
export function VoltarAoSistema() {
  const { pathname } = useLocation();
  // O modo da janela não muda com ela aberta: lê uma vez.
  const [comoApp] = useState(estaComoAppInstalado);
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
          const idx = (window.history.state as { idx?: number } | null)?.idx ?? 0;
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
