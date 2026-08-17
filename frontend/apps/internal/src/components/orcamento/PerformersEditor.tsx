import { Button, Table, TableCell, TableRow } from "@manto/ui";
import type { Performer } from "../../lib/orcamento";

const INPUT = "h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

export function emptyPerformer(type: Performer["type"] = "ator"): Performer {
  return { type, subtipo: "cara_limpa", nome: "", show: false, makeup: false };
}

/**
 * Editor da equipe do orçamento (coordenador + performers) — extraído de
 * `OrcamentoCalculadoraPage` na feature 235 para ser fonte única entre a Calculadora de
 * Orçamento e a contratação Manto embutida no EducaManto (Princípio I). Comportamento
 * idêntico ao original; só as props viraram explícitas.
 */
export function PerformersEditor({
  performers,
  onPerformersChange,
  coordenadorQty,
  onCoordenadorQtyChange,
  especiais,
  especiaisComShow,
  especiaisComCantor,
}: {
  performers: Performer[];
  onPerformersChange: (performers: Performer[]) => void;
  coordenadorQty: number;
  onCoordenadorQtyChange: (qty: number) => void;
  especiais: string[];
  especiaisComShow: string[];
  especiaisComCantor: string[];
}) {
  return (
    <>
      <Table className="min-w-[720px]">
        <thead>
          <TableRow head>
            <TableCell as="th">Tipo / Subtipo</TableCell>
            <TableCell as="th">Personagem/Nome</TableCell>
            <TableCell as="th">Flags</TableCell>
            <TableCell as="th">Maquiagem</TableCell>
            <TableCell as="th" align="right">
              Ações
            </TableCell>
          </TableRow>
        </thead>
        <tbody>
          <TableRow>
            <TableCell className="font-medium text-ink">Coordenador</TableCell>
            <TableCell colSpan={2} className="text-xs text-muted">
              Obrigatório — sempre presente na equipe
            </TableCell>
            <TableCell colSpan={2} align="right">
              <div className="flex items-center justify-end gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onCoordenadorQtyChange(Math.max(0, coordenadorQty - 1))}
                >
                  −
                </Button>
                <span className="w-6 text-center tabular-nums text-ink">{coordenadorQty}</span>
                <Button size="sm" variant="outline" onClick={() => onCoordenadorQtyChange(coordenadorQty + 1)}>
                  +
                </Button>
              </div>
            </TableCell>
          </TableRow>
          {performers.map((p, i) => (
            <PerformerTableRow
              key={i}
              performer={p}
              onChange={(np) => onPerformersChange(performers.map((x, idx) => (idx === i ? np : x)))}
              onRemove={() => onPerformersChange(performers.filter((_, idx) => idx !== i))}
              especiais={especiais}
              especiaisComShow={especiaisComShow}
              especiaisComCantor={especiaisComCantor}
            />
          ))}
        </tbody>
      </Table>
      <div className="flex gap-2 p-3">
        <Button
          size="sm"
          variant="ghost"
          onClick={() => onPerformersChange([...performers, emptyPerformer("ator")])}
        >
          + Ator / Cantor
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => onPerformersChange([...performers, emptyPerformer("especial")])}
        >
          + Especial
        </Button>
      </div>
    </>
  );
}

function PerformerTableRow({
  performer,
  onChange,
  onRemove,
  especiais,
  especiaisComShow,
  especiaisComCantor,
}: {
  performer: Performer;
  onChange: (p: Performer) => void;
  onRemove: () => void;
  especiais: string[];
  especiaisComShow: string[];
  especiaisComCantor: string[];
}) {
  const canShow =
    performer.type === "ator" ||
    (performer.type === "especial" && especiaisComShow.includes(performer.personagem ?? ""));
  const canCantor =
    performer.type === "especial" && especiaisComCantor.includes(performer.personagem ?? "");

  return (
    <TableRow>
      <TableCell>
        {performer.type === "ator" ? (
          <select
            className={INPUT}
            value={performer.subtipo ?? "cara_limpa"}
            onChange={(e) => onChange({ ...performer, subtipo: e.target.value as Performer["subtipo"] })}
          >
            <option value="cara_limpa">Ator — Cara limpa</option>
            <option value="boneco">Ator — Boneco</option>
            <option value="cantor">Ator — Cantor</option>
          </select>
        ) : (
          <div className="space-y-1.5">
            <select
              className={INPUT}
              value={performer.personagem ?? ""}
              onChange={(e) => onChange({ ...performer, personagem: e.target.value })}
            >
              <option value="">Selecione o especial…</option>
              {especiais.map((nome) => (
                <option key={nome} value={nome}>
                  {nome}
                </option>
              ))}
            </select>
            {performer.personagem === "Boneco Grande Especial" && (
              <select
                className={INPUT}
                value={performer.bge_subtipo ?? ""}
                onChange={(e) =>
                  onChange({ ...performer, bge_subtipo: e.target.value as Performer["bge_subtipo"] })
                }
              >
                <option value="">Sub-tipo do BGE…</option>
                <option value="dinossauro">Dinossauro</option>
                <option value="transformers">Transformers</option>
                <option value="outro">Outro</option>
              </select>
            )}
            {performer.bge_subtipo === "outro" && (
              <input
                className={INPUT}
                placeholder="Nome do personagem"
                value={performer.bge_outro_nome ?? ""}
                onChange={(e) => onChange({ ...performer, bge_outro_nome: e.target.value })}
              />
            )}
          </div>
        )}
      </TableCell>
      <TableCell>
        <input
          className={INPUT}
          placeholder="Opcional"
          value={performer.nome ?? ""}
          onChange={(e) => onChange({ ...performer, nome: e.target.value })}
        />
      </TableCell>
      <TableCell>
        <div className="flex flex-col gap-1">
          {canShow && (
            <label className="flex items-center gap-1.5 text-xs text-ink">
              <input
                type="checkbox"
                checked={Boolean(performer.show)}
                onChange={(e) => onChange({ ...performer, show: e.target.checked })}
              />
              Com show
            </label>
          )}
          {canCantor && (
            <label className="flex items-center gap-1.5 text-xs text-ink">
              <input
                type="checkbox"
                checked={Boolean(performer.cantor)}
                onChange={(e) => onChange({ ...performer, cantor: e.target.checked })}
              />
              Com cantor
            </label>
          )}
        </div>
      </TableCell>
      <TableCell>
        <div className="flex flex-col gap-1">
          <label className="flex items-center gap-1.5 text-xs text-ink">
            <input
              type="checkbox"
              checked={Boolean(performer.makeup)}
              onChange={(e) => onChange({ ...performer, makeup: e.target.checked })}
            />
            Maquiagem
          </label>
          {performer.makeup && (
            <select
              className={`${INPUT} h-8 text-xs`}
              value={performer.makeup_tipo ?? "comum"}
              onChange={(e) => onChange({ ...performer, makeup_tipo: e.target.value as Performer["makeup_tipo"] })}
            >
              <option value="comum">Comum</option>
              <option value="especial">Especial</option>
            </select>
          )}
        </div>
      </TableCell>
      <TableCell align="right">
        <Button size="sm" variant="ghost" onClick={onRemove}>
          Remover
        </Button>
      </TableCell>
    </TableRow>
  );
}
