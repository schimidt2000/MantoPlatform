import { useFormSchema } from "../lib/formularios";
import { DynamicForm } from "../components/formularios/DynamicForm";
import type { FormType, VersaoDaNota } from "../lib/formularios";

interface FormularioPageProps {
  formType: FormType;
  /** Hotfix 342b: a versão do link fixa a nota; sem ela (link antigo) a cliente marca a caixa. */
  versao?: VersaoDaNota;
}

/**
 * Usada por `/f/pre-contrato` (formType="comum") e `/f/corporativo` (formType="corporativo"),
 * cada um também em `/com-nota` e `/sem-nota`.
 */
export function FormularioPage({ formType, versao }: FormularioPageProps) {
  const schema = useFormSchema(formType);

  return (
    <div className="mx-auto max-w-2xl px-4 py-6">
      <header className="mb-4">
        <h1 className="font-display text-2xl text-ink">
          {schema.data?.header ?? "Formulário"}
        </h1>
        <p className="text-sm text-muted">Manto Produções</p>
      </header>
      {/* `key`: trocar de versão na mesma aba recomeça o formulário com a resposta da nota certa. */}
      <DynamicForm key={versao ?? "livre"} formType={formType} versao={versao} />
    </div>
  );
}
