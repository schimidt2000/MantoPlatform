import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useReducedMotion } from "framer-motion";
import { ApiRequestError, assetUrl } from "@manto/api-client";
import { Button, Card, CardContent, CardHeader, CardTitle, Skeleton } from "@manto/ui";
import { CheckCircle2 } from "lucide-react";
import { FormError, FormSuccess } from "../components/FormField";
import { StarRating } from "../components/StarRating";
import { formatDateTime } from "../lib/format";
import {
  baselineFrom,
  useRatingForm,
  useSubmitRating,
  useSubmitRatingDetail,
  type RatingForm,
  type RatingGeneralCategory,
  type RatingPersonCategory,
} from "../lib/portalRatings";

/** Nota mínima que dispensa comentário — espelha `COMMENT_REQUIRED_BELOW` no backend. */
const COMMENT_REQUIRED_BELOW = 4;

// Rótulos restaurados da tela Jinja (feature 232). `texto` chamava-se **"Show no geral"** e vinha
// com a explicação de que cobre coreografia, posicionamento, texto e interações — na migração virou
// "Texto / roteiro", que é mais estreito do que a coluna significa nos 42 registros históricos.
//
// Os mesmos nomes valem do outro lado, onde o casting LÊ: `RATING_CATEGORIES`
// (`app/talents/rating_ops.py`, fonte única do panorama) e `FeedbackSection.tsx` (ficha do evento).
// Mexer aqui sem mexer lá é o que fazia a pergunta e a resposta terem nomes diferentes.
const CATEGORY_LABELS: Record<RatingGeneralCategory, string> = {
  figurino: "👗 Figurino",
  som: "🎵 Som",
  texto: "🎭 Show no geral",
};

/** Explicação que existia embaixo do título da categoria na tela antiga. */
const CATEGORY_HINTS: Partial<Record<RatingGeneralCategory, string>> = {
  texto: "Falar sobre coreografia, posicionamento, texto e interações",
};

const PERSON_GROUP_LABELS: Record<RatingPersonCategory, string> = {
  artista: "🎭 Colegas artistas",
  coordenacao: "🧑‍💼 Coordenação",
  maquiagem: "💄 Maquiagem",
};

const PERSON_GROUP_ORDER: RatingPersonCategory[] = ["artista", "coordenacao", "maquiagem"];

/** Uma nota em edição na tela (geral, por categoria ou por pessoa). */
interface ScoreEntry {
  score: number | null;
  comment: string;
}

const EMPTY_ENTRY: ScoreEntry = { score: null, comment: "" };

/** Chave estável de uma sub-nota de pessoa dentro do estado local. */
const personKey = (category: string, talentId: number) => `${category}:${talentId}`;

function ScoreBlock({
  label,
  sublabel,
  photoUrl,
  name,
  entry,
  onChange,
  disabled,
}: {
  label: string;
  sublabel?: string | null;
  photoUrl?: string | null;
  name: string;
  entry: ScoreEntry;
  onChange: (next: ScoreEntry) => void;
  disabled: boolean;
}) {
  return (
    <div className="space-y-2 border-b border-line pb-3 last:border-0 last:pb-0">
      <div className="flex items-center gap-3">
        {photoUrl && (
          <img
            src={assetUrl(photoUrl)}
            alt=""
            className="h-10 w-10 shrink-0 rounded-full object-cover"
          />
        )}
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-ink">{label}</p>
          {sublabel && <p className="truncate text-xs text-muted">{sublabel}</p>}
        </div>
      </div>
      <StarRating
        name={name}
        label={`Nota para ${label}`}
        value={entry.score}
        disabled={disabled}
        onChange={(score) => onChange({ ...entry, score })}
      />
      {entry.score != null && (
        <textarea
          rows={2}
          disabled={disabled}
          value={entry.comment}
          onChange={(event) => onChange({ ...entry, comment: event.target.value })}
          placeholder="Comentário (opcional)"
          aria-label={`Comentário sobre ${label}`}
          className="w-full rounded-md border border-line bg-panel px-3 py-2 text-sm text-ink placeholder:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60"
        />
      )}
    </div>
  );
}

