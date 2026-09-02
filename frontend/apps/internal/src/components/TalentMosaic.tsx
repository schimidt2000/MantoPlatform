import { Link } from "react-router-dom";
import { Button } from "@manto/ui";
import { assetSrcSet, assetUrl } from "@manto/api-client";
import {
  useApproveTalent,
  useRejectTalent,
  type TalentSummary,
} from "../lib/talents";

const WARNING_COLORS: Record<string, string> = {
  leve: "bg-gold",
  moderado: "bg-blue",
  grave: "bg-red",
};

function measureBadges(talent: TalentSummary): string[] {
  return [
    talent.height_cm ? `${talent.height_cm}cm` : null,
    talent.clothing_size_top,
    talent.shoe_size ? `Calçado ${talent.shoe_size}` : null,
  ].filter((v): v is string => Boolean(v));
}

function MosaicCard({ talent, isPending }: { talent: TalentSummary; isPending: boolean }) {
  const approve = useApproveTalent();
  const reject = useRejectTalent();
  const badges = measureBadges(talent);

  return (
    <div className="overflow-hidden rounded-lg border border-line bg-panel shadow-sm">
      <Link to={`/talents/${talent.id}`} className="group relative block aspect-[3/4] bg-surface-2">
        {talent.photo_face_path ? (
          <img
            // Grade `2 / sm 3 / md 4 / xl 5 / 2xl 6` colunas (abaixo): o card tem ~200-270px, e
            // baixar a foto de rosto inteira para isso era ~6× de área jogada fora (feature 270).
            src={assetUrl(talent.photo_face_path, { largura: 640 })}
            srcSet={assetSrcSet(talent.photo_face_path, [320, 480, 640])}
            sizes="(min-width: 1536px) 16vw, (min-width: 1280px) 20vw, (min-width: 768px) 25vw, (min-width: 640px) 33vw, calc(50vw - 30px)"
            alt={talent.full_name}
            loading="lazy"
            className="h-full w-full object-cover transition-transform group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-4xl text-muted">👤</div>
        )}
        {talent.warning_level && (
          <span
            className={`absolute right-2 top-2 h-3 w-3 rounded-full ring-2 ring-white ${WARNING_COLORS[talent.warning_level] ?? "bg-muted"}`}
            title={`Alerta: ${talent.warning_level}`}
          />
        )}
        {/* O branco e o degradê preto daqui NÃO devem virar token: o fundo é a FOTO do talento,
            que não muda com o tema. Um texto que invertesse no escuro ficaria preto sobre um
            degradê preto. */}
        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent p-2 pt-6">
          <div className="truncate text-sm font-medium text-white">{talent.full_name}</div>
          {badges.length > 0 && (
            <div className="mt-0.5 truncate text-xs text-white/85">{badges.join(" • ")}</div>
          )}
        </div>
      </Link>
      {isPending && (
        <div className="flex gap-1.5 p-1.5">
          <Button
            size="sm"
            className="flex-1"
            loading={approve.isPending}
            onClick={() => approve.mutate(talent.id)}
          >
            ✓ Aprovar
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            loading={reject.isPending}
            onClick={() => {
              if (window.confirm(`Rejeitar o cadastro de "${talent.full_name}"? Isso exclui o registro.`)) {
                reject.mutate(talent.id);
              }
            }}
          >
            Rejeitar
          </Button>
        </div>
      )}
    </div>
  );
}

export interface TalentMosaicProps {
  talents: TalentSummary[];
  isPending: boolean;
}

/** Mosaico de fotos grandes do Banco de Talentos — feature 174 (substitui o card horizontal). */
export function TalentMosaic({ talents, isPending }: TalentMosaicProps) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6">
      {talents.map((t) => (
        <MosaicCard key={t.id} talent={t} isPending={isPending} />
      ))}
    </div>
  );
}
