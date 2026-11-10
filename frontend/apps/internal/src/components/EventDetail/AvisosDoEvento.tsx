import { Button } from "@manto/ui";
import { formatBRL } from "@manto/money";
import type { AvisoDoEvento, RoleItem } from "../../lib/agenda";

/** `dd/mm` a partir de um ISO de parede de São Paulo — recorte, nunca `Date` (docs/00 §6 item 1). */
function diaMes(iso: string | null): string {
  if (!iso) return "";
  const [, mes, dia] = iso.slice(0, 10).split("-");
  return dia && mes ? `${dia}/${mes}` : "";
}

/** "em 09/11, por Thays" — sem autor quando a mudança veio do Google Agenda. */
function quandoQuem(aviso: AvisoDoEvento): string {
  const dia = diaMes(aviso.created_at);
  const autor = aviso.dados.autor;
  return `${dia ? ` em ${dia}` : ""}${autor ? `, por ${autor}` : ""}`;
}

function textoDoAviso(aviso: AvisoDoEvento): { titulo: string; texto: string } {
  if (aviso.kind === "evento.vaga_sobrando") {
    const nome = (aviso.dados.personagem ?? "").toUpperCase();
    const vagas = aviso.dados.vagas ?? 0;
    const ocupadas = vagas === 1 ? "1 vaga ocupada" : `${vagas} vagas ocupadas`;
    const pedido = aviso.dados.pedido ?? 0;
    return {
      titulo: "Vaga a mais",
      texto:
        pedido === 0
          ? `${nome} saiu do título do evento, e há ${ocupadas}. Remova da escala quem não vai ` +
            "mais; a vaga que ficar vazia sai sozinha."
          : `${nome}: o título do evento pede ${pedido}, há ${ocupadas}. Remova alguém da ` +
            "escala; a vaga que ficar vazia sai sozinha.",
    };
  }
  if (aviso.dados.entrou === false) {
    return {
      titulo: "O evento deixou de ser SHOW",
      texto:
        `Este evento deixou de ser SHOW${quandoQuem(aviso)}. Os ensaios foram cancelados e o limite ` +
        "de cachê voltou ao valor sem show. Revise os cachês do elenco.",
    };
  }
  return {
    titulo: "O evento virou SHOW",
    texto:
      `Este evento virou SHOW${quandoQuem(aviso)}. Confira com cada artista a disponibilidade para ` +
      "o ensaio e revise os cachês: o limite subiu para o valor de show.",
  };
}

export interface AvisosDoEventoProps {
  avisos: AvisoDoEvento[];
  /** Elenco do payload — já vem com o corte de cachê do papel de quem lê. */
  elenco: RoleItem[];
  onCiente: (id: number) => void;
  /** Aviso cujo "Ciente" está indo ao servidor (botão em loading). */
  enviando: number | null;
  /** Aviso cujo "Ciente" falhou. */
  falhou: number | null;
}

/**
 * Faixas da feature 339 no topo do evento: o que mudou e o que fazer, até a PRÓPRIA pessoa clicar
 * "Ciente" — o de um usuário do Casting não some com a faixa do outro. Na troca de tipo, a lista de
 * escalados é a do elenco atual (viva, não a congelada no aviso), e o cachê só aparece para quem já o
 * vê no elenco: o Ensaio lê os nomes.
 */
export function AvisosDoEvento({ avisos, elenco, onCiente, enviando, falhou }: AvisosDoEventoProps) {
  if (!avisos.length) return null;
  const escalados = elenco.filter((r) => r.talent && !r.is_presence);
  return (
    <>
      {avisos.map((aviso) => {
        const { titulo, texto } = textoDoAviso(aviso);
        const listar = aviso.kind === "evento.tipo_show" && escalados.length > 0;
        return (
          <div
            key={aviso.id}
            className="mt-3 rounded-md border border-gold/40 bg-gold-soft p-3 text-sm"
            role="status"
          >
            <p className="font-semibold text-gold-ink">{titulo}</p>
            <p className="mt-0.5 text-ink">{texto}</p>
            {listar && (
              <ul className="mt-2 space-y-0.5 text-ink">
                {escalados.map((r) => (
                  <li key={r.role_id}>
                    {r.character_name} — {r.talent?.name}
                    {r.cache_value != null && (
                      <span className="tabular-nums text-muted"> · R$ {formatBRL(r.cache_value)}</span>
                    )}
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                loading={enviando === aviso.id}
                onClick={() => onCiente(aviso.id)}
              >
                Ciente
              </Button>
              {falhou === aviso.id && (
                <span className="text-xs text-red">Não foi possível registrar. Tente novamente.</span>
              )}
            </div>
          </div>
        );
      })}
    </>
  );
}
