import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  PageHeader,
  Skeleton,
} from "@manto/ui";
import { formatBRL } from "@manto/money";
import { ApiRequestError } from "@manto/api-client";
import { MemoriaDeCalculo } from "../components/MemoriaDeCalculo";
import {
  useEnviarEmailOrcamento,
  useOrcamentoDetalhe,
  useOrcamentoPdf,
  type Quote,
} from "../lib/orcamento";

/**
 * Orçamento gerado — sucessora React de `app/templates/orcamento/resultado.html`.
 *
 * É a tela para onde "Gerar Orçamento" leva depois de salvar: mensagem pronta para o WhatsApp,
 * detalhamento do transporte, resumo por duração, memória de cálculo, download do PDF e envio por
 * e-mail. A calculadora sozinha parava no "Orçamento salvo" e não dava saída nenhuma para
 * apresentar a proposta à cliente.
 */

function brl(v: number): string {
  return `R$ ${formatBRL(v)}`;
}

/** Durações marcadas no orçamento + a duração personalizada, quando houver. */
function duracoesVisiveis(quote: Quote): { label: string; total: number; destaque?: boolean }[] {
  const linhas: { label: string; total: number; destaque?: boolean }[] = [
    { label: "1 hora", total: quote.total_1h, mostrar: quote.show_1h },
    { label: "2 horas", total: quote.total_2h, mostrar: quote.show_2h },
    { label: "3 horas", total: quote.total_3h, mostrar: quote.show_3h },
    { label: "4 horas", total: quote.total_4h, mostrar: quote.show_4h },
  ]
    .filter((l) => l.mostrar)
    .map(({ label, total }) => ({ label, total }) as { label: string; total: number });

  if (quote.total_custom) {
    linhas.push({ label: `${quote.duracao_custom} horas`, total: quote.total_custom, destaque: true });
  }
  return linhas;
}

function MensagemWhatsApp({ texto }: { texto: string }) {
  const [copiado, setCopiado] = useState(false);

  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(texto);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      // Clipboard bloqueado (contexto inseguro / permissão negada): o <pre> é selecionável,
      // então o caminho manual continua disponível — não vale travar a tela por isso.
      setCopiado(false);
    }
  };

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-2 space-y-0">
        <CardTitle>Mensagem para WhatsApp</CardTitle>
        <Button size="sm" onClick={copiar}>
          {copiado ? "Copiado!" : "Copiar mensagem"}
        </Button>
      </CardHeader>
      <CardContent>
        <pre className="max-h-[26rem] overflow-y-auto whitespace-pre-wrap break-words rounded-md border border-line bg-surface-2 p-4 text-sm leading-relaxed text-ink">
          {texto}
        </pre>
      </CardContent>
    </Card>
  );
}

function EnvioPorEmail({ entryId }: { entryId: number }) {
  const email = useEnviarEmailOrcamento();
  const [destinatario, setDestinatario] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviado, setEnviado] = useState(false);

  const enviar = () => {
    const alvo = destinatario.trim();
    if (!alvo.includes("@")) {
      setErro("Digite um e-mail válido.");
      return;
    }
    setErro(null);
    email.mutate(
      { id: entryId, to: alvo },
      {
        onSuccess: () => setEnviado(true),
        onError: (err) =>
          setErro(err instanceof ApiRequestError ? err.message : "Não foi possível enviar agora."),
      },
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Enviar por e-mail</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted">
          O PDF vai como anexo, a partir de contato@mantoproducoes.com.br.
        </p>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Input
            type="email"
            placeholder="cliente@email.com"
            value={destinatario}
            onChange={(e) => {
              setDestinatario(e.target.value);
              setEnviado(false);
            }}
            className="flex-1"
          />
          <Button onClick={enviar} loading={email.isPending} disabled={enviado}>
            {enviado ? "Enviado!" : "Enviar"}
          </Button>
        </div>
        {erro && (
          <p className="text-sm text-red" role="alert">
            {erro}
          </p>
        )}
        {enviado && <p className="text-sm text-green">Orçamento enviado para {destinatario}.</p>}
      </CardContent>
    </Card>
  );
}

