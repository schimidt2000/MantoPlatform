import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Button,
  Card,
  CardContent,
  PageHeader,
  Skeleton,
  FilterDropdown,
  CheckboxList,
} from "@manto/ui";
import { assetUrl, API_BASE } from "@manto/api-client";
import { Pencil, Printer } from "lucide-react";
import {
  useFigurinoSheets,
  useDismissMissingCharacter,
  useAssociateMissingCharacter,
  type FigurinoSheetItem,
  type MissingCharacter,
} from "../lib/figurino";
import { useCurrentUser } from "../lib/useAuth";
import { useCatalogElencoBusca } from "../lib/catalogoElenco";
import { useLinkCharacterFigurino } from "../lib/adminCatalogo";
import { SectorPanel } from "../components/SectorPanel";
import { Modal } from "../components/Modal";
import { CharacterAutocomplete } from "../components/CharacterAutocomplete";

/** Remove acentos e caixa para comparação de busca (sem dependência nova). */
function normalizeSearch(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

function formatCardDate(sheet: FigurinoSheetItem): string {
  const iso = sheet.updated_at ?? sheet.created_at;
  return iso ? new Date(iso).toLocaleDateString("pt-BR") : "—";
}

interface FigurinoCardProps {
  sheet: FigurinoSheetItem;
  canEdit: boolean;
  /** Nome do Personagem do catálogo vinculado a esta ficha, ou `null` (feature 186, US2). */
  linkedCharacterName: string | null;
  onQuickLink: () => void;
}

function FigurinoCard({ sheet, canEdit, linkedCharacterName, onQuickLink }: FigurinoCardProps) {
  return (
    <Card>
      <CardContent className="space-y-2 p-2">
        <div className="relative aspect-[3/4] w-full overflow-hidden rounded-md bg-surface-2">
          {sheet.photo_url ? (
            <img
              src={assetUrl(sheet.photo_url)}
              alt={sheet.character_name}
              className="h-full w-full object-cover object-top"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-3xl" aria-hidden="true">
              📷
            </div>
          )}
          {/* Manutenção aberta (feature 225b) — sobre a foto de propósito: quem separa figurino
              olha a imagem, não o texto. É o que impede um boneco quebrado de ir para a festa. */}
          {sheet.manutencao && (
            <Link
              to={`/figurinos/producao?ficha=${sheet.id}`}
              title={sheet.manutencao.titulos.join(" · ")}
              className={`absolute left-1 top-1 rounded-md px-1.5 py-0.5 text-[11px] font-bold ${
                sheet.manutencao.impede_uso
                  ? "bg-red text-on-color"
                  : "bg-gold-soft text-gold-ink"
              }`}
            >
              {sheet.manutencao.impede_uso
                ? "⚠ Não pode ir"
                : `🪡 ${sheet.manutencao.abertas} conserto${sheet.manutencao.abertas === 1 ? "" : "s"}`}
            </Link>
          )}
          {/* Só aparece quando foge do padrão (1): é a informação que decide se dá para escalar
              o mesmo personagem em dois eventos no mesmo horário (feature 235). */}
          {sheet.quantity !== 1 && (
            <span
              title={
                sheet.quantity === 0
                  ? "Nenhum figurino pronto desta ficha"
                  : `${sheet.quantity} figurinos iguais no acervo`
              }
              className={`absolute right-1 top-1 rounded-md px-1.5 py-0.5 text-[11px] font-bold ${
                sheet.quantity === 0 ? "bg-red text-on-color" : "bg-accent-soft text-accent-dark"
              }`}
            >
              {sheet.quantity === 0 ? "sem figurino" : `${sheet.quantity}×`}
            </span>
          )}
        </div>
        <div>
          <div className="truncate text-sm font-medium text-ink" title={sheet.character_name}>
            {sheet.character_name}
          </div>
          <div className="text-xs text-muted">
            {sheet.pieces.length} peça{sheet.pieces.length === 1 ? "" : "s"} · {formatCardDate(sheet)}
          </div>
          {linkedCharacterName ? (
            <span className="mt-1 inline-block rounded-full bg-green-soft px-2 py-0.5 text-[11px] font-medium text-green">
              ✓ {linkedCharacterName}
            </span>
          ) : canEdit ? (
            <button
              type="button"
              onClick={onQuickLink}
              className="mt-1 inline-block rounded-full bg-red-soft px-2 py-0.5 text-[11px] font-medium text-red hover:opacity-80"
            >
              ⚠ Sem personagem — + Vincular
            </button>
          ) : (
            <span className="mt-1 inline-block rounded-full bg-red-soft px-2 py-0.5 text-[11px] font-medium text-red">
              ⚠ Sem personagem vinculado
            </span>
          )}
        </div>
        <div className="flex gap-1.5">
          <Button
            size="sm"
            className="flex-1"
            onClick={() => window.open(`${API_BASE}/figurinos/${sheet.id}/print`, "_blank", "noopener")}
          >
            <Printer className="h-3.5 w-3.5" aria-hidden="true" />
            Imprimir
          </Button>
          {canEdit && (
            <Button asChild variant="outline" size="sm" aria-label={`Editar ficha de ${sheet.character_name}`}>
              <Link to={`/figurinos/${sheet.id}/edit`}>
                <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
              </Link>
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

interface AssociateMissingModalProps {
  missing: MissingCharacter | null;
  sheets: FigurinoSheetItem[];
  onClose: () => void;
}

/** Modal de "Associar a uma ficha existente" (feature 183) — reaproveita o `Modal` local
 * (feature 179), já que `@manto/ui` não tem um Dialog compartilhado (ver research.md §4). */
function AssociateMissingModal({ missing, sheets, onClose }: AssociateMissingModalProps) {
  const [sheetId, setSheetId] = useState<string>("");
  const associate = useAssociateMissingCharacter();

  const confirm = () => {
    if (!missing || !sheetId) return;
    associate.mutate(
      { characterNameNorm: missing.character_name_norm, sheetId: Number(sheetId) },
      {
        onSuccess: () => {
          setSheetId("");
          onClose();
        },
      },
    );
  };

  return (
    <Modal open={Boolean(missing)} onClose={onClose} title="Associar a uma ficha existente">
      {missing && (
        <div className="space-y-4">
          <p className="text-sm text-muted">
            Vincular os cargos de evento de <strong className="text-ink">{missing.character_name}</strong>{" "}
            à ficha escolhida abaixo.
          </p>
          <select
            className="h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink"
            value={sheetId}
            onChange={(e) => setSheetId(e.target.value)}
            aria-label="Ficha de figurino"
          >
            <option value="">Selecione uma ficha…</option>
            {sheets.map((s) => (
              <option key={s.id} value={s.id}>
                {s.character_name}
              </option>
            ))}
          </select>
          {associate.isError && (
            <p className="text-sm text-red">Não foi possível associar. Tente novamente.</p>
          )}
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose}>
              Cancelar
            </Button>
            <Button loading={associate.isPending} disabled={!sheetId} onClick={confirm}>
              Confirmar
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}

interface MissingPanelProps {
  missing: MissingCharacter[];
  sheets: FigurinoSheetItem[];
}

/** Painel "Figurinos solicitados/faltantes" — SUPERADMIN apenas, colapsável (feature 183). */
function MissingSheetsPanel({ missing, sheets }: MissingPanelProps) {
  const dismiss = useDismissMissingCharacter();
  const [associating, setAssociating] = useState<MissingCharacter | null>(null);
  const [dismissingNorm, setDismissingNorm] = useState<string | null>(null);

  if (missing.length === 0) {
    return null;
  }

  const handleDismiss = (item: MissingCharacter) => {
    if (!window.confirm(`Descartar o alerta de "${item.character_name}"?`)) return;
    setDismissingNorm(item.character_name_norm);
    dismiss.mutate(item.character_name_norm, { onSettled: () => setDismissingNorm(null) });
  };

  return (
    <>
      <SectorPanel title="⚠️ Figurinos solicitados/faltantes" count={missing.length} defaultOpen={false}>
        <ul className="divide-y divide-line">
          {missing.map((item) => (
            <li key={item.character_name_norm} className="flex items-center justify-between gap-2 py-2">
              <span className="text-sm text-ink">{item.character_name}</span>
              <div className="flex shrink-0 gap-2">
                <Button variant="outline" size="sm" onClick={() => setAssociating(item)}>
                  Associar a uma ficha existente
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  loading={dismissingNorm === item.character_name_norm}
                  onClick={() => handleDismiss(item)}
                >
                  Excluir
                </Button>
              </div>
            </li>
          ))}
        </ul>
      </SectorPanel>
      <AssociateMissingModal missing={associating} sheets={sheets} onClose={() => setAssociating(null)} />
    </>
  );
}

export function FigurinoListPage() {
  const query = useFigurinoSheets();
  const { data: user } = useCurrentUser();
  const canEdit = Boolean(user?.is_superadmin || user?.roles.includes("FIGURINO"));
  const [q, setQ] = useState("");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [linkingSheet, setLinkingSheet] = useState<FigurinoSheetItem | null>(null);

  const elencoBusca = useCatalogElencoBusca();
  const linkCharacter = useLinkCharacterFigurino();
  const linkedNameBySheetId = useMemo(() => {
    const map = new Map<number, string>();
    for (const tema of elencoBusca.data?.temas ?? []) {
      for (const character of tema.characters) {
        if (character.figurino_sheet_id) map.set(character.figurino_sheet_id, character.name);
      }
    }
    return map;
  }, [elencoBusca.data]);

  const items = query.data?.items ?? [];

  const allTags = useMemo(() => {
    const set = new Set<string>();
    for (const item of items) {
      for (const tag of item.tags) set.add(tag);
    }
    return Array.from(set).sort((a, b) => a.localeCompare(b, "pt-BR"));
  }, [items]);

  const filtered = useMemo(() => {
    const needle = normalizeSearch(q);
    return items.filter((s) => {
      const matchesName = !needle || normalizeSearch(s.character_name).includes(needle);
      const matchesTags = selectedTags.length === 0 || selectedTags.every((t) => s.tags.includes(t));
      return matchesName && matchesTags;
    });
  }, [items, q, selectedTags]);

  const toggleTag = (tag: string) =>
    setSelectedTags((tags) => (tags.includes(tag) ? tags.filter((t) => t !== tag) : [...tags, tag]));

  return (
    <div className="mx-auto max-w-[110rem] space-y-4 p-4 sm:p-6">
      <header className="flex items-center justify-between">
        <PageHeader title="Figurino" className="mb-0" />
        {canEdit && (
          <Button asChild size="sm">
            <Link to="/figurinos/new">+ Nova ficha</Link>
          </Button>
        )}
      </header>

      {user?.is_superadmin && query.data && (
        <MissingSheetsPanel missing={query.data.chars_without_sheet} sheets={items} />
      )}

      <div className="flex flex-wrap items-center gap-2">
        <input
          className="h-10 min-w-[200px] flex-1 rounded-md border border-line bg-panel px-3 text-sm text-ink"
          placeholder="Buscar ficha por nome…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          aria-label="Buscar ficha de figurino"
        />
        {allTags.length > 0 && (
          <FilterDropdown label="Tags" count={selectedTags.length}>
            <CheckboxList
              options={allTags.map((t) => ({ value: t, label: t }))}
              selected={selectedTags}
              onToggle={toggleTag}
              searchable
              searchPlaceholder="Buscar tag…"
            />
          </FilterDropdown>
        )}
      </div>

      {query.isLoading && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="aspect-[3/4] w-full" />
          ))}
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar as fichas.
        </div>
      )}

      {query.data && filtered.length === 0 && (
        <p className="text-sm text-muted">Nenhuma ficha encontrada.</p>
      )}

      {filtered.length > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6">
          {filtered.map((sheet) => (
            <FigurinoCard
              key={sheet.id}
              sheet={sheet}
              canEdit={canEdit}
              linkedCharacterName={linkedNameBySheetId.get(sheet.id) ?? null}
              onQuickLink={() => setLinkingSheet(sheet)}
            />
          ))}
        </div>
      )}

      <Modal
        open={linkingSheet !== null}
        onClose={() => setLinkingSheet(null)}
        title={`Vincular "${linkingSheet?.character_name ?? ""}" a um Personagem do Catálogo`}
      >
        <CharacterAutocomplete
          temas={elencoBusca.data?.temas ?? []}
          placeholder="Buscar personagem do catálogo…"
          onSelect={(selection) => {
            if (!linkingSheet) return;
            linkCharacter.mutate(
              { characterId: selection.character.id, figurinoSheetId: linkingSheet.id },
              { onSuccess: () => setLinkingSheet(null) },
            );
          }}
        />
      </Modal>
    </div>
  );
}
