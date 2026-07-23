import { useState } from "react";
import { Button, Card, CardContent, PageHeader, Skeleton } from "@manto/ui";
import { useTalentDirectory } from "../lib/talents";
import { TalentMosaic } from "../components/TalentMosaic";

function toggleInList(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

function MultiChoice({
  label,
  options,
  selected,
  onToggle,
}: {
  label: string;
  options: string[];
  selected: string[];
  onToggle: (value: string) => void;
}) {
  if (options.length === 0) return null;
  return (
    <div>
      <div className="mb-1 text-xs font-medium text-muted">{label}</div>
      <div className="flex flex-wrap gap-1.5">
        {options.map((opt) => (
          <button
            key={opt}
            type="button"
            className={`rounded-md border px-2 py-1 text-xs ${
              selected.includes(opt)
                ? "border-accent bg-accent-soft text-accent-dark"
                : "border-line text-ink"
            }`}
            onClick={() => onToggle(opt)}
          >
            {opt}
          </button>
        ))}
      </div>
    </div>
  );
}

export function TalentsListPage() {
  const [status, setStatus] = useState<"active" | "pending">("active");
  const [q, setQ] = useState("");
  const [jaTrabalhou, setJaTrabalhou] = useState(false);
  const [page, setPage] = useState(1);
  const [showFilters, setShowFilters] = useState(false);
  const [language, setLanguage] = useState<string[]>([]);
  const [race, setRace] = useState<string[]>([]);
  const [top, setTop] = useState<string[]>([]);
  const [bottom, setBottom] = useState<string[]>([]);
  const [shoe, setShoe] = useState<string[]>([]);
  const [passport, setPassport] = useState<string[]>([]);
  const [tag, setTag] = useState<string[]>([]);
  const [heightOp, setHeightOp] = useState<"gte" | "lte">("gte");
  const [heightValue, setHeightValue] = useState("");
  const [character, setCharacter] = useState("");

  const activeFilterCount =
    language.length + race.length + top.length + bottom.length + shoe.length + passport.length + tag.length +
    (heightValue ? 1 : 0) + (character ? 1 : 0);

  const query = useTalentDirectory({
    status,
    q: q || undefined,
    ja_trabalhou: jaTrabalhou,
    page,
    language,
    race,
    top,
    bottom,
    shoe,
    passport,
    tag,
    height_op: heightOp,
    height_value: heightValue || undefined,
    character: character || undefined,
  });

  return (
    <div className="mx-auto max-w-4xl p-4 sm:p-6">
      <PageHeader title="Talentos" className="mb-4" />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="flex rounded-md border border-line">
          <button
            className={`px-3 py-1.5 text-sm ${status === "active" ? "bg-accent text-white" : "text-ink"}`}
            onClick={() => {
              setStatus("active");
              setPage(1);
            }}
          >
            Ativos
          </button>
          <button
            className={`px-3 py-1.5 text-sm ${status === "pending" ? "bg-accent text-white" : "text-ink"}`}
            onClick={() => {
              setStatus("pending");
              setPage(1);
            }}
          >
            Pendentes {query.data && query.data.pending_count > 0 && `(${query.data.pending_count})`}
          </button>
        </div>
        <input
          className="h-10 min-w-40 flex-1 rounded-md border border-line bg-panel px-3 text-sm text-ink"
          placeholder="Buscar por nome…"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setPage(1);
          }}
          aria-label="Buscar talento"
        />
        <label className="flex items-center gap-1.5 text-sm text-ink">
          <input
            type="checkbox"
            checked={jaTrabalhou}
            onChange={(e) => {
              setJaTrabalhou(e.target.checked);
              setPage(1);
            }}
          />
          Já trabalhou com a Manto
        </label>
        {status === "active" && (
          <Button variant="outline" size="sm" onClick={() => setShowFilters((v) => !v)}>
            Filtros {activeFilterCount > 0 && `(${activeFilterCount})`}
          </Button>
        )}
      </div>

      {status === "active" && showFilters && query.data?.filter_options && (
        <Card className="mb-4">
          <CardContent className="space-y-3 p-4">
            <input
              className="h-9 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink"
              placeholder="Personagem já interpretado…"
              value={character}
              onChange={(e) => {
                setCharacter(e.target.value);
                setPage(1);
              }}
              aria-label="Filtrar por personagem"
            />
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-medium text-muted">Altura</span>
              <select
                className="h-8 rounded-md border border-line bg-panel px-1 text-xs text-ink"
                value={heightOp}
                onChange={(e) => setHeightOp(e.target.value as "gte" | "lte")}
              >
                <option value="gte">≥</option>
                <option value="lte">≤</option>
              </select>
              <input
                type="number"
                className="h-8 w-20 rounded-md border border-line bg-panel px-2 text-xs text-ink"
                placeholder="cm"
                value={heightValue}
                onChange={(e) => {
                  setHeightValue(e.target.value);
                  setPage(1);
                }}
              />
            </div>
            <MultiChoice
              label="Idioma"
              options={query.data.filter_options.languages}
              selected={language}
              onToggle={(v) => {
                setLanguage((s) => toggleInList(s, v));
                setPage(1);
              }}
            />
            <MultiChoice
              label="Raça"
              options={query.data.filter_options.races}
              selected={race}
              onToggle={(v) => {
                setRace((s) => toggleInList(s, v));
                setPage(1);
              }}
            />
            <MultiChoice
              label="Tamanho (superior)"
              options={query.data.filter_options.sizes}
              selected={top}
              onToggle={(v) => {
                setTop((s) => toggleInList(s, v));
                setPage(1);
              }}
            />
            <MultiChoice
              label="Tamanho (inferior)"
              options={query.data.filter_options.sizes}
              selected={bottom}
              onToggle={(v) => {
                setBottom((s) => toggleInList(s, v));
                setPage(1);
              }}
            />
            <MultiChoice
              label="Calçado"
              options={query.data.filter_options.shoes}
              selected={shoe}
              onToggle={(v) => {
                setShoe((s) => toggleInList(s, v));
                setPage(1);
              }}
            />
            <MultiChoice
              label="Passaporte/Visto"
              options={query.data.filter_options.passport.map(([value]) => value)}
              selected={passport}
              onToggle={(v) => {
                setPassport((s) => toggleInList(s, v));
                setPage(1);
              }}
            />
            <MultiChoice
              label="Tags"
              options={query.data.filter_options.tags}
              selected={tag}
              onToggle={(v) => {
                setTag((s) => toggleInList(s, v));
                setPage(1);
              }}
            />
            {activeFilterCount > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setLanguage([]);
                  setRace([]);
                  setTop([]);
                  setBottom([]);
                  setShoe([]);
                  setPassport([]);
                  setTag([]);
                  setHeightValue("");
                  setCharacter("");
                  setPage(1);
                }}
              >
                Limpar filtros
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {query.isLoading && (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar os talentos.
        </div>
      )}

      {query.data && (
        <>
          {query.data.items.length === 0 ? (
            <p className="text-sm text-muted">Nenhum talento encontrado.</p>
          ) : (
            <TalentMosaic talents={query.data.items} isPending={status === "pending"} />
          )}

          {query.data.pages > 1 && (
            <div className="mt-4 flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                ‹ Anterior
              </Button>
              <span className="text-sm text-muted">
                Página {query.data.page} de {query.data.pages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= query.data.pages}
                onClick={() => setPage((p) => p + 1)}
              >
                Próxima ›
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
