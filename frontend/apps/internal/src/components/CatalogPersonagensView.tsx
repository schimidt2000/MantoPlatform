import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Plus, Shirt, TriangleAlert, X } from "lucide-react";
import { assetUrl, ApiRequestError } from "@manto/api-client";
import { Button, cn } from "@manto/ui";
import {
  useCatalogPersonagens,
  useReuseCharacter,
  type CatalogListItem,
  type CatalogPersonagem,
} from "../lib/adminCatalogo";

/** Remove acentos e baixa a caixa — mesmo espírito do `strip_accents_lower` do backend. */
function normalize(value: string): string {
  return value.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
}

type Filtro = "todos" | "sem_ficha" | "varios_temas";

interface CatalogPersonagensViewProps {
  /** Temas disponíveis para receber um personagem (a lista já carregada da tela). */
  temas: CatalogListItem[];
  busca: string;
}

/** Um contador do termômetro do topo. Clicar filtra a lista. */
function Contador({
  valor,
  rotulo,
  tone = "neutral",
  ativo,
  onClick,
}: {
  valor: number | string;
  rotulo: string;
  tone?: "neutral" | "red" | "green";
  ativo?: boolean;
  onClick?: () => void;
}) {
  const conteudo = (
    <>
      <span
        className={cn(
          "text-lg font-semibold leading-none",
          tone === "red" ? "text-red" : tone === "green" ? "text-green" : "text-ink",
        )}
      >
        {valor}
      </span>
      <span className="text-[11px] leading-tight text-muted">{rotulo}</span>
    </>
  );
  const classe = cn(
    "flex min-w-24 flex-col items-start gap-0.5 rounded-md border px-2.5 py-1.5 text-left",
    ativo ? "border-accent bg-accent-soft" : "border-line bg-panel",
    onClick && "hover:border-accent",
  );
  return onClick ? (
    <button type="button" onClick={onClick} className={classe}>
      {conteudo}
    </button>
  ) : (
    <div className={classe}>{conteudo}</div>
  );
}

