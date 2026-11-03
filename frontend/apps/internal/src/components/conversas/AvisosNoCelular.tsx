import { useEffect, useState } from "react";
import { Bell, BellRing } from "lucide-react";
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Skeleton,
  cn,
} from "@manto/ui";
import {
  AvisosNegados,
  type EstadoDosAvisos,
  ativarAvisos,
  confirmarAparelho,
  desativarAvisos,
  estadoDosAvisos,
  useChaveDosAvisos,
} from "../../lib/avisos";

/**
 * "Avisos no celular" (feature 332, FR-001/FR-002): ativar ou desativar os avisos das Conversas
 * neste aparelho. Cada aparelho é ativado à parte; quem tocar no aviso cai na conversa.
 */

const TEXTO_DO_ESTADO: Record<EstadoDosAvisos, string> = {
  desligado: "Os avisos no celular ainda não foram configurados.",
  sem_suporte: "Este navegador não recebe avisos.",
  iphone_fora_da_tela_de_inicio:
    "No iPhone, adicione a Plataforma à Tela de Início (Compartilhar → Adicionar à Tela de Início) e abra por lá para ativar.",
  negado: "O navegador bloqueou os avisos. Libere nas configurações do navegador e tente de novo.",
  inativo: "Os avisos estão desativados neste aparelho.",
  ativo: "Os avisos estão ativados neste aparelho.",
};

export function AvisosNoCelular() {
  const [aberto, setAberto] = useState(false);
  const chave = useChaveDosAvisos(true);
  const [estado, setEstado] = useState<EstadoDosAvisos | null>(null);
  const [ocupado, setOcupado] = useState<"ativar" | "desativar" | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const chavePublica = chave.data?.chave_publica ?? null;
  useEffect(() => {
    if (!chave.data) return;
    let vivo = true;
    void estadoDosAvisos(chavePublica).then((novo) => {
      if (!vivo) return;
      setEstado(novo);
      // Quem está logado agora fica com o aparelho já ativado (o navegador pode ser de outra pessoa).
      if (novo === "ativo") void confirmarAparelho().catch(() => undefined);
    });
    return () => {
      vivo = false;
    };
  }, [chave.data, chavePublica]);

  useEffect(() => {
    if (!aberto) setErro(null);
  }, [aberto]);

  const ativar = async () => {
    if (!chavePublica) return;
    setErro(null);
    setOcupado("ativar");
    try {
      await ativarAvisos(chavePublica);
      setEstado("ativo");
    } catch (falha) {
      if (falha instanceof AvisosNegados) setEstado(await estadoDosAvisos(chavePublica));
      else setErro("Não foi possível ativar os avisos. Tente novamente.");
    } finally {
      setOcupado(null);
    }
  };

  const desativar = async () => {
    setErro(null);
    setOcupado("desativar");
    try {
      await desativarAvisos();
      setEstado("inativo");
    } catch {
      setErro("Não foi possível desativar os avisos. Tente novamente.");
      setEstado(await estadoDosAvisos(chavePublica));
    } finally {
      setOcupado(null);
    }
  };

  const ativo = estado === "ativo";
  const Icone = ativo ? BellRing : Bell;
  return (
    <>
      <Button
        type="button"
        variant="outline"
        className={cn("h-11 w-11 shrink-0 px-0", ativo && "text-accent")}
        aria-label="Avisos no celular"
        title="Avisos no celular"
        onClick={() => setAberto(true)}
      >
        <Icone className="h-4 w-4" aria-hidden />
      </Button>
      <Dialog open={aberto} onOpenChange={setAberto}>
        <DialogContent open={aberto} className="max-w-md">
          <DialogHeader>
            <DialogTitle>Avisos no celular</DialogTitle>
            <DialogDescription>
              O aparelho avisa quando uma cliente escreve, quando alguém espera resposta há 15 minutos e quando uma
              conversa é transferida para você. Cada aparelho é ativado à parte.
            </DialogDescription>
          </DialogHeader>
          {chave.isError ? (
            <div className="space-y-2">
              <p role="alert" className="text-sm text-red">
                Não foi possível carregar os avisos. Tente novamente.
              </p>
              <Button type="button" variant="outline" loading={chave.isFetching} onClick={() => void chave.refetch()}>
                Tentar novamente
              </Button>
            </div>
          ) : estado === null ? (
            <Skeleton className="h-5 w-full" />
          ) : (
            <p className="text-sm" aria-live="polite">
              {TEXTO_DO_ESTADO[estado]}
            </p>
          )}
          {erro ? (
            <p role="alert" className="text-sm text-red">
              {erro}
            </p>
          ) : null}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setAberto(false)} disabled={ocupado !== null}>
              Fechar
            </Button>
            {estado === "inativo" ? (
              <Button type="button" onClick={() => void ativar()} loading={ocupado === "ativar"}>
                {ocupado === "ativar" ? "Ativando…" : "Ativar avisos"}
              </Button>
            ) : null}
            {estado === "ativo" ? (
              <Button
                type="button"
                variant="outline"
                onClick={() => void desativar()}
                loading={ocupado === "desativar"}
              >
                {ocupado === "desativar" ? "Desativando…" : "Desativar avisos"}
              </Button>
            ) : null}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
