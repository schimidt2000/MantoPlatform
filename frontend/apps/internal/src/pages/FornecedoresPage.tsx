import { useEffect, useMemo, useState } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import { ApiRequestError } from "@manto/api-client";
import {
  Badge,
  Button,
  Card,
  CardContent,
  Combobox,
  CopyButton,
  PageHeader,
  Skeleton,
  useRestaurarRolagem,
  type ComboboxOption,
} from "@manto/ui";
import { KebabMenu } from "../components/KebabMenu";
import { Modal } from "../components/Modal";
import {
  dataCurta,
  useAlterarFornecedor,
  useCadastrarFornecedor,
  useFornecedores,
  useJuntarFornecedores,
  type Fornecedor,
} from "../lib/fornecedores";
import { useChegouPeloHistorico } from "../lib/navegacao";
import { brl, normalizeSearch } from "../lib/pagamentos";

const LABEL = "mb-1 block text-xs font-medium text-muted";
const INPUT = "h-10 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink";

function contagemDeGastos(n: number): string {
  return `${n} ${n === 1 ? "gasto" : "gastos"}`;
}

function resumo(f: Fornecedor): string {
  const partes = [contagemDeGastos(f.gastos ?? 0), `${brl(f.total_aprovado)} aprovados`];
  if (f.ultimo_gasto) partes.push(`último em ${dataCurta(f.ultimo_gasto)}`);
  return partes.join(" · ");
}

// ── cadastrar / alterar ──────────────────────────────────────────────────────────────────────────

interface FormValues {
  nome: string;
  pix: string;
  categoria: string;
}

function FornecedorFormModal({
  fornecedor,
  categorias,
  open,
  onClose,
}: {
  /** `null` = cadastro novo. */
  fornecedor: Fornecedor | null;
  categorias: string[];
  open: boolean;
  onClose: () => void;
}) {
  const cadastrar = useCadastrarFornecedor();
  const alterar = useAlterarFornecedor();
  const [values, setValues] = useState<FormValues>({ nome: "", pix: "", categoria: "" });
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!open) return;
    setFieldErrors({});
    cadastrar.reset();
    alterar.reset();
    setValues({
      nome: fornecedor?.nome ?? "",
      pix: fornecedor?.pix ?? "",
      categoria: fornecedor?.categoria_padrao ?? "",
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, fornecedor?.id]);

  const mutation = fornecedor ? alterar : cadastrar;
  const onError = (err: Error) => {
    if (err instanceof ApiRequestError && err.fields) setFieldErrors(err.fields);
  };
  const salvar = () => {
    setFieldErrors({});
    const corpo = { nome: values.nome, pix: values.pix, categoria_padrao: values.categoria };
    if (fornecedor) alterar.mutate({ id: fornecedor.id, ...corpo }, { onSuccess: onClose, onError });
    else cadastrar.mutate(corpo, { onSuccess: onClose, onError });
  };
  const erroSemCampo =
    mutation.isError && !Object.keys(fieldErrors).length
      ? mutation.error?.message || "Não foi possível salvar o fornecedor. Tente novamente."
      : null;

  return (
    <Modal open={open} onClose={onClose} title={fornecedor ? "Alterar fornecedor" : "Novo fornecedor"}>
      <div className="space-y-3">
        <div>
          <label className={LABEL} htmlFor="fornecedor-nome">
            Nome
          </label>
          <input
            id="fornecedor-nome"
            className={INPUT}
            value={values.nome}
            aria-invalid={Boolean(fieldErrors.nome)}
            onChange={(e) => setValues((v) => ({ ...v, nome: e.target.value }))}
          />
          {fieldErrors.nome && (
            <p className="mt-1 text-xs text-red" role="alert">
              {fieldErrors.nome}
            </p>
          )}
          {fornecedor && (fornecedor.gastos ?? 0) > 0 && (
            <p className="mt-1 text-xs text-muted">O nome novo vale também nos {contagemDeGastos(fornecedor.gastos ?? 0)} já lançados.</p>
          )}
        </div>
        <div>
          <label className={LABEL} htmlFor="fornecedor-pix">
            Chave PIX (opcional)
          </label>
          <input
            id="fornecedor-pix"
            className={INPUT}
            value={values.pix}
            onChange={(e) => setValues((v) => ({ ...v, pix: e.target.value }))}
          />
          {fornecedor && <p className="mt-1 text-xs text-muted">Vale para os próximos gastos; os já lançados mantêm a chave com que foram lançados.</p>}
        </div>
        <div>
          <label className={LABEL} htmlFor="fornecedor-categoria">
            Categoria padrão
          </label>
          <select
            id="fornecedor-categoria"
            className={INPUT}
            value={values.categoria}
            onChange={(e) => setValues((v) => ({ ...v, categoria: e.target.value }))}
          >
            <option value="">Sem categoria padrão</option>
            {categorias.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          {fieldErrors.categoria_padrao && (
            <p className="mt-1 text-xs text-red" role="alert">
              {fieldErrors.categoria_padrao}
            </p>
          )}
        </div>
        {erroSemCampo && <p className="text-sm text-red">{erroSemCampo}</p>}
        <div className="flex flex-wrap gap-2 pt-1">
          <Button loading={mutation.isPending} onClick={salvar}>
            Salvar
          </Button>
          <Button type="button" variant="ghost" onClick={onClose} disabled={mutation.isPending}>
            Cancelar
          </Button>
        </div>
      </div>
    </Modal>
  );
}

