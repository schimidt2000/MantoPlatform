import type { Ref } from "react";
import {
  OBSERVACOES_MAX,
  formatarDoc,
  type DadosDaNota,
  type ErrosDaNota,
  type NotaDoFormulario,
} from "../../lib/notaFiscal";
import { FIELD, FIELD_ERROR, FieldError, HELP, LABEL } from "./shared";

export interface DadosDaNotaCamposProps {
  valor: DadosDaNota;
  onChange: (patch: Partial<DadosDaNota>) => void;
  erros?: ErrosDaNota;
  /** O documento do cadastro do cliente, mostrado como o que vale com o campo em branco. */
  docDoCliente?: string | null;
  /** Feature 342: o que a cliente respondeu no formulário, para conferir ao lado dos campos. */
  doFormulario?: NotaDoFormulario | null;
  /** Para o foco chegar ao campo do erro (Princípio V). */
  refDoc?: Ref<HTMLInputElement>;
  refMunicipio?: Ref<HTMLInputElement>;
  /** Prefixo dos ids — a tela do evento e o card Comercial podem coexistir. */
  idPrefixo?: string;
}

/** As respostas da cliente, em uma linha por dado; some quando não há formulário com pedido. */
function RespostasDoFormulario({ respostas }: { respostas: NotaDoFormulario }) {
  const linhas: [string, string][] = [];
  if (respostas.doc) linhas.push(["CNPJ ou CPF", formatarDoc(respostas.doc)]);
  if (respostas.email) linhas.push(["E-mail", respostas.email]);
  if (respostas.iss) linhas.push(["Retém ISS", respostas.iss]);
  if (respostas.referencia) linhas.push(["Para constar na nota", respostas.referencia]);
  if (linhas.length === 0) return null;
  return (
    <div className="rounded-md border border-line bg-panel p-3 text-sm">
      <p className="font-medium text-ink">A cliente informou no formulário</p>
      <dl className="mt-1 space-y-0.5">
        {linhas.map(([rotulo, valor]) => (
          <div key={rotulo} className="flex flex-wrap gap-x-2">
            <dt className="text-muted">{rotulo}:</dt>
            <dd className="break-all text-ink">{valor}</dd>
          </div>
        ))}
      </dl>
      <p className={HELP}>Confira com os campos abaixo antes de salvar.</p>
    </div>
  );
}

/**
 * Os dados da nota (feature 323), abertos quando a venda "precisa de nota fiscal". Componente
 * controlado: serve ao formulário do evento (react-hook-form) e ao card Comercial (`useState`).
 */
export function DadosDaNotaCampos({
  valor,
  onChange,
  erros,
  docDoCliente,
  doFormulario,
  refDoc,
  refMunicipio,
  idPrefixo = "nota",
}: DadosDaNotaCamposProps) {
  const id = (campo: string) => `${idPrefixo}_${campo}`;
  const docCadastro = docDoCliente ? formatarDoc(docDoCliente) : null;

  return (
    <fieldset className="space-y-3 rounded-lg border border-line bg-surface-2/40 p-3">
      <legend className="px-1 text-sm font-medium text-ink">Dados da nota</legend>

      {doFormulario && <RespostasDoFormulario respostas={doFormulario} />}

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className={LABEL} htmlFor={id("tomador_doc")}>
            CNPJ ou CPF do tomador{docCadastro ? "" : " *"}
          </label>
          <input
            id={id("tomador_doc")}
            ref={refDoc}
            inputMode="numeric"
            className={erros?.nota_tomador_doc ? FIELD_ERROR : FIELD}
            value={valor.tomador_doc}
            placeholder={docCadastro ?? "00.000.000/0000-00"}
            onChange={(e) => onChange({ tomador_doc: e.target.value })}
            onBlur={(e) => onChange({ tomador_doc: formatarDoc(e.target.value) })}
          />
          <FieldError message={erros?.nota_tomador_doc} />
          {!erros?.nota_tomador_doc && (
            <p className={HELP}>
              {docCadastro
                ? `Em branco, vale o do cadastro do cliente: ${docCadastro}.`
                : "O cadastro do cliente não tem CNPJ nem CPF: informe o de quem recebe a nota."}
            </p>
          )}
        </div>
        <div>
          <label className={LABEL} htmlFor={id("email")}>
            E-mail para envio da nota
          </label>
          <input
            id={id("email")}
            type="email"
            className={erros?.nota_email ? FIELD_ERROR : FIELD}
            value={valor.email}
            placeholder="financeiro@empresa.com.br"
            maxLength={200}
            onChange={(e) => onChange({ email: e.target.value })}
          />
          <FieldError message={erros?.nota_email} />
          {!erros?.nota_email && <p className={HELP}>Em branco, vale o e-mail do cadastro.</p>}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className={LABEL} htmlFor={id("municipio")}>
            Município do evento{valor.iss_retido ? " *" : ""}
          </label>
          <input
            id={id("municipio")}
            ref={refMunicipio}
            className={erros?.nota_municipio ? FIELD_ERROR : FIELD}
            value={valor.municipio}
            placeholder="Ex.: Jundiaí - SP"
            maxLength={120}
            onChange={(e) => onChange({ municipio: e.target.value })}
          />
          <FieldError message={erros?.nota_municipio} />
          {!erros?.nota_municipio && (
            <p className={HELP}>O ISS é devido na cidade do evento. Confira antes de salvar.</p>
          )}
        </div>
        <div>
          <label className={LABEL} htmlFor={id("referencia")}>
            Referência do cliente
          </label>
          <input
            id={id("referencia")}
            className={FIELD}
            value={valor.referencia}
            placeholder="Ex.: AF 618/2026"
            maxLength={120}
            onChange={(e) => onChange({ referencia: e.target.value })}
          />
          <p className={HELP}>Pedido de compra ou AF, se o cliente informou.</p>
        </div>
      </div>

      <label className="flex min-h-11 items-center gap-2 text-sm text-ink">
        <input
          type="checkbox"
          className="h-5 w-5"
          checked={valor.iss_retido}
          onChange={(e) => onChange({ iss_retido: e.target.checked })}
        />
        ISS retido pelo tomador
      </label>

      <div>
        <label className={LABEL} htmlFor={id("observacoes")}>
          Observações para a nota
        </label>
        <textarea
          id={id("observacoes")}
          rows={3}
          maxLength={OBSERVACOES_MAX}
          className={`w-full rounded-md border bg-panel px-2 py-2 text-sm text-ink ${
            erros?.nota_observacoes ? "border-2 border-red" : "border-line"
          }`}
          value={valor.observacoes}
          placeholder="O que o cliente pediu para constar na nota"
          onChange={(e) => onChange({ observacoes: e.target.value })}
        />
        <FieldError message={erros?.nota_observacoes} />
      </div>
    </fieldset>
  );
}
