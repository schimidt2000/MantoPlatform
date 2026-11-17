import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { ApiRequestError } from "@manto/api-client";
import {
  Badge,
  Button,
  Card,
  CardContent,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  PageHeader,
  Skeleton,
} from "@manto/ui";
import {
  useParceiros,
  useSalvarParceiro,
  type DadosDoParceiro,
  type Parceiro,
} from "../lib/baseAutorizada";

const VAZIO: DadosDoParceiro = {
  nome: "",
  tipo: "",
  contato: "",
  telefone: "",
  email: "",
  comissao_percentual: "",
  observacao: "",
};

function percentual(valor: string): string {
  return `${Number(valor).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%`;
}

function dadosDe(parceiro: Parceiro): DadosDoParceiro {
  return {
    nome: parceiro.nome,
    tipo: parceiro.tipo,
    contato: parceiro.contato ?? "",
    telefone: parceiro.telefone ?? "",
    email: parceiro.email ?? "",
    comissao_percentual: Number(parceiro.comissao_percentual).toLocaleString("pt-BR"),
    observacao: parceiro.observacao ?? "",
  };
}

function Campo({
  rotulo,
  erro,
  children,
}: {
  rotulo: string;
  erro?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm text-muted">{rotulo}</span>
      {children}
      {erro && (
        <p className="mt-1 text-sm text-red" role="alert">
          {erro}
        </p>
      )}
    </label>
  );
}

