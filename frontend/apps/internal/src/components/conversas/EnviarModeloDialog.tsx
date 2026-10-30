import { useEffect, useMemo, useState } from "react";
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

export function EnviarModeloDialog({ conversaId, nomeDoContato, open, onOpenChange }: EnviarModeloDialogProps) {
  const modelos = useModelos(open);
  const enviar = useEnviarModelo(conversaId);
  const [escolhido, setEscolhido] = useState<string | null>(null);
  const [valores, setValores] = useState<string[]>([]);
  const [erro, setErro] = useState<string | null>(null);

  const modelo = useMemo(
    () => modelos.data?.modelos.find((m) => chaveDoModelo(m) === escolhido) ?? null,
    [modelos.data, escolhido],
  );

  useEffect(() => {
    if (!open) {
      setEscolhido(null);
      setErro(null);
    }
  }, [open]);

  useEffect(() => {
    // A primeira variável quase sempre é o nome: já vem com o primeiro nome do contato.
    if (!modelo) return;
    const primeiroNome = nomeDoContato.split(/\s+/)[0] ?? "";
    setValores(Array.from({ length: modelo.variaveis }, (_, i) => (i === 0 ? primeiroNome : "")));
  }, [modelo, nomeDoContato]);

  const faltando = modelo ? valores.some((v) => !v.trim()) : true;

  const aoEnviar = () => {
    if (!modelo) {
      setErro("Selecione um modelo aprovado.");
      return;
    }
    if (faltando) {
      setErro(`Preencha as ${modelo.variaveis} variáveis do modelo.`);
      return;
    }
    setErro(null);
    enviar.mutate(
      { nome: modelo.nome, idioma: modelo.idioma, variaveis: valores, chave_envio: novaChaveDeEnvio() },
      {
        onSuccess: () => onOpenChange(false),
        onError: (falha) => setErro(mensagemDoErro(falha, "Não foi possível enviar o modelo. Tente novamente.")),
      },
    );
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
          <p role="alert" className="text-sm text-red">
            Não foi possível carregar os modelos. Tente novamente.
          </p>
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
                onChange={(valor) => setEscolhido(valor)}
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
                      value={valor}
                      onChange={(e) =>
                        setValores((atuais) => atuais.map((v, i) => (i === indice ? e.target.value : v)))
                      }
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
          <Button type="button" onClick={aoEnviar} loading={enviar.isPending} disabled={!modelo}>
            {enviar.isPending ? "Enviando…" : "Enviar modelo"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
