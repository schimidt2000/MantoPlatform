import { useEffect, useState } from "react";
import { Button, Input } from "@manto/ui";
import { formatBRL } from "@manto/money";
import { mensagemDaApi } from "../../lib/formulariosAdmin";
import {
  usePixConfig,
  usePixResumo,
  usePixSaude,
  useSalvarConfigPix,
  type ConfigPix,
} from "../../lib/pix";

function mesCurto(ym: string): string {
  const [ano, mes] = ym.split("-").map(Number);
  return new Date(ano, mes - 1, 1).toLocaleDateString("pt-BR", { month: "short", year: "2-digit" });
}

/**
 * A faixa que impede a equipe de achar que está coberta quando não está (feature 318): leitura
 * desligada, parada há mais de 1 hora ou com erro de acesso à caixa.
 */
export function SaudeDaLeitura() {
  const saude = usePixSaude();
  const s = saude.data;
  if (!s) return null;
  let aviso: string | null = null;
  if (!s.ativo) aviso = "A leitura dos avisos de PIX está desligada: nada é ligado sozinho.";
  else if (s.alerta === "erro") aviso = `A caixa de e-mail não pôde ser lida: ${s.ultimo_erro ?? "erro desconhecido"}.`;
  else if (s.alerta === "parada") aviso = "A leitura dos avisos de PIX está parada há mais de 1 hora.";
  return (
    <div className="space-y-2">
      {aviso && (
        <div role="alert" className="rounded-md border border-red/40 bg-red-soft px-3 py-2 text-sm text-red">
          {aviso}
        </div>
      )}
      <p className="text-xs text-muted">
        Últimos 7 dias: {s.lidos_7d} aviso(s) lido(s)
        {s.contas_vistas_7d.length > 0 && ` · contas: ${s.contas_vistas_7d.join(", ")}`}
        {s.nao_entendidos_7d > 0 && ` · ${s.nao_entendidos_7d} não entendido(s)`}
        {s.conta_nao_cadastrada_7d > 0 && ` · ${s.conta_nao_cadastrada_7d} de conta não cadastrada`}
        {s.ultima_leitura && ` · última leitura ${new Date(s.ultima_leitura).toLocaleString("pt-BR")}`}
      </p>
    </div>
  );
}

/** Recebido por conta × mês (Financeiro/Superadmin): a base para a pergunta do contador (MEI). */
export function ResumoPorConta() {
  const resumo = usePixResumo(true);
  const r = resumo.data;
  if (resumo.isLoading) return <p className="text-sm text-muted">Carregando…</p>;
  if (!r) return null;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-muted">
            <th className="py-1.5 pr-3 font-medium">Conta</th>
            {r.meses.map((m) => (
              <th key={m} className="py-1.5 pr-3 text-right font-medium">
                {mesCurto(m)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {[...r.contas, { conta: "Sem conta informada", por_mes: r.sem_conta }].map((linha) => (
            <tr key={linha.conta}>
              <td className="py-1.5 pr-3 text-ink">{linha.conta}</td>
              {r.meses.map((m) => (
                <td key={m} className="py-1.5 pr-3 text-right tabular-nums text-ink">
                  {linha.por_mes[m] ? formatBRL(Number(linha.por_mes[m])) : "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-1 text-xs text-muted">
        Pelo mês em que o pagamento foi registrado. Comprovantes manuais só entram na conta certa quando a
        conta é informada.
      </p>
    </div>
  );
}

/** Configuração da leitura (Superadmin): interruptor, números das contas, pagadores próprios. */
export function ConfigPixPainel() {
  const config = usePixConfig(true);
  const salvar = useSalvarConfigPix();
  const [rascunho, setRascunho] = useState<ConfigPix | null>(null);
  const [proprios, setProprios] = useState("");

  useEffect(() => {
    if (config.data) {
      setRascunho(config.data);
      setProprios(config.data.pagadores_proprios.join("\n"));
    }
  }, [config.data]);

  if (!rascunho) return <p className="text-sm text-muted">Carregando…</p>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm text-ink">
          Leitura {rascunho.ativo ? "ligada" : "desligada"}
          {rascunho.ativo && rascunho.ativo_desde && (
            <span className="text-muted"> desde {new Date(rascunho.ativo_desde).toLocaleString("pt-BR")}</span>
          )}
        </span>
        <Button
          size="sm"
          variant={rascunho.ativo ? "outline" : "default"}
          loading={salvar.isPending}
          onClick={() => salvar.mutate({ ativo: !rascunho.ativo })}
        >
          {rascunho.ativo ? "Desligar" : "Ligar a leitura"}
        </Button>
      </div>
      <div>
        <p className="mb-1 text-sm font-medium text-ink">Número de cada conta (como aparece no aviso: "na conta …")</p>
        <div className="grid gap-2 sm:grid-cols-2">
          {rascunho.contas.map((c) => (
            <label key={c.id} className="flex items-center gap-2 text-sm">
              <span className="w-36 shrink-0 text-muted">{c.apelido}</span>
              <Input
                inputMode="numeric"
                value={c.numero_conta ?? ""}
                onChange={(e) =>
                  setRascunho({
                    ...rascunho,
                    contas: rascunho.contas.map((x) =>
                      x.id === c.id ? { ...x, numero_conta: e.target.value.replace(/\D/g, "") } : x,
                    ),
                  })
                }
                placeholder="sem número"
                aria-label={`Número da conta ${c.apelido}`}
              />
            </label>
          ))}
        </div>
      </div>
      <label className="block text-sm">
        <span className="mb-1 block font-medium text-ink">Pagadores próprios (um por linha)</span>
        <span className="mb-1 block text-xs text-muted">
          Transferência entre contas da empresa: nunca é venda. "Prime Dreams" no MEI é tratado à parte (repasse).
        </span>
        <textarea
          className="min-h-24 w-full rounded-md border border-line bg-panel p-2 text-sm text-ink"
          value={proprios}
          onChange={(e) => setProprios(e.target.value)}
        />
      </label>
      <div className="flex items-center gap-3">
        <Button
          size="sm"
          loading={salvar.isPending}
          onClick={() =>
            salvar.mutate({
              pagadores_proprios: proprios.split("\n").map((l) => l.trim()).filter(Boolean),
              contas: rascunho.contas.map((c) => ({ id: c.id, numero_conta: c.numero_conta })),
            })
          }
        >
          Salvar
        </Button>
        {salvar.isSuccess && <span className="text-sm text-green">Salvo.</span>}
        {salvar.isError && (
          <span role="alert" className="text-sm text-red">
            {mensagemDaApi(salvar.error, "Não foi possível salvar.")}
          </span>
        )}
      </div>
    </div>
  );
}
