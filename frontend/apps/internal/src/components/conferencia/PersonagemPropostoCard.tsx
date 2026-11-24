import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Badge, Button, ConfirmDialog, cn } from "@manto/ui";
import { FigurinoPicker } from "../FigurinoPicker";
import { RecortePersonagem } from "./RecortePersonagem";
import {
  erroDoCampo,
  mensagemDoErro,
  useAlterarPersonagem,
  useExcluirPersonagem,
  type CamposDoPersonagem,
  type PersonagemProposto,
} from "../../lib/catalogoConferencia";

const CAMPO =
  "w-full rounded-md border border-line bg-panel px-3 text-sm text-ink disabled:cursor-not-allowed disabled:opacity-60";
const BOTAO_DE_DECISAO =
  "h-11 rounded-md border text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60";

interface PersonagemPropostoCardProps {
  itemId: number;
  personagem: PersonagemProposto;
  /** Item conferido: tudo fica só para consulta até reabrir. */
  travado: boolean;
  /** Abre a foto original no visualizador do sistema. */
  onAbrirFoto: (url: string, nome: string) => void;
}

/**
 * Um personagem proposto pela leitura, com o que quem confere pode corrigir.
 *
 * Cada controle salva na hora (FR-008). O nome e a observação salvam ao sair do campo; se a API
 * recusar, o texto digitado fica no campo com o erro embaixo. O que a leitura propôs (nome e ficha)
 * continua visível depois da correção, para dar para voltar atrás sem lembrar de cabeça.
 */
