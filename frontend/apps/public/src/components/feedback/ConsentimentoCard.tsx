import { useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { ApiRequestError } from "@manto/api-client";
import { Button, Input } from "@manto/ui";
import { useSalvarConsentimento, type ConsentimentoPublico } from "../../lib/feedback";

interface Props {
  token: string;
  consentimento: ConsentimentoPublico;
}

/**
 * Feature 350 (LGPD): as duas autorizações, separadas e desmarcadas — receber novidades, e guardar o
 * primeiro nome e o aniversário da criança. Nenhuma é condição de nada. O texto mostrado é o que o
 * servidor grava (a tela manda a versão). Quem já recebe novidades vê o "Não quero mais receber".
 */
export function ConsentimentoCard({ token, consentimento }: Props) {
  const reduzir = useReducedMotion();
  const salvar = useSalvarConsentimento(token);
  const [novidades, setNovidades] = useState(false);
  const [nome, setNome] = useState("");
  const [nascimento, setNascimento] = useState("");
  const [aceiteDaCrianca, setAceiteDaCrianca] = useState(false);
  const [salvo, setSalvo] = useState<string | null>(null);
  const { textos } = consentimento;

  const campos = salvar.error instanceof ApiRequestError ? (salvar.error.fields ?? {}) : {};
  const erroGeral =
    salvar.error && Object.keys(campos).length === 0 ? salvar.error.message : null;
  const temCrianca = Boolean(nome.trim() || nascimento || aceiteDaCrianca);

  function enviar(retirar = false) {
    setSalvo(null);
    salvar.mutate(
      {
        novidades: retirar ? "retirar" : novidades ? "aceitar" : null,
        versao_novidades: textos.novidades.versao,
        crianca:
          !retirar && temCrianca
            ? { primeiro_nome: nome, nascimento, aceite: aceiteDaCrianca }
            : null,
        versao_aniversario: textos.aniversario.versao,
      },
      {
        onSuccess: () => {
          setNovidades(false);
          setNome("");
          setNascimento("");
          setAceiteDaCrianca(false);
          setSalvo(
            retirar
              ? "Combinado: você não vai mais receber nossas novidades."
              : "Suas escolhas foram salvas. Obrigado!",
          );
        },
      },
    );
  }

  return (
    <motion.section
      initial={reduzir ? undefined : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: 0.25 }}
      className="mt-2 w-full space-y-3 rounded-lg border border-line p-3 text-left"
      aria-labelledby="titulo-autorizacoes"
    >
      <h2 id="titulo-autorizacoes" className="font-display text-base text-ink">
        Quer ficar por perto?
      </h2>

      {consentimento.recebe_novidades ? (
        <div className="space-y-2 text-sm text-ink">
          <p>Você já recebe nossas novidades. 💜</p>
          <Button
            variant="ghost"
            className="min-h-11 px-0 text-muted underline"
            loading={salvar.isPending && salvar.variables?.novidades === "retirar"}
            onClick={() => enviar(true)}
          >
            Não quero mais receber
          </Button>
        </div>
      ) : (
        <label className="flex min-h-11 cursor-pointer items-start gap-3 text-sm leading-snug text-ink">
          <input
            type="checkbox"
            checked={novidades}
            onChange={(e) => setNovidades(e.target.checked)}
            className="mt-0.5 h-5 w-5 shrink-0 accent-accent"
          />
          <span>{textos.novidades.texto}</span>
        </label>
      )}

      <div className="space-y-2 border-t border-line pt-3">
        <p className="text-sm text-ink">
          Quer um lembrete antes do próximo aniversário da sua criança? Conte para a gente:
        </p>
        <label className="block">
          <span className="mb-1 block text-xs text-muted">Primeiro nome da criança</span>
          <Input
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            maxLength={60}
            autoComplete="off"
            aria-invalid={Boolean(campos["crianca.primeiro_nome"])}
          />
          {campos["crianca.primeiro_nome"] && (
            <span className="mt-1 block text-xs text-red" role="alert">
              {campos["crianca.primeiro_nome"]}
            </span>
          )}
        </label>
        <label className="block">
          <span className="mb-1 block text-xs text-muted">Data de aniversário</span>
          <Input
            type="date"
            value={nascimento}
            onChange={(e) => setNascimento(e.target.value)}
            aria-invalid={Boolean(campos["crianca.nascimento"])}
          />
          {campos["crianca.nascimento"] && (
            <span className="mt-1 block text-xs text-red" role="alert">
              {campos["crianca.nascimento"]}
            </span>
          )}
        </label>
        <label
          className={`flex min-h-11 cursor-pointer items-start gap-3 rounded-md p-2 text-sm leading-snug text-ink ${
            campos["crianca.aceite"] ? "border border-red" : ""
          }`}
        >
          <input
            type="checkbox"
            checked={aceiteDaCrianca}
            onChange={(e) => setAceiteDaCrianca(e.target.checked)}
            className="mt-0.5 h-5 w-5 shrink-0 accent-accent"
          />
          <span>{textos.aniversario.texto}</span>
        </label>
        {campos["crianca.aceite"] && (
          <p className="text-xs text-red" role="alert">
            {campos["crianca.aceite"]}
          </p>
        )}
      </div>

      {erroGeral && (
        <p className="text-sm text-red" role="alert">
          {erroGeral}
        </p>
      )}
      {salvo && (
        <p className="text-sm text-green" role="status">
          {salvo}
        </p>
      )}

      <Button
        size="lg"
        className="w-full"
        disabled={!novidades && !temCrianca}
        loading={salvar.isPending && salvar.variables?.novidades !== "retirar"}
        onClick={() => enviar()}
      >
        Salvar minhas escolhas
      </Button>
    </motion.section>
  );
}