/** Linha de um personagem: quem é, se tem figurino e em que temas ele já está. */
function PersonagemRow({
  personagem,
  temas,
  onAdd,
  adicionando,
  erro,
}: {
  personagem: CatalogPersonagem;
  temas: CatalogListItem[];
  onAdd: (temaId: number) => void;
  adicionando: boolean;
  erro: string | null;
}) {
  const [escolhendoTema, setEscolhendoTema] = useState(false);
  const [buscaTema, setBuscaTema] = useState("");
  const jaEstaEm = new Set(personagem.temas.map((t) => t.tema_id));
  const maxSimultaneo = Math.max(...personagem.temas.map((t) => t.aparicoes.length), 0);

  const opcoes = useMemo(() => {
    const termo = normalize(buscaTema.trim());
    return temas
      .filter((t) => !jaEstaEm.has(t.id) && (!termo || normalize(t.name).includes(termo)))
      .slice(0, 8);
    // `jaEstaEm` deriva de `personagem`, que já está nas dependências pela prop.
  }, [temas, buscaTema, personagem]);

  return (
    <li className="rounded-md border border-line bg-panel p-2.5">
      {/* No celular a ação desce para a própria linha: espremida ao lado, ela roubava a largura
          do nome e do selo da ficha, que é o que se lê primeiro. */}
      <div className="flex flex-wrap items-start gap-3">
        <div className="h-12 w-12 flex-none overflow-hidden rounded-full bg-surface-2">
          {personagem.photo_url ? (
            <img
              src={assetUrl(personagem.photo_url)}
              alt=""
              className="h-full w-full object-cover"
            />
          ) : (
            <span className="flex h-full w-full items-center justify-center text-lg">🎭</span>
          )}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="truncate text-sm font-medium text-ink">{personagem.name}</span>

            {personagem.figurino_sheet_id ? (
              <Link
                to={`/figurinos/${personagem.figurino_sheet_id}/edit`}
                className="inline-flex items-center gap-1 rounded-full bg-green-soft px-2 py-0.5 text-[11px] font-medium text-green hover:underline"
                title={`Ficha: ${personagem.figurino_sheet_name}`}
              >
                <Shirt className="h-3 w-3" aria-hidden="true" />
                {personagem.figurino_sheet_name}
              </Link>
            ) : (
              <span className="inline-flex items-center gap-1 rounded-full bg-red-soft px-2 py-0.5 text-[11px] font-medium text-red">
                <TriangleAlert className="h-3 w-3" aria-hidden="true" />
                sem ficha — só existe neste tema
              </span>
            )}

            {/* Quantos figurinos iguais existem: é o que decide se dá para escalar o mesmo
                personagem em dois eventos no mesmo horário (feature 235). */}
            {personagem.quantidade_figurinos !== null &&
              personagem.quantidade_figurinos !== 1 && (
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 text-[11px] font-medium",
                    personagem.quantidade_figurinos === 0
                      ? "bg-red-soft text-red"
                      : "bg-accent-soft text-accent-dark",
                  )}
                >
                  {personagem.quantidade_figurinos === 0
                    ? "nenhum figurino pronto"
                    : `${personagem.quantidade_figurinos} figurinos iguais`}
                </span>
              )}

            {personagem.manutencao && (
              <Link
                to={`/figurinos/producao?ficha=${personagem.figurino_sheet_id}`}
                title={personagem.manutencao.titulos.join(" · ")}
                className={cn(
                  "rounded-full px-2 py-0.5 text-[11px] font-medium",
                  personagem.manutencao.impede_uso
                    ? "bg-red text-on-color"
                    : "bg-gold-soft text-gold-ink",
                )}
              >
                {personagem.manutencao.impede_uso
                  ? "⚠ não pode ir"
                  : `🪡 ${personagem.manutencao.abertas} conserto${personagem.manutencao.abertas === 1 ? "" : "s"}`}
              </Link>
            )}
          </div>

          <div className="mt-1 flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] text-muted">
              {personagem.temas.length === 1 ? "em 1 tema:" : `em ${personagem.temas.length} temas:`}
            </span>
            {personagem.temas.map((tema) => {
              const todasInativas = tema.aparicoes.every((a) => !a.is_active);
              const apelidos = tema.aparicoes
                .map((a) => a.character_name)
                .filter((nome) => nome !== personagem.name);
              return (
                <Link
                  key={tema.tema_id}
                  to={`/admin/catalogo/${tema.tema_id}/editar`}
                  className={cn(
                    "rounded-md border border-line px-1.5 py-0.5 text-[11px] hover:border-accent hover:text-accent",
                    todasInativas ? "text-muted line-through" : "text-ink",
                  )}
                  title={apelidos.length > 0 ? `Aparece como: ${apelidos.join(", ")}` : undefined}
                >
                  {tema.tema_name}
                  {/* Duas aparições no mesmo tema = dois performers do mesmo figurino ao mesmo
                      tempo (o caso "Astronauta 1"/"Astronauta 2"). É o que torna a quantidade de
                      figurinos iguais uma informação de logística, não um detalhe de cadastro. */}
                  {tema.aparicoes.length > 1 && (
                    <span className="ml-1 font-semibold text-accent">
                      ×{tema.aparicoes.length}
                    </span>
                  )}
                </Link>
              );
            })}
            {/* O alerta que só existe porque as duas informações agora estão na mesma linha. */}
            {personagem.quantidade_figurinos !== null &&
              maxSimultaneo > personagem.quantidade_figurinos && (
                <span className="rounded-md bg-gold-soft px-1.5 py-0.5 text-[11px] font-medium text-gold-ink">
                  um tema pede {maxSimultaneo} ao mesmo tempo, temos{" "}
                  {personagem.quantidade_figurinos}
                </span>
              )}
          </div>

          {erro && (
            <p className="mt-1 text-[11px] text-red" role="alert">
              {erro}
            </p>
          )}
        </div>

        <div className="w-full sm:w-auto sm:flex-none">
          {personagem.figurino_sheet_id ? (
            <Button
              variant="outline"
              size="sm"
              className="w-full sm:w-auto"
              loading={adicionando}
              onClick={() => setEscolhendoTema((prev) => !prev)}
            >
              <Plus className="h-4 w-4" aria-hidden="true" />
              Usar em outro tema
            </Button>
          ) : (
            <span
              className="block text-[11px] text-muted sm:max-w-40 sm:text-right"
              title="A ficha é o que diz que dois personagens de temas diferentes são o mesmo"
            >
              Vincule uma ficha para poder reaproveitar
            </span>
          )}
        </div>
      </div>

      <AnimatePresence initial={false}>
        {escolhendoTema && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <div className="mt-2 rounded-md bg-surface-2/60 p-2">
              <div className="mb-1.5 flex items-center justify-between gap-2">
                <label
                  className="text-[11px] font-medium text-muted"
                  htmlFor={`busca-tema-${personagem.key}`}
                >
                  Em qual tema {personagem.name} também aparece?
                </label>
                <button
                  type="button"
                  className="text-muted hover:text-ink"
                  aria-label="Fechar"
                  onClick={() => setEscolhendoTema(false)}
                >
                  <X className="h-4 w-4" aria-hidden="true" />
                </button>
              </div>
              <input
                id={`busca-tema-${personagem.key}`}
                type="search"
                className="h-9 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink"
                placeholder="Buscar tema…"
                value={buscaTema}
                onChange={(e) => setBuscaTema(e.target.value)}
              />
              <ul className="mt-1.5 space-y-1">
                {opcoes.map((tema) => (
                  <li key={tema.id}>
                    <button
                      type="button"
                      disabled={adicionando}
                      className="flex w-full items-center gap-2 rounded-md px-1.5 py-1 text-left hover:bg-panel disabled:opacity-50"
                      onClick={() => {
                        onAdd(tema.id);
                        setEscolhendoTema(false);
                        setBuscaTema("");
                      }}
                    >
                      <span className="h-7 w-7 flex-none overflow-hidden rounded bg-surface-2">
                        {tema.cover_url && (
                          <img
                            src={assetUrl(tema.cover_url)}
                            alt=""
                            className="h-full w-full object-cover"
                          />
                        )}
                      </span>
                      <span className="min-w-0 flex-1 truncate text-sm text-ink">{tema.name}</span>
                    </button>
                  </li>
                ))}
                {opcoes.length === 0 && (
                  <li className="px-1.5 py-1 text-[11px] text-muted">
                    Nenhum tema disponível — ele já está em todos os que batem com a busca.
                  </li>
                )}
              </ul>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </li>
  );
}

