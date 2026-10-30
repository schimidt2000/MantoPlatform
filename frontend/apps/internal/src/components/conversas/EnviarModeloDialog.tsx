import { useEffect, useMemo, useRef, useState } from "react";
import { ApiRequestError } from "@manto/api-client";
import {
  Button,
  Combobox,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Skeleton,
} from "@manto/ui";
import {
  mensagemDoErro,
  novaChaveDeEnvio,
  useEnviarModelo,
  useModelos,
  type ModeloAprovado,
} from "../../lib/conversas";

/**
 * "Enviar modelo" (feature 325, FR-012): o único jeito de falar com quem sumiu há mais de 24 h.
 * Os modelos são criados e aprovados no gerenciador da Meta; aqui só se escolhe e preenche as
 * variáveis. A prévia mostra o texto exatamente como a cliente vai ler.
 *
 * Erro sempre aponta o campo (Princípio V): o modelo não escolhido realça o seletor, a variável
 * vazia é realçada e recebe o foco — tanto na conferência local quanto nos `fields` do 422.
 */

interface EnviarModeloDialogProps {
  conversaId: number;
  nomeDoContato: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function chaveDoModelo(modelo: ModeloAprovado): string {
  return `${modelo.nome}|${modelo.idioma}`;
}

function textoFinal(modelo: ModeloAprovado, valores: string[]): string {
  return modelo.texto.replace(/\{\{\s*(\w+)\s*\}\}/g, (inteiro, nome: string) => {
    const indice = modelo.nomes_das_variaveis.indexOf(nome);
    return valores[indice]?.trim() || inteiro;
  });
}

/** Princípio XV, contagem: "a variável" no singular, "as N variáveis" no plural. */
function textoDasVariaveis(quantidade: number): string {
  return quantidade === 1 ? "Preencha a variável do modelo." : `Preencha as ${quantidade} variáveis do modelo.`;
}

export function EnviarModeloDialog({ conversaId, nomeDoContato, open, onOpenChange }: EnviarModeloDialogProps) {
  const modelos = useModelos(open);
  const enviar = useEnviarModelo(conversaId);
  const [escolhido, setEscolhido] = useState<string | null>(null);
  const [valores, setValores] = useState<string[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  const [modeloInvalido, setModeloInvalido] = useState(false);
  const [variaveisInvalidas, setVariaveisInvalidas] = useState<boolean[]>([]);
  const campos = useRef<(HTMLInputElement | null)[]>([]);
  // A chave é do rascunho (FR-018): o reenvio depois de uma resposta perdida não manda duas vezes.
  const chaveDoRascunho = useRef<string | null>(null);

  const modelo = useMemo(
    () => modelos.data?.modelos.find((m) => chaveDoModelo(m) === escolhido) ?? null,
    [modelos.data, escolhido],
  );

  useEffect(() => {
    if (!open) {
      setEscolhido(null);
      setErro(null);
      setModeloInvalido(false);
      chaveDoRascunho.current = null;
    }
  }, [open]);

  useEffect(() => {
    // A primeira variável quase sempre é o nome: já vem com o primeiro nome do contato.
    if (!modelo) return;
    const primeiroNome = nomeDoContato.split(/\s+/)[0] ?? "";
    setValores(Array.from({ length: modelo.variaveis }, (_, i) => (i === 0 ? primeiroNome : "")));
    setVariaveisInvalidas(Array.from({ length: modelo.variaveis }, () => false));
  }, [modelo, nomeDoContato]);

  const apontarVariaveisVazias = (atual: ModeloAprovado) => {
    const vazias = valores.map((v) => !v.trim());
    setVariaveisInvalidas(vazias);
    setErro(textoDasVariaveis(atual.variaveis));
    campos.current[vazias.indexOf(true)]?.focus();
  };

  const aoFalhar = (falha: unknown, atual: ModeloAprovado) => {
    const campo = falha instanceof ApiRequestError ? falha.fields : undefined;
    if (campo?.nome) setModeloInvalido(true);
    if (campo?.variaveis) {
      apontarVariaveisVazias(atual);
      return;
    }
    setErro(mensagemDoErro(falha, "Não foi possível enviar o modelo. Tente novamente."));
  };

  const aoEnviar = () => {
    if (!modelo) {
      setModeloInvalido(true);
      setErro("Selecione um modelo aprovado.");
      return;
    }
    if (valores.some((v) => !v.trim())) {
      apontarVariaveisVazias(modelo);
      return;
    }
    setErro(null);
    chaveDoRascunho.current ??= novaChaveDeEnvio();
    enviar.mutate(
      { nome: modelo.nome, idioma: modelo.idioma, variaveis: valores, chave_envio: chaveDoRascunho.current },
      { onSuccess: () => onOpenChange(false), onError: (falha) => aoFalhar(falha, modelo) },
    );
  };

  const alterarValor = (indice: number, valor: string) => {
    chaveDoRascunho.current = null;
    setValores((atuais) => atuais.map((v, i) => (i === indice ? valor : v)));
    setVariaveisInvalidas((atuais) => atuais.map((v, i) => (i === indice ? false : v)));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent open={open} className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Enviar modelo</DialogTitle>
          <DialogDescription>
            Só modelos aprovados pela Meta podem ser enviados depois de 24 horas sem resposta da cliente.
          </DialogDescription>
        </DialogHeader>

        {modelos.isLoading ? (
          <Skeleton className="h-11 w-full" />
        ) : modelos.isError ? (
          <div className="space-y-2">
            <p role="alert" className="text-sm text-red">
              Não foi possível carregar os modelos. Tente novamente.
            </p>
            <Button type="button" variant="outline" loading={modelos.isFetching} onClick={() => void modelos.refetch()}>
              Tentar novamente
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="space-y-1.5">
              <label htmlFor="modelo-escolhido" className="text-sm font-medium">
                Modelo
              </label>
              <Combobox
                id="modelo-escolhido"
                options={(modelos.data?.modelos ?? []).map((m) => ({
                  value: chaveDoModelo(m),
                  label: m.nome,
                  description: m.texto,
                }))}
                value={escolhido}
                onChange={(valor) => {
                  setEscolhido(valor);
                  setModeloInvalido(false);
                  setErro(null);
                  chaveDoRascunho.current = null;
                }}
                invalid={modeloInvalido}
                placeholder="Selecione o modelo"
                emptyMessage="Nenhum modelo aprovado encontrado."
              />
            </div>
            {modelo
              ? valores.map((valor, indice) => (
                  <div key={`${chaveDoModelo(modelo)}-${indice}`} className="space-y-1.5">
                    <label htmlFor={`variavel-${indice}`} className="text-sm font-medium">
                      Variável {`{{${modelo.nomes_das_variaveis[indice]}}}`}
                    </label>
                    <Input
                      id={`variavel-${indice}`}
                      ref={(elemento) => {
                        campos.current[indice] = elemento;
                      }}
                      value={valor}
                      aria-invalid={variaveisInvalidas[indice] ? true : undefined}
                      className="aria-[invalid=true]:border-red aria-[invalid=true]:ring-1 aria-[invalid=true]:ring-red"
                      onChange={(e) => alterarValor(indice, e.target.value)}
                    />
                  </div>
                ))
              : null}
            {modelo ? (
              <div className="rounded-md border border-line bg-surface p-3 text-sm">
                <p className="mb-1 text-xs font-medium text-muted">Prévia</p>
                <p className="whitespace-pre-wrap">{textoFinal(modelo, valores)}</p>
              </div>
            ) : null}
          </div>
        )}

        {erro ? (
          <p role="alert" className="text-sm text-red">
            {erro}
          </p>
        ) : null}
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={enviar.isPending}>
            Cancelar
          </Button>
          <Button type="button" onClick={aoEnviar} loading={enviar.isPending}>
            {enviar.isPending ? "Enviando…" : "Enviar modelo"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