function ParceiroDialog({
  parceiro,
  tipos,
  aberto,
  onFechar,
  onSalvo,
}: {
  parceiro: Parceiro | null;
  tipos: { valor: string; rotulo: string }[];
  aberto: boolean;
  onFechar: () => void;
  onSalvo: (mensagem: string) => void;
}) {
  const [dados, setDados] = useState<DadosDoParceiro>(VAZIO);
  const salvar = useSalvarParceiro();

  useEffect(() => {
    if (aberto) {
      setDados(parceiro ? dadosDe(parceiro) : VAZIO);
      salvar.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aberto, parceiro]);

  const campos = salvar.error instanceof ApiRequestError ? (salvar.error.fields ?? {}) : {};
  const erroGeral =
    salvar.error && Object.keys(campos).length === 0 ? "Não foi possível salvar. Tente novamente." : null;
  const mudar = (campo: keyof DadosDoParceiro) => (valor: string) =>
    setDados((atual) => ({ ...atual, [campo]: valor }));

  return (
    <Dialog open={aberto} onOpenChange={(abrir) => !abrir && !salvar.isPending && onFechar()}>
      <DialogContent open={aberto} className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{parceiro ? "Editar parceiro" : "Novo parceiro"}</DialogTitle>
          <DialogDescription>
            A comissão é a declarada ao parceiro e à cliente. Esta tela não paga ninguém: o repasse de
            um evento continua sendo o BV.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <Campo rotulo="Nome" erro={campos.nome}>
            <Input value={dados.nome} onChange={(e) => mudar("nome")(e.target.value)} maxLength={160} />
          </Campo>
          <Campo rotulo="Tipo" erro={campos.tipo}>
            <select
              value={dados.tipo}
              onChange={(e) => mudar("tipo")(e.target.value)}
              className="h-11 w-full rounded-md border border-line bg-panel px-2 text-sm text-ink"
            >
              <option value="">Selecione…</option>
              {tipos.map((tipo) => (
                <option key={tipo.valor} value={tipo.valor}>
                  {tipo.rotulo}
                </option>
              ))}
            </select>
          </Campo>
          <Campo rotulo="Comissão declarada (%)" erro={campos.comissao_percentual}>
            <Input
              inputMode="decimal"
              value={dados.comissao_percentual}
              onChange={(e) => mudar("comissao_percentual")(e.target.value)}
              placeholder="Ex.: 10"
            />
          </Campo>
          <div className="grid gap-3 sm:grid-cols-2">
            <Campo rotulo="Contato" erro={campos.contato}>
              <Input value={dados.contato} onChange={(e) => mudar("contato")(e.target.value)} />
            </Campo>
            <Campo rotulo="Telefone" erro={campos.telefone}>
              <Input
                inputMode="tel"
                value={dados.telefone}
                onChange={(e) => mudar("telefone")(e.target.value)}
              />
            </Campo>
          </div>
          <Campo rotulo="E-mail" erro={campos.email}>
            <Input type="email" value={dados.email} onChange={(e) => mudar("email")(e.target.value)} />
          </Campo>
          <Campo rotulo="Observação">
            <textarea
              value={dados.observacao}
              onChange={(e) => mudar("observacao")(e.target.value)}
              className="min-h-16 w-full rounded-md border border-line bg-panel p-2 text-sm text-ink"
            />
          </Campo>
          {erroGeral && (
            <p className="text-sm text-red" role="alert">
              {erroGeral}
            </p>
          )}
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onFechar} disabled={salvar.isPending}>
            Cancelar
          </Button>
          <Button
            loading={salvar.isPending}
            onClick={() =>
              salvar.mutate(
                { id: parceiro?.id ?? null, dados },
                {
                  onSuccess: () => {
                    onFechar();
                    onSalvo(parceiro ? "Parceiro salvo." : "Parceiro cadastrado.");
                  },
                },
              )
            }
          >
            Salvar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Parceiros (feature 350): buffets, assessorias e agências que trazem clientes, com a comissão
 * declarada. Comercial e Superadmin cadastram; o Financeiro só consulta. Não se exclui: desativa-se,
 * e as fichas já ligadas continuam mostrando o nome.
 */
export function ParceirosPage() {
  const [comInativos, setComInativos] = useState(false);
  const lista = useParceiros(comInativos);
  const salvar = useSalvarParceiro();
  const [editando, setEditando] = useState<Parceiro | null>(null);
  const [novo, setNovo] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const reduzir = useReducedMotion();
  const podeEditar = Boolean(lista.data?.flags.pode_editar);
  const itens = lista.data?.items ?? [];

  return (
    <div className="mx-auto max-w-[900px] space-y-4 p-4 sm:p-6">
      <Button asChild variant="ghost" size="sm">
        <Link to="/clientes">‹ Clientes</Link>
      </Button>
      <PageHeader
        title="Parceiros"
        subtitle="Buffets, assessorias e agências, com a comissão declarada"
        actions={podeEditar && <Button onClick={() => setNovo(true)}>Novo parceiro</Button>}
      />
      {aviso && (
        <p className="rounded-md bg-green-soft px-3 py-2 text-sm text-green" role="status">
          {aviso}
        </p>
      )}
      <Card>
        <CardContent className="pt-4">
          <label className="mb-2 flex min-h-11 cursor-pointer items-center gap-2 text-sm text-muted">
            <input
              type="checkbox"
              checked={comInativos}
              onChange={(e) => setComInativos(e.target.checked)}
              className="h-4 w-4 accent-accent"
            />
            Mostrar inativos
          </label>
          {lista.isLoading && <Skeleton className="h-32 w-full" />}
          {lista.isError && (
            <p className="text-sm text-red" role="alert">
              Não foi possível carregar os parceiros. Tente novamente.
            </p>
          )}
          {lista.data && itens.length === 0 && (
            <p className="text-sm text-muted">Nenhum parceiro cadastrado ainda.</p>
          )}
          {itens.length > 0 && (
            <motion.ul
              initial={reduzir ? false : { opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: reduzir ? 0 : 0.2 }}
              className="divide-y divide-line"
            >
              {itens.map((parceiro) => (
                <li key={parceiro.id} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-ink">
                      {parceiro.nome}
                      {!parceiro.ativo && <span className="font-normal text-muted"> (inativo)</span>}
                    </p>
                    <p className="text-sm text-muted">
                      {[parceiro.tipo_label, parceiro.contato, parceiro.telefone].filter(Boolean).join(" · ")}
                    </p>
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      <Badge tone="gold">Comissão {percentual(parceiro.comissao_percentual)}</Badge>
                      <Badge>
                        {parceiro.clientes === 1 ? "1 cliente" : `${parceiro.clientes} clientes`}
                      </Badge>
                    </div>
                  </div>
                  {podeEditar && (
                    <div className="flex shrink-0 gap-2">
                      <Button variant="outline" size="sm" className="min-h-11" onClick={() => setEditando(parceiro)}>
                        Editar
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="min-h-11"
                        loading={salvar.isPending && salvar.variables?.id === parceiro.id}
                        onClick={() =>
                          salvar.mutate(
                            { id: parceiro.id, dados: { ativo: !parceiro.ativo } },
                            {
                              onSuccess: () =>
                                setAviso(parceiro.ativo ? "Parceiro desativado." : "Parceiro reativado."),
                            },
                          )
                        }
                      >
                        {parceiro.ativo ? "Desativar" : "Reativar"}
                      </Button>
                    </div>
                  )}
                </li>
              ))}
            </motion.ul>
          )}
        </CardContent>
      </Card>
      <ParceiroDialog
        parceiro={editando}
        tipos={lista.data?.tipos ?? []}
        aberto={novo || editando !== null}
        onFechar={() => {
          setNovo(false);
          setEditando(null);
        }}
        onSalvo={setAviso}
      />
    </div>
  );
}