/**
 * Modo Personagens do gerenciador de catálogo (feature 235).
 *
 * As outras duas visões olham o catálogo pelo **produto** (Cards) e pela **hierarquia**
 * (Árvore): as duas repetem o mesmo personagem uma vez por tema. Esta olha pelo **personagem** —
 * uma linha por identidade, com os temas em que ele aparece.
 *
 * A identidade é a **ficha de figurino**, e não o nome: é a ficha que representa o figurino
 * físico que a Manto tem, e é ela que o resto do ERP já usa (elenco do evento, alerta de "sem
 * ficha", manutenção, produção). Personagem sem ficha aparece como pendência e não pode ser
 * reaproveitado — sem ela não há como afirmar que dois personagens de temas diferentes são o
 * mesmo.
 */
export function CatalogPersonagensView({ temas, busca }: CatalogPersonagensViewProps) {
  const query = useCatalogPersonagens();
  const reuse = useReuseCharacter();
  const reduceMotion = useReducedMotion();
  const [filtro, setFiltro] = useState<Filtro>("todos");
  const [erroPorKey, setErroPorKey] = useState<Record<string, string>>({});

  const personagens = query.data?.personagens ?? [];
  const totais = query.data?.totais;

  const visiveis = useMemo(() => {
    const termo = normalize(busca.trim());
    return personagens.filter((p) => {
      if (filtro === "sem_ficha" && p.figurino_sheet_id) return false;
      if (filtro === "varios_temas" && p.temas.length < 2) return false;
      if (!termo) return true;
      return (
        normalize(p.name).includes(termo) ||
        p.temas.some((t) => normalize(t.tema_name).includes(termo))
      );
    });
  }, [personagens, busca, filtro]);

  function adicionar(personagem: CatalogPersonagem, temaId: number) {
    if (!personagem.figurino_sheet_id) return;
    setErroPorKey((prev) => ({ ...prev, [personagem.key]: "" }));
    reuse.mutate(
      { temaId, figurinoSheetId: personagem.figurino_sheet_id },
      {
        onError: (err) =>
          setErroPorKey((prev) => ({
            ...prev,
            [personagem.key]:
              err instanceof ApiRequestError ? err.message : "Não foi possível adicionar ao tema.",
          })),
      },
    );
  }

  if (query.isLoading) {
    return <p className="p-4 text-sm text-muted">Carregando personagens…</p>;
  }
  if (query.isError) {
    return <p className="p-4 text-sm text-red">Não foi possível carregar os personagens.</p>;
  }

  return (
    <div className="space-y-3">
      {totais && (
        <div className="flex flex-wrap gap-2">
          <Contador
            valor={totais.personagens}
            rotulo="personagens"
            ativo={filtro === "todos"}
            onClick={() => setFiltro("todos")}
          />
          <Contador valor={totais.aparicoes} rotulo="aparições em temas" />
          <Contador valor={totais.com_ficha} rotulo="com ficha" tone="green" />
          <Contador
            valor={totais.sem_ficha}
            rotulo="sem ficha"
            tone={totais.sem_ficha > 0 ? "red" : "neutral"}
            ativo={filtro === "sem_ficha"}
            onClick={() => setFiltro(filtro === "sem_ficha" ? "todos" : "sem_ficha")}
          />
          <Contador
            valor={totais.em_varios_temas}
            rotulo="em mais de um tema"
            ativo={filtro === "varios_temas"}
            onClick={() => setFiltro(filtro === "varios_temas" ? "todos" : "varios_temas")}
          />
          <div className="flex min-w-24 flex-col items-start gap-0.5 rounded-md border border-dashed border-line px-2.5 py-1.5">
            <span className="text-lg font-semibold leading-none text-muted">
              {totais.fichas_fora_do_catalogo}
            </span>
            <span className="text-[11px] leading-tight text-muted">
              fichas do acervo ainda fora do catálogo
            </span>
          </div>
        </div>
      )}

      {reuse.isError && !Object.values(erroPorKey).some(Boolean) && (
        <p className="text-sm text-red">Não foi possível adicionar ao tema.</p>
      )}

      <ul className="space-y-1.5">
        <AnimatePresence initial={false}>
          {visiveis.map((personagem) => (
            <motion.div
              key={personagem.key}
              layout={!reduceMotion}
              initial={reduceMotion ? false : { opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -4 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
            >
              <PersonagemRow
                personagem={personagem}
                temas={temas}
                adicionando={
                  reuse.isPending &&
                  reuse.variables?.figurinoSheetId === personagem.figurino_sheet_id
                }
                erro={erroPorKey[personagem.key] || null}
                onAdd={(temaId) => adicionar(personagem, temaId)}
              />
            </motion.div>
          ))}
        </AnimatePresence>
      </ul>

      {visiveis.length === 0 && (
        <p className="rounded-md border border-dashed border-line p-6 text-center text-sm text-muted">
          {personagens.length === 0
            ? "Nenhum personagem criado ainda. Abra um tema e adicione o elenco dele."
            : "Nenhum personagem bate com o filtro."}
        </p>
      )}
    </div>
  );
}
