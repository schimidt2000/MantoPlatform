import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Banknote,
  CalendarCheck,
  ClipboardList,
  FileText,
  Megaphone,
  MessageCircle,
  Star,
  UserPlus,
} from "lucide-react";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Skeleton,
} from "@manto/ui";
import { useLinhaDoTempo, type MarcoDaFicha } from "../lib/clientes";

const ICONE: Record<MarcoDaFicha["tipo"], typeof UserPlus> = {
  entrada: UserPlus,
  contato: MessageCircle,
  anuncio: Megaphone,
  orcamento: FileText,
  formulario: ClipboardList,
  evento: CalendarCheck,
  pagamento: Banknote,
  avaliacao: Star,
};

const DESTINO: Record<
  NonNullable<MarcoDaFicha["link"]>["tipo"],
  { rotulo: string; href: (id: number) => string }
> = {
  conversa: { rotulo: "Abrir conversa", href: (id) => `/conversas?c=${id}` },
  orcamento: { rotulo: "Ver orçamento", href: (id) => `/orcamento/${id}` },
  evento: { rotulo: "Ver evento", href: (id) => `/events/${id}` },
};

// O suficiente para a história recente sem empurrar os outros cartões; o resto abre num toque.
const PRIMEIROS = 10;

/** A data e a hora do marco no fuso de São Paulo (o `quando` vem com o fuso da fonte). */
function quandoLegivel(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", {
    timeZone: "America/Sao_Paulo",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * A linha do tempo da ficha (feature 335): só os marcos — entrada, contatos, anúncios, orçamentos,
 * formulários, eventos, pagamentos e avaliações —, do mais novo para o mais antigo, cada um com o
 * link para o lugar de origem quando a pessoa pode abri-lo. A conversa em si fica nas Conversas.
 */
export function LinhaDoTempoDaFicha({ clientId }: { clientId: number }) {
  const query = useLinhaDoTempo(clientId);
  const [todos, setTodos] = useState(false);
  const marcos = query.data?.marcos ?? [];
  const visiveis = todos ? marcos : marcos.slice(0, PRIMEIROS);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Linha do tempo</CardTitle>
      </CardHeader>
      <CardContent>
        {query.isLoading && (
          <div className="space-y-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-2/3" />
          </div>
        )}
        {query.isError && (
          <p className="text-sm text-red" role="alert">
            Não foi possível carregar a linha do tempo. Tente novamente.
          </p>
        )}
        {query.data && marcos.length === 0 && (
          <p className="text-sm text-muted">Nenhum marco ainda.</p>
        )}
        {visiveis.length > 0 && (
          <ol className="relative space-y-3 border-l border-line pl-5">
            {visiveis.map((marco, i) => {
              const Icone = ICONE[marco.tipo];
              const destino = marco.link ? DESTINO[marco.link.tipo] : null;
              return (
                <li
                  key={`${marco.tipo}-${marco.quando}-${i}`}
                  className="relative text-sm"
                >
                  <span
                    aria-hidden
                    className="absolute -left-[31px] top-0.5 flex h-5 w-5 items-center justify-center rounded-full border border-line bg-panel text-muted"
                  >
                    <Icone className="h-3 w-3" />
                  </span>
                  <p className="flex flex-wrap items-baseline gap-x-2">
                    <span className="font-medium text-ink">{marco.titulo}</span>
                    <span className="text-xs tabular-nums text-muted">
                      {quandoLegivel(marco.quando)}
                    </span>
                  </p>
                  {marco.detalhe && (
                    <p className="break-words text-muted">{marco.detalhe}</p>
                  )}
                  {destino && marco.link && (
                    <Link
                      to={destino.href(marco.link.id)}
                      className="text-xs text-accent hover:underline"
                    >
                      {destino.rotulo}
                    </Link>
                  )}
                </li>
              );
            })}
          </ol>
        )}
        {marcos.length > PRIMEIROS && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="mt-2"
            onClick={() => setTodos((v) => !v)}
          >
            {todos ? "Mostrar menos" : `Mostrar todos (${marcos.length})`}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
