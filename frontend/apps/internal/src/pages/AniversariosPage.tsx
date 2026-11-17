import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { Badge, Button, Card, CardContent, PageHeader, Skeleton } from "@manto/ui";
import { dataCurta, useAniversarios, type Aniversario } from "../lib/baseAutorizada";

function quando(dias: number): string {
  if (dias === 0) return "Hoje";
  if (dias === 1) return "Amanhã";
  return `Em ${dias} dias`;
}

function Linha({ item }: { item: Aniversario }) {
  return (
    <li className="flex items-start justify-between gap-3 py-3">
      <div className="min-w-0">
        <p className="font-medium text-ink">
          {item.primeiro_nome}
          <span className="font-normal text-muted">
            {" "}
            · {item.idade === 1 ? "faz 1 ano" : `faz ${item.idade} anos`}
          </span>
        </p>
        <p className="text-sm text-muted">{dataCurta(item.data).slice(0, 5)}</p>
        <Link
          to={`/clientes/${item.cliente.id}`}
          className="block truncate text-sm text-accent hover:underline"
        >
          {item.cliente.name} · {item.cliente.phone_display}
        </Link>
      </div>
      <Badge tone={item.dias <= 7 ? "gold" : "neutral"}>{quando(item.dias)}</Badge>
    </li>
  );
}

/**
 * Aniversários dos próximos 60 dias (feature 350), só leitura. Entram as crianças com o aceite de
 * aniversário cuja responsável também aceita novidades — sem os dois, o dado não serve para
 * contato. O lembrete automático é outra feature.
 */
export function AniversariosPage() {
  const lista = useAniversarios(60);
  const reduzir = useReducedMotion();
  const itens = lista.data?.items ?? [];

  return (
    <div className="mx-auto max-w-[900px] space-y-4 p-4 sm:p-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/clientes">‹ Clientes</Link>
      </Button>
      <PageHeader
        title="Aniversários"
        subtitle="Próximos 60 dias, só de quem autorizou guardar o aniversário e receber novidades"
      />
      <Card>
        <CardContent className="pt-4">
          {lista.isLoading && <Skeleton className="h-40 w-full" />}
          {lista.isError && (
            <p className="text-sm text-red" role="alert">
              Não foi possível carregar os aniversários. Tente novamente.
            </p>
          )}
          {lista.data && itens.length === 0 && (
            <p className="text-sm text-muted">Nenhum aniversário autorizado nos próximos 60 dias.</p>
          )}
          {itens.length > 0 && (
            <motion.ul
              initial={reduzir ? false : { opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: reduzir ? 0 : 0.2 }}
              className="divide-y divide-line"
            >
              {itens.map((item) => (
                <Linha key={item.crianca_id} item={item} />
              ))}
            </motion.ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
