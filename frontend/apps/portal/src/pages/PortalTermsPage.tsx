import { useRef, useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { Button } from "@manto/ui";
import { FormError } from "../components/FormField";
import { useAcceptTerms } from "../lib/portalAccount";
import { useCurrentTalent } from "../lib/portalAuth";
import {
  TERMS_CONSENT_LABEL,
  TERMS_PREAMBLE,
  TERMS_SECTIONS,
  TERMS_SUBTITLE,
  TERMS_TITLE,
} from "../lib/termsContent";

/** Distância do fim (px) a partir da qual consideramos que o talento leu até o final. */
const SCROLL_BOTTOM_SLACK = 24;

function TermsBody() {
  return (
    <>
      {TERMS_PREAMBLE && <p className="mb-3">{TERMS_PREAMBLE}</p>}
      {TERMS_SECTIONS.map((section, index) => (
        <section key={section.title || `bloco-${index}`} className="mb-4">
          {section.title && (
            <h2 className="mb-1 text-xs font-bold uppercase tracking-wide text-accent-dark">
              {section.title}
            </h2>
          )}
          {section.paragraphs?.map((text) => (
            <p key={text} className="mb-2">
              {text}
            </p>
          ))}
          {section.bullets && (
            <ul className="mb-2 list-disc space-y-1 pl-5">
              {section.bullets.map((text) => (
                <li key={text}>{text}</li>
              ))}
            </ul>
          )}
        </section>
      ))}
    </>
  );
}

/**
 * Aceite do Termo de Consentimento.
 *
 * Mantém a trava da versão Jinja: o checkbox só libera depois que o talento rola até o fim do
 * texto — o aceite precisa ser informado, não um clique reflexo. Em modo `viewOnly` (talento que
 * já aceitou) a tela vira leitura, sem trava nem botão.
 */
export function PortalTermsPage({ viewOnly = false }: { viewOnly?: boolean }) {
  const { data: talent } = useCurrentTalent();
  const acceptTerms = useAcceptTerms();
  const boxRef = useRef<HTMLDivElement>(null);
  const [readToEnd, setReadToEnd] = useState(viewOnly);
  const [checked, setChecked] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const alreadyAccepted = viewOnly || Boolean(talent?.terms_accepted);

  function handleScroll() {
    const box = boxRef.current;
    if (!box) return;
    if (box.scrollTop + box.clientHeight >= box.scrollHeight - SCROLL_BOTTOM_SLACK) {
      setReadToEnd(true);
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-2xl flex-col gap-4 p-4">
      <header className="text-center">
        <h1 className="text-base font-bold text-ink">{TERMS_TITLE}</h1>
        <p className="text-sm text-muted">{TERMS_SUBTITLE}</p>
      </header>

      <div
        ref={boxRef}
        onScroll={handleScroll}
        tabIndex={0}
        role="region"
        aria-label="Texto do termo de consentimento"
        className="max-h-[55vh] overflow-y-auto rounded-lg border border-line bg-panel p-4 text-sm leading-relaxed text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <TermsBody />
      </div>

      {alreadyAccepted ? (
        <div className="flex items-center justify-center gap-2 rounded-md bg-green-soft px-3 py-3 text-sm text-green">
          <CheckCircle2 className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span>Você já aceitou este termo.</span>
        </div>
      ) : (
        <div className="space-y-3">
          {!readToEnd && (
            <p className="text-center text-xs text-muted">Role o texto até o fim para aceitar.</p>
          )}

          <label className="flex min-h-[44px] cursor-pointer items-start gap-3 text-sm font-medium text-ink">
            <input
              type="checkbox"
              className="mt-1 h-5 w-5 shrink-0 accent-accent disabled:opacity-40"
              disabled={!readToEnd}
              checked={checked}
              onChange={(event) => setChecked(event.target.checked)}
            />
            <span>{TERMS_CONSENT_LABEL}</span>
          </label>

          <FormError>{formError}</FormError>

          <Button
            className="w-full"
            disabled={!checked}
            loading={acceptTerms.isPending}
            onClick={() => {
              setFormError(null);
              // O hook atualiza o cache do talento; o `OnboardingGate` libera o app sozinho.
              acceptTerms.mutate(undefined, { onError: (error) => setFormError(error.message) });
            }}
          >
            Aceitar e entrar no portal
          </Button>
        </div>
      )}
    </div>
  );
}