export function OrcamentoResultadoPage() {
  const { id } = useParams<{ id: string }>();
  const entryId = Number(id);
  const detalhe = useOrcamentoDetalhe(Number.isFinite(entryId) ? entryId : null);
  const pdf = useOrcamentoPdf();

  if (detalhe.isLoading) {
    return (
      <div className="mx-auto max-w-4xl space-y-4 p-4 sm:p-6">
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (detalhe.isError || !detalhe.data) {
    return (
      <div className="mx-auto max-w-4xl p-4 sm:p-6">
        <div className="rounded-md bg-red-soft px-4 py-3 text-sm text-red" role="alert">
          Não foi possível carregar este orçamento.
        </div>
      </div>
    );
  }

  const { quote } = detalhe.data;
  const transporte = quote.transport_breakdown;

  return (
    <div className="mx-auto max-w-4xl space-y-4 p-4 sm:p-6">
      <PageHeader
        title="Orçamento gerado"
        subtitle={[quote.client_name, quote.fmt_date, quote.event_location]
          .filter(Boolean)
          .join(" · ")}
        className="mb-0"
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="ghost" size="sm" asChild>
              <Link to="/orcamento">Novo orçamento</Link>
            </Button>
            <Button variant="ghost" size="sm" asChild>
              <Link to={`/orcamento?recalcular_id=${entryId}`}>Recalcular</Link>
            </Button>
            <Button
              variant="outline"
              size="sm"
              loading={pdf.isPending}
              onClick={() => pdf.mutate({ id: entryId, clientName: quote.client_name })}
            >
              Baixar PDF
            </Button>
          </div>
        }
      />

      <MensagemWhatsApp texto={quote.message} />

      <Card>
        <CardHeader>
          <CardTitle>Resumo de valores</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {duracoesVisiveis(quote).map(({ label, total, destaque }) => (
              <div
                key={label}
                className={`rounded-md p-3 text-center ${
                  destaque ? "border-2 border-gold bg-surface-2" : "border border-line"
                }`}
              >
                <p className="text-xs uppercase text-muted">{label}</p>
                <p className="text-lg font-semibold text-ink">{brl(total)}</p>
              </div>
            ))}
          </div>
          {quote.nota_fiscal && (
            <p className="mt-3 text-sm text-muted">🧾 Valores com Nota Fiscal inclusa.</p>
          )}
        </CardContent>
      </Card>

      {quote.fora_sp && transporte && (
        <Card>
          <CardHeader>
            <CardTitle>Detalhamento do transporte</CardTitle>
            {quote.deslocamento_responsavel === "cliente" && (
              <p className="text-xs text-muted">
                Deslocamento por conta da contratante — van/carro não incluído.
              </p>
            )}
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              {[
                // Modo "cliente": o veículo não foi vendido — só os adicionais da equipe.
                ...(quote.deslocamento_responsavel === "cliente"
                  ? []
                  : [["Veículo", transporte.transporte] as [string, number]]),
                ["Adicional fora de SP", transporte.adicional_fora_sp],
                ["Adicional show", transporte.adicional_show],
              ].map(([label, valor]) => (
                <div key={label as string} className="rounded-md border border-line p-3">
                  <p className="text-xs uppercase text-muted">{label}</p>
                  <p className="text-base font-semibold text-ink">{brl(valor as number)}</p>
                </div>
              ))}
            </div>
            <p className="mt-3 border-t border-line pt-3 text-center font-semibold text-ink">
              Total do transporte: {brl(transporte.total)}
            </p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Memória de cálculo</CardTitle>
        </CardHeader>
        <CardContent>
          {quote.personalizado && (
            <p className="mb-3 text-sm text-muted">
              Orçamento personalizado
              {quote.personalizado_criterio === "multiplicador"
                ? " por multiplicador sobre o cachê-base"
                : " com valor final definido manualmente"}
              . Transporte, Nota Fiscal e acréscimos não são somados.
            </p>
          )}
          <MemoriaDeCalculo linhas={quote.memoria} />
        </CardContent>
      </Card>

      <EnvioPorEmail entryId={entryId} />
    </div>
  );
}