// ── juntar ───────────────────────────────────────────────────────────────────────────────────────

function efeitoDeJuntar(origem: Fornecedor, destino: Fornecedor): string {
  const n = origem.gastos ?? 0;
  const gastos =
    n === 0
      ? `“${origem.nome}” não tem gastos.`
      : n === 1
        ? `O gasto de “${origem.nome}” passa para “${destino.nome}”, com o nome dele.`
        : `Os ${n} gastos de “${origem.nome}” passam para “${destino.nome}”, com o nome dele.`;
  return `${gastos} Se “${destino.nome}” não tiver chave PIX ou categoria, fica com as de “${origem.nome}”. “${origem.nome}” deixa de existir; não é possível desfazer.`;
}

function JuntarModal({
  origem,
  fornecedores,
  onClose,
}: {
  origem: Fornecedor | null;
  fornecedores: Fornecedor[];
  onClose: () => void;
}) {
  const juntar = useJuntarFornecedores();
  const [destinoId, setDestinoId] = useState<string | null>(null);
  const [erroCampo, setErroCampo] = useState<string | null>(null);

  useEffect(() => {
    setDestinoId(null);
    setErroCampo(null);
    juntar.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [origem?.id]);

  const opcoes: ComboboxOption[] = useMemo(
    () =>
      fornecedores
        .filter((f) => f.id !== origem?.id)
        .map((f) => ({
          value: String(f.id),
          label: f.nome,
          description: [f.ativo ? null : "Arquivado", f.pix, contagemDeGastos(f.gastos ?? 0)].filter(Boolean).join(" · "),
          imageShape: "circle",
        })),
    [fornecedores, origem?.id],
  );
  const destino = fornecedores.find((f) => String(f.id) === destinoId) ?? null;

  const confirmar = () => {
    if (!origem) return;
    if (!destino) {
      setErroCampo("Selecione o fornecedor que fica.");
      return;
    }
    setErroCampo(null);
    juntar.mutate(
      { origemId: origem.id, destinoId: destino.id },
      {
        onSuccess: onClose,
        onError: (err) => {
          if (err instanceof ApiRequestError && err.fields?.destino_id) setErroCampo(err.fields.destino_id);
        },
      },
    );
  };

  return (
    <Modal open={origem !== null} onClose={onClose} title="Juntar com outro fornecedor">
      {origem && (
        <div className="space-y-3">
          <p className="text-sm text-ink">
            Escolha o fornecedor que fica. “{origem.nome}” é juntado a ele.
          </p>
          <div>
            <label className={LABEL} htmlFor="juntar-destino">
              Fornecedor que fica
            </label>
            <Combobox
              id="juntar-destino"
              options={opcoes}
              value={destinoId}
              invalid={Boolean(erroCampo)}
              placeholder="Buscar fornecedor…"
              emptyMessage="Nenhum fornecedor encontrado."
              onChange={(valor) => {
                setDestinoId(valor);
                setErroCampo(null);
              }}
            />
            {erroCampo && (
              <p className="mt-1 text-xs text-red" role="alert">
                {erroCampo}
              </p>
            )}
          </div>
          {destino && (
            <p className="rounded-md border border-line bg-surface-2 p-2 text-sm text-ink" role="note">
              {efeitoDeJuntar(origem, destino)}
            </p>
          )}
          {juntar.isError && !erroCampo && (
            <p className="text-sm text-red">{juntar.error?.message || "Não foi possível juntar os fornecedores. Tente novamente."}</p>
          )}
          <div className="flex flex-wrap gap-2 pt-1">
            <Button className="bg-red hover:bg-red/90" loading={juntar.isPending} onClick={confirmar}>
              Juntar fornecedores
            </Button>
            <Button type="button" variant="ghost" onClick={onClose} disabled={juntar.isPending}>
              Cancelar
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}

// ── lista ────────────────────────────────────────────────────────────────────────────────────────

function LinhaFornecedor({
  fornecedor: f,
  salvando,
  onAlterar,
  onJuntar,
  onArquivar,
}: {
  fornecedor: Fornecedor;
  /** Arquivar/reativar em voo nesta linha (o menu fecha no clique; o aviso fica na linha). */
  salvando: boolean;
  onAlterar: () => void;
  onJuntar: () => void;
  onArquivar: () => void;
}) {
  return (
    <li className={`flex items-start gap-2 px-4 py-3 ${salvando ? "opacity-60" : ""}`}>
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="break-words font-medium text-ink">{f.nome}</span>
          {f.categoria_padrao && <Badge tone="accent">{f.categoria_padrao}</Badge>}
          {!f.ativo && <Badge>Arquivado</Badge>}
          {salvando && <span className="text-xs text-muted">Salvando…</span>}
        </div>
        {f.pix ? (
          <div className="flex flex-wrap items-center gap-2 text-sm text-muted">
            <span className="break-all">PIX {f.pix}</span>
            <CopyButton value={f.pix} label={`Copiar a chave PIX de ${f.nome}`} />
          </div>
        ) : (
          <p className="text-sm text-muted">Sem chave PIX</p>
        )}
        <p className="text-xs tabular-nums text-muted">{resumo(f)}</p>
      </div>
      <KebabMenu
        label={`Ações de ${f.nome}`}
        items={[
          { label: "Alterar", onClick: onAlterar },
          { label: "Juntar com outro fornecedor", onClick: onJuntar },
          { label: f.ativo ? "Arquivar" : "Reativar", onClick: onArquivar },
        ]}
      />
    </li>
  );
}

export function FornecedoresPage() {
  const query = useFornecedores();
  const alterar = useAlterarFornecedor();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const [editando, setEditando] = useState<Fornecedor | null>(null);
  const [formAberto, setFormAberto] = useState(false);
  const [juntando, setJuntando] = useState<Fornecedor | null>(null);
  /** Arquivar some com a linha (sem "Mostrar arquivados"): a confirmação fica escrita. */
  const [aviso, setAviso] = useState<string | null>(null);

  const busca = searchParams.get("busca") ?? "";
  const verArquivados = searchParams.get("arquivados") === "1";
  function atualizarUrl(chave: string, valor: string | null) {
    const proximo = new URLSearchParams(searchParams);
    if (valor) proximo.set(chave, valor);
    else proximo.delete(chave);
    setSearchParams(proximo, { replace: true });
  }

  const voltou = useChegouPeloHistorico();
  useRestaurarRolagem(location.key, { restaurar: voltou, pronto: Boolean(query.data) });

  const todos = useMemo(() => query.data?.fornecedores ?? [], [query.data]);
  const arquivados = todos.filter((f) => !f.ativo).length;
  const termos = normalizeSearch(busca).split(/\s+/).filter(Boolean);
  const visiveis = todos.filter((f) => {
    if (!verArquivados && !f.ativo) return false;
    const indice = normalizeSearch([f.nome, f.pix, f.categoria_padrao].filter(Boolean).join(" "));
    return termos.every((t) => indice.includes(t));
  });

  const abrirNovo = () => {
    setEditando(null);
    setFormAberto(true);
  };

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Fornecedores"
        subtitle="Cadastro usado no preenchimento dos gastos extras"
        actions={query.data?.can_manage ? <Button onClick={abrirNovo}>+ Novo fornecedor</Button> : undefined}
      />

      {query.isLoading && (
        <div className="space-y-3">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      )}

      {query.isError && (
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar os fornecedores.
        </div>
      )}

      {query.data && !query.data.can_manage && (
        <Card>
          <CardContent className="p-6 text-center text-sm text-muted">
            O cadastro de fornecedores é gerenciado pelo Financeiro.
          </CardContent>
        </Card>
      )}

      {query.data?.can_manage && (
        <>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <input
              type="search"
              className={`${INPUT} sm:flex-1`}
              placeholder="Buscar por nome, PIX ou categoria"
              aria-label="Buscar fornecedor"
              value={busca}
              onChange={(e) => atualizarUrl("busca", e.target.value || null)}
            />
            {arquivados > 0 && (
              <label className="flex min-h-11 items-center gap-2 text-sm text-ink">
                <input
                  type="checkbox"
                  checked={verArquivados}
                  onChange={(e) => atualizarUrl("arquivados", e.target.checked ? "1" : null)}
                />
                Mostrar arquivados ({arquivados})
              </label>
            )}
          </div>

          <p aria-live="polite" className={aviso ? "text-sm text-ink" : "sr-only"}>
            {aviso ?? ""}
          </p>

          <Card>
            <CardContent className="p-0">
              {visiveis.length === 0 ? (
                <p className="p-6 text-center text-sm text-muted">
                  {todos.length === 0 ? "Nenhum fornecedor cadastrado ainda." : "Nenhum fornecedor encontrado."}
                </p>
              ) : (
                <ul className="divide-y divide-line">
                  {visiveis.map((f) => (
                    <LinhaFornecedor
                      key={f.id}
                      fornecedor={f}
                      salvando={alterar.isPending && alterar.variables?.id === f.id}
                      onAlterar={() => {
                        setEditando(f);
                        setFormAberto(true);
                      }}
                      onJuntar={() => setJuntando(f)}
                      onArquivar={() =>
                        alterar.mutate(
                          { id: f.id, ativo: !f.ativo },
                          {
                            onSuccess: () =>
                              setAviso(f.ativo ? `“${f.nome}” arquivado.` : `“${f.nome}” reativado.`),
                          },
                        )
                      }
                    />
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
          {alterar.isError && (
            <p className="text-sm text-red" role="alert">
              Não foi possível alterar a situação do fornecedor. Tente novamente.
            </p>
          )}
        </>
      )}

      <FornecedorFormModal
        fornecedor={editando}
        categorias={query.data?.categorias ?? []}
        open={formAberto}
        onClose={() => setFormAberto(false)}
      />
      <JuntarModal origem={juntando} fornecedores={todos} onClose={() => setJuntando(null)} />
    </div>
  );
}
