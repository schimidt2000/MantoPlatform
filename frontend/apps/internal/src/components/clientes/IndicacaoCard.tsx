import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ApiRequestError } from "@manto/api-client";
import { Button, Card, CardContent, CardHeader, CardTitle, Combobox } from "@manto/ui";
import { useClientSearch } from "../../lib/clientes";
import {
  useDefinirIndicacao,
  useParceiros,
  type FichaResumida,
  type ParceiroResumido,
} from "../../lib/baseAutorizada";

export interface IndicacaoCardProps {
  clientId: number;
  indicadoPor: FichaResumida | null;
  indicacoes: FichaResumida[];
  parceiro: ParceiroResumido | null;
  podeEditar: boolean;
}

/**
 * Quem indicou esta cliente, quem ela indicou e por qual parceiro chegou (feature 350).
 *
 * Selecionar no combobox já salva (molde do `AssociarDialog`); "Remover" tira o vínculo sem apagar
 * a outra ficha nem o parceiro.
 */
export function IndicacaoCard({ clientId, indicadoPor, indicacoes, parceiro, podeEditar }: IndicacaoCardProps) {
  const [busca, setBusca] = useState("");
  const clientes = useClientSearch(busca);
  const parceiros = useParceiros();
  const definir = useDefinirIndicacao(clientId);

  const opcoesDeFicha = useMemo(
    () =>
      (clientes.data ?? [])
        .filter((c) => c.id !== clientId)
        .map((c) => ({ value: String(c.id), label: c.name, description: c.phone_display })),
    [clientes.data, clientId],
  );
  const opcoesDeParceiro = useMemo(
    () =>
      (parceiros.data?.items ?? []).map((p) => ({
        value: String(p.id),
        label: p.nome,
        description: `${p.tipo_label} · comissão declarada ${Number(p.comissao_percentual).toLocaleString("pt-BR")}%`,
      })),
    [parceiros.data],
  );
  const campos = definir.error instanceof ApiRequestError ? (definir.error.fields ?? {}) : {};
  const erroGeral =
    definir.error && Object.keys(campos).length === 0 ? "Não foi possível salvar. Tente novamente." : null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Indicação e parceiro</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <section className="space-y-1">
          <h3 className="font-medium text-ink">Indicado por</h3>
          {indicadoPor ? (
            <div className="flex min-h-11 items-center justify-between gap-2">
              <Link to={`/clientes/${indicadoPor.id}`} className="truncate text-accent hover:underline">
                {indicadoPor.name}
              </Link>
              {podeEditar && (
                <Button
                  variant="ghost"
                  size="sm"
                  loading={definir.isPending}
                  onClick={() => definir.mutate({ indicado_por_id: null })}
                >
                  Remover
                </Button>
              )}
            </div>
          ) : (
            <p className="text-muted">Nenhuma indicação registrada.</p>
          )}
          {podeEditar && (
            <Combobox
              options={opcoesDeFicha}
              value={null}
              onChange={(valor) => valor !== null && definir.mutate({ indicado_por_id: Number(valor) })}
              onQueryChange={setBusca}
              loading={clientes.isFetching}
              placeholder="Buscar quem indicou, por nome ou telefone…"
              hintMessage={busca.trim().length < 2 ? "Digite ao menos 2 letras." : undefined}
              emptyMessage="Nenhuma cliente encontrada."
              invalid={Boolean(campos.indicado_por_id)}
              aria-label="Indicado por"
            />
          )}
          {campos.indicado_por_id && (
            <p className="text-red" role="alert">
              {campos.indicado_por_id}
            </p>
          )}
        </section>

        {indicacoes.length > 0 && (
          <section className="space-y-1 border-t border-line pt-3">
            <h3 className="font-medium text-ink">Indicou</h3>
            <ul className="space-y-1">
              {indicacoes.map((ficha) => (
                <li key={ficha.id}>
                  <Link to={`/clientes/${ficha.id}`} className="text-accent hover:underline">
                    {ficha.name}
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className="space-y-1 border-t border-line pt-3">
          <h3 className="font-medium text-ink">Parceiro</h3>
          {parceiro ? (
            <div className="flex min-h-11 items-center justify-between gap-2">
              <span className="truncate text-ink">
                {parceiro.nome}
                <span className="text-muted">
                  {" "}
                  · {parceiro.tipo_label}
                  {parceiro.ativo ? "" : " (inativo)"}
                </span>
              </span>
              {podeEditar && (
                <Button
                  variant="ghost"
                  size="sm"
                  loading={definir.isPending}
                  onClick={() => definir.mutate({ parceiro_id: null })}
                >
                  Remover
                </Button>
              )}
            </div>
          ) : (
            <p className="text-muted">Nenhum parceiro ligado.</p>
          )}
          {podeEditar && (
            <Combobox
              options={opcoesDeParceiro}
              value={null}
              onChange={(valor) => valor !== null && definir.mutate({ parceiro_id: Number(valor) })}
              loading={parceiros.isLoading}
              placeholder="Selecionar parceiro…"
              emptyMessage="Nenhum parceiro cadastrado. Cadastre em Clientes › Parceiros."
              invalid={Boolean(campos.parceiro_id)}
              aria-label="Parceiro"
            />
          )}
          {campos.parceiro_id && (
            <p className="text-red" role="alert">
              {campos.parceiro_id}
            </p>
          )}
        </section>
        {erroGeral && (
          <p className="text-red" role="alert">
            {erroGeral}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