/** Deriva o estado inicial das sub-notas a partir do que já está gravado. */
function initialSubs(form: RatingForm | undefined): Record<string, ScoreEntry> {
  const state: Record<string, ScoreEntry> = {};
  for (const sub of form?.rating?.subs ?? []) {
    const key =
      sub.subject_talent_id != null ? personKey(sub.category, sub.subject_talent_id) : sub.category;
    state[key] = { score: sub.score, comment: sub.comment ?? "" };
  }
  return state;
}

/**
 * Avaliação de um evento pelo artista.
 *
 * Duas etapas na mesma tela — a versão Jinja usava duas páginas, e a migração para React manteve
 * as duas etapas mas **inverteu qual era o caminho padrão** (feature 232). Lá, o botão principal da
 * nota geral era "Enviar e avaliar em detalhes →" e levava para uma página dedicada às partes; "Só
 * enviar a nota geral" era o desvio. Aqui a etapa 2 tinha virado um cartão "(opcional)" anexado
 * abaixo, depois de um "Avaliação enviada. Obrigado!" que se lê como fim — quem não rolava a tela
 * nunca via as partes.
 *
 * Agora o padrão volta a ser detalhar: o botão principal salva a nota geral **e leva** para as
 * partes (rolagem até o bloco), e quem quiser parar na nota geral tem um botão próprio para isso.
 */
