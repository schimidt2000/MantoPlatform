import { assetUrl } from "@manto/api-client";
import { Foto, cn } from "@manto/ui";
import type { FotoDoPersonagem } from "../../lib/catalogoConferencia";

/** Caixa em que o recorte tem de caber: estreita o bastante para sobrar espaço aos campos a 390 px. */
const LARGURA_MAX = 112;
const ALTURA_MAX = 190;

interface RecortePersonagemProps {
  foto: FotoDoPersonagem | null;
  nome: string;
  /** Esmaece o recorte: o personagem não será criado, ou será criado sem esta foto. */
  apagado?: boolean;
  /** Abre a foto original inteira, para comparar com o recorte. */
  onAbrir?: () => void;
}

function SemFoto() {
  return (
    <div className="flex h-28 w-28 shrink-0 items-center justify-center self-start rounded-md border border-dashed border-line bg-surface-2 text-xs text-muted">
      Sem foto
    </div>
  );
}

/**
 * O recorte que a leitura propôs para um personagem, mostrado a partir da foto original.
 *
 * Não existe arquivo recortado: a leitura guardou só a geometria (`[x, y, largura, altura]` em % da
 * foto). A moldura tem a proporção do recorte e a foto inteira é posicionada por dentro dela. Os
 * `style` abaixo são a única forma de aplicar números que vêm do dado — mesmo caso da linha do
 * tempo da agenda e das barras de progresso.
 */
export function RecortePersonagem({ foto, nome, apagado = false, onAbrir }: RecortePersonagemProps) {
  if (!foto || foto.recorte.length !== 4) return <SemFoto />;
  const [x, y, largura, altura] = foto.recorte;
  if (!foto.largura || !foto.altura || largura <= 0 || altura <= 0) return <SemFoto />;

  const proporcao = (largura * foto.largura) / (altura * foto.altura);
  const larguraPx = Math.round(Math.min(LARGURA_MAX, ALTURA_MAX * proporcao));
  return (
    <button
      type="button"
      onClick={onAbrir}
      aria-label={`Ver a foto original de ${nome}`}
      className={cn(
        // `self-start`: num flex em linha o item estica até a altura do cartão, a moldura perde a
        // proporção do recorte e o deslocamento (que é % da altura) aponta para o lugar errado.
        "relative shrink-0 self-start overflow-hidden rounded-md border border-line bg-surface-2 transition-opacity",
        apagado && "opacity-40",
      )}
      style={{ width: larguraPx, aspectRatio: String(proporcao) }}
    >
      <div
        className="absolute"
        style={{
          width: `${(100 / largura) * 100}%`,
          left: `${-(x / largura) * 100}%`,
          top: `${-(y / altura) * 100}%`,
        }}
      >
        <Foto
          src={assetUrl(foto.url)}
          alt={`Recorte de ${nome}`}
          loading="lazy"
          className="block h-auto w-full max-w-none"
          fallback={<span className="block p-2 text-xs text-muted">Foto indisponível</span>}
        />
      </div>
    </button>
  );
}