export function PersonagemPropostoCard({ itemId, personagem, travado, onAbrirFoto }: PersonagemPropostoCardProps) {
  const reduzirMovimento = useReducedMotion();
  const alterar = useAlterarPersonagem(itemId, personagem.id);
  const excluir = useExcluirPersonagem(itemId, personagem.id);
  const [nome, setNome] = useState(personagem.nome);
  const [observacao, setObservacao] = useState(personagem.observacao ?? "");
  const [observacaoAberta, setObservacaoAberta] = useState(Boolean(personagem.observacao));
  const [confirmandoExclusao, setConfirmandoExclusao] = useState(false);

  // O servidor é a verdade depois de salvar (ele apara espaços) e quando outra pessoa altera.
  useEffect(() => setNome(personagem.nome), [personagem.nome]);
  useEffect(() => setObservacao(personagem.observacao ?? ""), [personagem.observacao]);

  const bloqueado = travado || alterar.isPending;
  const naoCriar = personagem.decisao === "nao_criar";
  const semFotoPossivel = personagem.foto === null;
  const erroDoNome = erroDoCampo(alterar.error, "nome");
  const erroDaObservacao = erroDoCampo(alterar.error, "observacao");
  const erroGeral = erroDoNome || erroDaObservacao ? null : mensagemDoErro(alterar.error);
  const sugerida = personagem.ficha_sugerida;
  const fichaDiferenteDaSugerida = sugerida !== null && personagem.ficha?.id !== sugerida.id;

  function salvar(campos: CamposDoPersonagem) {
    if (!travado) alterar.mutate(campos);
  }

  function salvarNome() {
    if (nome.trim() !== personagem.nome) salvar({ nome });
  }

  function salvarObservacao() {
    if (observacao.trim() !== (personagem.observacao ?? "")) salvar({ observacao });
  }

  return (
    // Entra e sai com transição curta (Princípio XI): acrescentar ou excluir um personagem não pode
    // ser um "tranco" numa lista de cartões altos.
    <motion.li
      initial={reduzirMovimento ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={reduzirMovimento ? undefined : { opacity: 0 }}
      transition={{ duration: reduzirMovimento ? 0 : 0.2, ease: "easeOut" }}
      className="flex gap-3 rounded-lg border border-line bg-panel p-3"
    >
      <RecortePersonagem
        foto={personagem.foto}
        nome={personagem.nome}
        apagado={naoCriar || personagem.sem_foto}
        onAbrir={personagem.foto ? () => onAbrirFoto(personagem.foto!.url, personagem.nome) : undefined}
      />

      <div className="min-w-0 flex-1 space-y-2">
        <div>
          <input
            className={cn(CAMPO, "h-11 font-medium", erroDoNome && "border-red")}
            value={nome}
            disabled={travado}
            maxLength={200}
            aria-label={`Nome de ${personagem.nome}`}
            aria-invalid={Boolean(erroDoNome)}
            onChange={(e) => setNome(e.target.value)}
            onBlur={salvarNome}
            onKeyDown={(e) => {
              if (e.key === "Enter") e.currentTarget.blur();
            }}
          />
          {erroDoNome && <p className="mt-1 text-xs text-red">{erroDoNome}</p>}
          {personagem.nome_lido && personagem.nome_lido !== personagem.nome && (
            <p className="mt-1 text-xs text-muted">A leitura propôs: {personagem.nome_lido}</p>
          )}
          {personagem.origem === "manual" && (
            <Badge tone="blue" className="mt-1">
              Acrescentado na conferência
            </Badge>
          )}
        </div>

        {personagem.aviso && (
          <p className="rounded-md bg-gold-soft px-2 py-1.5 text-xs text-gold-ink">{personagem.aviso}</p>
        )}

        <div>
          <FigurinoPicker
            value={personagem.ficha?.id ?? null}
            onChange={(fichaId) => salvar({ ficha_id: fichaId })}
            characterName={personagem.nome}
            disabled={bloqueado}
            ariaLabel={`Ficha de figurino de ${personagem.nome}`}
            placeholder="Buscar ficha de figurino"
          />
          {fichaDiferenteDaSugerida && (
            <div className="mt-1 flex flex-wrap items-center gap-x-2 text-xs text-muted">
              <span>
                Ficha sugerida: {sugerida.id} {sugerida.nome}
              </span>
              <button
                type="button"
                className="min-h-11 font-medium text-accent underline disabled:opacity-60"
                disabled={bloqueado}
                onClick={() => salvar({ ficha_id: sugerida.id })}
              >
                Usar a sugerida
              </button>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-2" role="group" aria-label={`Decisão sobre ${personagem.nome}`}>
          <button
            type="button"
            disabled={bloqueado}
            aria-pressed={!naoCriar}
            aria-label={`Criar ${personagem.nome}`}
            onClick={() => naoCriar && salvar({ decisao: "criar" })}
            className={cn(
              BOTAO_DE_DECISAO,
              naoCriar ? "border-line bg-panel text-muted" : "border-green bg-green-soft text-green",
            )}
          >
            Criar
          </button>
          <button
            type="button"
            disabled={bloqueado}
            aria-pressed={naoCriar}
            aria-label={`Não criar ${personagem.nome}`}
            onClick={() => !naoCriar && salvar({ decisao: "nao_criar" })}
            className={cn(
              BOTAO_DE_DECISAO,
              naoCriar ? "border-red bg-red-soft text-red" : "border-line bg-panel text-muted",
            )}
          >
            Não criar
          </button>
        </div>

        <label className="flex min-h-11 items-center gap-2 text-sm text-ink">
          <input
            type="checkbox"
            className="h-5 w-5 accent-accent"
            checked={personagem.sem_foto}
            disabled={bloqueado || semFotoPossivel}
            aria-label={`Criar ${personagem.nome} sem foto`}
            onChange={(e) => salvar({ sem_foto: e.target.checked })}
          />
          <span>
            Criar sem foto
            {semFotoPossivel && <span className="block text-xs text-muted">A leitura não tem foto deste personagem.</span>}
          </span>
        </label>

        {observacaoAberta ? (
          <div>
            <textarea
              className={cn(CAMPO, "h-20 resize-y py-2", erroDaObservacao && "border-red")}
              value={observacao}
              disabled={travado}
              maxLength={1000}
              placeholder="Observação sobre este personagem"
              aria-label={`Observação sobre ${personagem.nome}`}
              onChange={(e) => setObservacao(e.target.value)}
              onBlur={salvarObservacao}
            />
            {erroDaObservacao && <p className="mt-1 text-xs text-red">{erroDaObservacao}</p>}
          </div>
        ) : (
          !travado && (
            <Button variant="ghost" className="px-3" onClick={() => setObservacaoAberta(true)}>
              Observação
            </Button>
          )
        )}

        <div className="flex min-h-6 flex-wrap items-center justify-between gap-2 text-xs" aria-live="polite">
          <span className={cn(erroGeral ? "text-red" : "text-muted")}>
            {alterar.isPending ? "Salvando…" : erroGeral ? erroGeral : alterar.isSuccess ? "Salvo." : ""}
          </span>
          {erroGeral && alterar.variables && !travado && (
            <button
              type="button"
              className="min-h-11 font-medium text-accent underline"
              onClick={() => alterar.mutate(alterar.variables)}
            >
              Tentar novamente
            </button>
          )}
          {personagem.origem === "manual" && !travado && (
            <Button variant="ghost" className="px-3" onClick={() => setConfirmandoExclusao(true)}>
              Excluir
            </Button>
          )}
        </div>
      </div>

      <ConfirmDialog
        open={confirmandoExclusao}
        title="Excluir este personagem?"
        description={`"${personagem.nome}" foi acrescentado na conferência e sai do elenco proposto.`}
        confirmLabel="Excluir"
        destructive
        pending={excluir.isPending}
        error={mensagemDoErro(excluir.error)}
        onConfirm={() => excluir.mutate(undefined, { onSuccess: () => setConfirmandoExclusao(false) })}
        onOpenChange={setConfirmandoExclusao}
      />
    </motion.li>
  );
}