export function PortalRatePage() {
  const { eventId: eventIdParam } = useParams<{ eventId: string }>();
  const eventId = Number(eventIdParam);
  const navigate = useNavigate();

  const formQuery = useRatingForm(eventId);
  const submitRating = useSubmitRating();
  const submitDetail = useSubmitRatingDetail();

  const [general, setGeneral] = useState<ScoreEntry>(EMPTY_ENTRY);
  const [subs, setSubs] = useState<Record<string, ScoreEntry>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [savedStep, setSavedStep] = useState<"general" | "detail" | null>(null);
  /** Alvo da rolagem depois de salvar a nota geral — as partes viraram destino de novo. */
  const detalheRef = useRef<HTMLDivElement>(null);
  const reduzirMovimento = useReducedMotion();

  const form = formQuery.data;

  // Preenche o estado uma vez, quando o formulário chega — depois disso a tela é dona do estado
  // (as mutations devolvem o formulário atualizado, mas reaplicá-lo apagaria o que está sendo
  // digitado na etapa seguinte).
  useEffect(() => {
    if (!form) return;
    setGeneral({ score: form.rating?.score ?? null, comment: form.rating?.comment ?? "" });
    setSubs(initialSubs(form));
    // `form.event.id` e não `form`: o objeto muda a cada mutation, o evento não.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form?.event.id]);

  // Baseline de versionamento: capturado no primeiro carregamento e mantido fixo durante a
  // sessão de edição, para o backend comparar contra o estado pré-edição (feature 181).
  const baseline = useMemo(() => baselineFrom(formQuery.data), [formQuery.data?.event.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (formQuery.isLoading) {
    return (
      <div className="space-y-3 p-4">
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (formQuery.isError || !form) {
    const message =
      formQuery.error instanceof ApiRequestError
        ? formQuery.error.message
        : "Não foi possível abrir a avaliação deste evento.";
    return (
      <div className="space-y-3 p-4">
        <FormError>{message}</FormError>
        <Button variant="outline" className="w-full" onClick={() => navigate("/historico")}>
          Voltar ao histórico
        </Button>
      </div>
    );
  }

  const locked = !form.can_edit;
  const commentRequired =
    general.score != null && general.score < COMMENT_REQUIRED_BELOW && !general.comment.trim();

  // Arrow consts, não `function` — declarações são içadas e o TS perde o estreitamento de
  // `form` (garantido não-nulo pelo early-return acima) dentro delas.
  /**
   * Salva a nota geral. `depois` decide o que acontece em seguida — é o que restaura o desenho
   * antigo: "detalhar" era o caminho principal, "parar aqui" o desvio explícito.
   */
  const handleSubmitGeneral = (depois: "detalhar" | "sair") => {
    setFormError(null);
    setSavedStep(null);
    if (general.score == null) {
      setFormError("Selecione uma nota de 1 a 5 estrelas.");
      return;
    }
    submitRating.mutate(
      {
        eventId,
        score: general.score,
        comment: general.comment.trim() || null,
        baseline,
      },
      {
        onSuccess: () => {
          if (depois === "sair") {
            navigate("/historico");
            return;
          }
          setSavedStep("general");
          // O bloco das partes só existe no DOM depois deste sucesso; o rAF duplo espera o React
          // pintá-lo antes de rolar. Sem isso a rolagem acontece para um elemento que ainda não
          // está lá e a tela fica parada — exatamente o sintoma que a feature conserta.
          requestAnimationFrame(() =>
            requestAnimationFrame(() =>
              detalheRef.current?.scrollIntoView({
                behavior: reduzirMovimento ? "auto" : "smooth",
                block: "start",
              }),
            ),
          );
        },
        onError: (error) => setFormError(error.message),
      },
    );
  };

  const handleSubmitDetail = () => {
    setFormError(null);
    setSavedStep(null);

    const generalScores: Partial<
      Record<RatingGeneralCategory, { score: number; comment: string | null }>
    > = {};
    for (const category of form.general_categories) {
      const entry = subs[category];
      if (entry?.score != null) {
        generalScores[category] = { score: entry.score, comment: entry.comment.trim() || null };
      }
    }

    const people = form.people.flatMap((person) => {
      const entry = subs[personKey(person.category, person.talent_id)];
      if (entry?.score == null) return [];
      return [
        {
          category: person.category,
          subject_talent_id: person.talent_id,
          score: entry.score,
          comment: entry.comment.trim() || null,
        },
      ];
    });

    submitDetail.mutate(
      { eventId, general: generalScores, people, baseline },
      {
        onSuccess: () => setSavedStep("detail"),
        onError: (error) => setFormError(error.message),
      },
    );
  };

  const setSub = (key: string, next: ScoreEntry) =>
    setSubs((prev) => ({ ...prev, [key]: next }));

  const hasGeneralRating = form.rating != null;

  return (
    <div className="space-y-4 p-4">
      <header>
        <h1 className="text-lg font-semibold text-ink">Avaliar evento</h1>
        <p className="text-sm text-ink">{form.event.title}</p>
        <p className="text-xs text-muted">
          {formatDateTime(form.event.start_at)}
          {form.event.location ? ` · ${form.event.location}` : ""}
        </p>
      </header>

      {locked && (
        <div className="rounded-md bg-blue-soft px-3 py-2 text-sm text-blue" role="status">
          O prazo para alterar esta avaliação encerrou. Você pode consultá-la, mas não editar.
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Como foi sua experiência?</CardTitle>
          <p className="text-sm text-muted">
            Sua nota geral sobre a produção do evento. Notas abaixo de 4 pedem um comentário.
          </p>
        </CardHeader>
        <CardContent className="space-y-3">
          <StarRating
            name="general-score"
            label="Nota geral do evento"
            value={general.score}
            disabled={locked}
            onChange={(score) => setGeneral((prev) => ({ ...prev, score }))}
          />

          <textarea
            rows={3}
            disabled={locked}
            value={general.comment}
            onChange={(event) => setGeneral((prev) => ({ ...prev, comment: event.target.value }))}
            placeholder={
              commentRequired ? "Conte o que aconteceu (obrigatório)" : "Comentário (opcional)"
            }
            aria-label="Comentário sobre o evento"
            aria-invalid={commentRequired ? true : undefined}
            className="w-full rounded-md border border-line bg-panel px-3 py-2 text-sm text-ink placeholder:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring aria-[invalid=true]:border-red disabled:opacity-60"
          />
          {commentRequired && (
            <p className="text-sm text-red" role="alert">
              Para notas abaixo de 4 estrelas, deixe um comentário explicando o que aconteceu.
            </p>
          )}

          {savedStep === "general" && (
            <FormSuccess>Nota geral salva. Agora conte as partes, logo abaixo.</FormSuccess>
          )}

          {/* Dois botões, como na tela antiga: o principal salva E leva para as partes; o de baixo
              é o desvio para quem quer parar na nota geral. Enquanto havia um só, "detalhar"
              dependia de a pessoa notar um cartão abaixo da dobra. */}
          {!locked && (
            <div className="space-y-2">
              <Button
                className="w-full"
                loading={submitRating.isPending}
                disabled={general.score == null || commentRequired}
                onClick={() => handleSubmitGeneral("detalhar")}
              >
                {hasGeneralRating ? "Atualizar e avaliar em detalhes →" : "Enviar e avaliar em detalhes →"}
              </Button>
              {!hasGeneralRating && (
                <Button
                  variant="ghost"
                  className="w-full"
                  disabled={submitRating.isPending || general.score == null || commentRequired}
                  onClick={() => handleSubmitGeneral("sair")}
                >
                  Só enviar a nota geral
                </Button>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {hasGeneralRating && (
        // `scroll-mt-4` para o topo do cartão não encostar na borda quando a rolagem para aqui.
        <Card ref={detalheRef} className="scroll-mt-4">
          <CardHeader>
            <p className="text-xs uppercase tracking-wide text-muted">Avaliação detalhada</p>
            <CardTitle>Como foram as partes?</CardTitle>
            {/* Os dois textos da tela antiga: quantas estrelas a pessoa deu, e que tudo aqui é
                opcional. O primeiro fecha o ciclo do que ela acabou de enviar. */}
            {form.rating?.score != null && (
              <p className="text-sm text-muted">
                Você deu {form.rating.score} estrela{form.rating.score > 1 ? "s" : ""} para este
                evento.
              </p>
            )}
            <p className="text-sm text-muted">
              Agora você pode avaliar aspectos específicos e as pessoas com quem trabalhou. Tudo é
              opcional — só avalie o que quiser.
            </p>
          </CardHeader>
          <CardContent className="space-y-5">
            {form.general_categories.length > 0 && (
              <section className="space-y-3">
                <h2 className="text-sm font-semibold uppercase text-muted">Produção</h2>
                {form.general_categories.map((category) => (
                  <ScoreBlock
                    key={category}
                    name={`sub-${category}`}
                    label={CATEGORY_LABELS[category]}
                    sublabel={CATEGORY_HINTS[category]}
                    entry={subs[category] ?? EMPTY_ENTRY}
                    onChange={(next) => setSub(category, next)}
                    disabled={locked}
                  />
                ))}
              </section>
            )}

            {PERSON_GROUP_ORDER.map((group) => {
              const members = form.people.filter((person) => person.category === group);
              if (members.length === 0) return null;
              return (
                <section key={group} className="space-y-3">
                  <h2 className="text-sm font-semibold uppercase text-muted">
                    {PERSON_GROUP_LABELS[group]}
                  </h2>
                  {members.map((person) => {
                    const key = personKey(person.category, person.talent_id);
                    return (
                      <ScoreBlock
                        key={key}
                        name={`sub-${key}`}
                        label={person.name}
                        sublabel={person.character_name}
                        photoUrl={person.photo_face_url}
                        entry={subs[key] ?? EMPTY_ENTRY}
                        onChange={(next) => setSub(key, next)}
                        disabled={locked}
                      />
                    );
                  })}
                </section>
              );
            })}

            {savedStep === "detail" && (
              <FormSuccess>Avaliação completa enviada. Obrigado pelo retorno!</FormSuccess>
            )}

            {!locked && (
              <div className="space-y-2">
                <Button
                  className="w-full"
                  loading={submitDetail.isPending}
                  onClick={handleSubmitDetail}
                >
                  Enviar avaliação completa ✓
                </Button>
                {/* "Pular — já enviei o suficiente" da tela antiga: a nota geral já está salva
                    neste ponto, então sair daqui não perde nada. */}
                <Button variant="ghost" className="w-full" onClick={() => navigate("/historico")}>
                  Pular — já enviei o suficiente
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <FormError>{formError}</FormError>

      {form.rating?.detail_submitted_at && (
        <p className="flex items-center justify-center gap-2 text-sm text-green">
          <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
          Avaliação completa enviada.
        </p>
      )}

      {/* Escondido quando o bloco das partes está aberto: lá dentro já existe o "Pular — já enviei
          o suficiente", que vai para o mesmo lugar. Dois botões fantasma colados só dão dúvida. */}
      {!(hasGeneralRating && !locked) && (
        <Button variant="ghost" className="w-full" onClick={() => navigate("/historico")}>
          Voltar ao histórico
        </Button>
      )}
    </div>
  );
}
