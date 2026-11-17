import { useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, ConfirmDialog } from "@manto/ui";
import {
  dataCurta,
  useRemoverCrianca,
  type Consentimentos,
  type CriancaDaFicha,
  type LinhaDoConsentimento,
} from "../../lib/baseAutorizada";
import { AceiteDeNovidadesDialog } from "./AceiteDeNovidadesDialog";
import { CriancaDialog } from "./CriancaDialog";

/** "17/11/2026 14:30" pelo texto: o carimbo é horário de parede de SP, sem fuso. */
function dataHora(iso: string | null): string {
  if (!iso) return "";
  const hora = iso.slice(11, 16);
  return hora ? `${dataCurta(iso)} ${hora}` : dataCurta(iso);
}

const ROTULO_DA_LINHA: Record<string, string> = {
  "novidades:aceite": "Aceitou novidades",
  "novidades:retirada": "Saiu das novidades",
  "aniversario:aceite": "Autorizou guardar aniversário",
  "aniversario:retirada": "Aniversário removido",
};

function Historico({ linhas }: { linhas: LinhaDoConsentimento[] }) {
  const [aberto, setAberto] = useState(false);
  const reduzir = useReducedMotion();
  if (linhas.length === 0) return null;
  return (
    <div className="border-t border-line pt-3">
      <button
        type="button"
        className="min-h-11 text-sm text-accent underline-offset-2 hover:underline"
        onClick={() => setAberto((v) => !v)}
        aria-expanded={aberto}
      >
        {aberto ? "Esconder histórico" : `Ver histórico (${linhas.length})`}
      </button>
      <AnimatePresence initial={false}>
        {aberto && (
          <motion.ol
            key="historico"
            initial={reduzir ? false : { opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={reduzir ? { opacity: 0 } : { opacity: 0, height: 0 }}
            transition={{ duration: reduzir ? 0 : 0.2 }}
            className="mt-2 space-y-2 overflow-hidden text-sm"
          >
            {linhas.map((linha, indice) => (
              <li key={`${linha.em}-${indice}`} className="rounded-md bg-surface-2 px-3 py-2">
                <p className="text-ink">
                  {ROTULO_DA_LINHA[`${linha.tipo}:${linha.acao}`] ?? linha.acao}
                  <span className="text-muted"> · {dataHora(linha.em)}</span>
                </p>
                <p className="text-xs text-muted">
                  {[linha.origem, linha.autor, linha.referencia].filter(Boolean).join(" · ")}
                </p>
                <p className="mt-1 text-xs text-muted">
                  “{linha.texto}” (versão {linha.versao})
                </p>
              </li>
            ))}
          </motion.ol>
        )}
      </AnimatePresence>
    </div>
  );
}

function Criancas({
  clientId,
  criancas,
  podeEditar,
  onRemovida,
}: {
  clientId: number;
  criancas: CriancaDaFicha[];
  podeEditar: boolean;
  onRemovida: (mensagem: string) => void;
}) {
  const [remover, setRemover] = useState<CriancaDaFicha | null>(null);
  const remocao = useRemoverCrianca(clientId);
  if (criancas.length === 0) {
    return <p className="text-sm text-muted">Nenhum aniversário registrado.</p>;
  }
  return (
    <>
      <ul className="divide-y divide-line">
        {criancas.map((crianca) => (
          <li key={crianca.id} className="flex min-h-11 items-center justify-between gap-2 py-1">
            <span className="min-w-0 text-sm text-ink">
              {crianca.primeiro_nome}
              <span className="text-muted"> · {dataCurta(crianca.nascimento)}</span>
            </span>
            {podeEditar && (
              <Button variant="ghost" size="sm" onClick={() => setRemover(crianca)}>
                Remover
              </Button>
            )}
          </li>
        ))}
      </ul>
      <ConfirmDialog
        open={remover !== null}
        title="Remover este aniversário?"
        description={
          remover
            ? `O nome e a data de ${remover.primeiro_nome} serão apagados. O histórico guarda só que a autorização foi retirada.`
            : ""
        }
        confirmLabel="Remover"
        destructive
        pending={remocao.isPending}
        error={remocao.error ? "Não foi possível remover. Tente novamente." : null}
        onConfirm={() =>
          remover &&
          remocao.mutate(remover.id, {
            onSuccess: () => {
              setRemover(null);
              onRemovida("Aniversário removido da ficha.");
            },
          })
        }
        onOpenChange={(aberto) => !aberto && setRemover(null)}
      />
    </>
  );
}

export interface ConsentimentosCardProps {
  clientId: number;
  nome: string;
  consentimentos: Consentimentos;
  podeEditar: boolean;
}

/**
 * Os dois consentimentos da ficha (feature 350): novidades e aniversário da criança, cada um com a
 * prova (data, origem, texto e versão no histórico). Sem aceite, nada de prospecção.
 */
export function ConsentimentosCard({ clientId, nome, consentimentos, podeEditar }: ConsentimentosCardProps) {
  const [novidadesAberto, setNovidadesAberto] = useState(false);
  const [criancaAberta, setCriancaAberta] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const { novidades, criancas, historico, textos, origens } = consentimentos;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Consentimentos</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <section className="space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-medium text-ink">Novidades por WhatsApp e e-mail</h3>
            {novidades.ativo ? <Badge tone="green">Autorizou</Badge> : <Badge>Sem aceite</Badge>}
          </div>
          <p className="text-sm text-muted">
            {novidades.ativo
              ? `Desde ${dataCurta(novidades.aceite_em)} · ${novidades.origem ?? ""}`
              : novidades.retirada_em
                ? `Saiu em ${dataCurta(novidades.retirada_em)} · ${novidades.retirada_origem ?? ""}. Não prospectar.`
                : "Nenhum aceite registrado. Não prospectar."}
          </p>
          {podeEditar && (
            <Button variant="outline" size="sm" onClick={() => setNovidadesAberto(true)}>
              {novidades.ativo ? "Retirar aceite" : "Registrar aceite"}
            </Button>
          )}
        </section>

        {criancas !== undefined && (
          <section className="space-y-2 border-t border-line pt-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-medium text-ink">Aniversários autorizados</h3>
              {podeEditar && (
                <Button variant="outline" size="sm" onClick={() => setCriancaAberta(true)}>
                  Inserir aniversário
                </Button>
              )}
            </div>
            <Criancas
              clientId={clientId}
              criancas={criancas}
              podeEditar={podeEditar}
              onRemovida={setAviso}
            />
          </section>
        )}

        {aviso && (
          <p className="text-sm text-green" role="status">
            {aviso}
          </p>
        )}

        <Historico linhas={historico} />
      </CardContent>

      <AceiteDeNovidadesDialog
        clientId={clientId}
        nome={nome}
        ativo={novidades.ativo}
        texto={textos.novidades}
        origens={origens}
        open={novidadesAberto}
        onOpenChange={setNovidadesAberto}
        onConcluido={setAviso}
      />
      <CriancaDialog
        clientId={clientId}
        texto={textos.aniversario}
        origens={origens}
        open={criancaAberta}
        onOpenChange={setCriancaAberta}
        onConcluido={setAviso}
      />
    </Card>
  );
}
