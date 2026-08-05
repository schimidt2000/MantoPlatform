import { useState, type FormEvent } from "react";
import { useParams } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Button, Card, CardContent, Skeleton } from "@manto/ui";
import { useFeedbackEvent, useSubmitFeedback } from "../lib/feedback";
import { StarRating } from "../components/feedback/StarRating";
import { TagChips } from "../components/feedback/TagChips";

export function AvaliarPage() {
  const { token = "" } = useParams<{ token: string }>();
  const feedbackEvent = useFeedbackEvent(token);
  const submitFeedback = useSubmitFeedback(token);
  const reducedMotion = useReducedMotion();

  const [clientName, setClientName] = useState("");
  const [score, setScore] = useState(0);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  function handleScoreChange(nextScore: number) {
    setScore(nextScore);
    setSelectedTags([]); // troca de faixa (positiva/atenção) sempre limpa a seleção anterior
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    submitFeedback.mutate(
      { client_name: clientName, score, tags: selectedTags, comment },
      {
        onSuccess: () => setSubmitted(true),
        onError: (err) => setError(err.message),
      },
    );
  }

  if (feedbackEvent.isLoading) {
    return (
      <div className="mx-auto max-w-md space-y-4 px-4 py-10">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (feedbackEvent.isError) {
    return (
      <div className="mx-auto flex min-h-[70vh] max-w-md items-center px-4 py-10">
        <Card className="w-full p-4 text-center">
          <CardContent className="flex flex-col items-center gap-3 pt-4">
            <div className="text-4xl">🔗</div>
            <h1 className="font-display text-xl text-ink">Este link de avaliação não é válido</h1>
            <p className="text-sm text-muted">
              Confira se o link foi copiado corretamente, ou peça um novo link a quem enviou.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (submitted) {
    const reviewUrl = score === 5 ? feedbackEvent.data?.google_review_url : undefined;
    return (
      <div className="mx-auto flex min-h-[70vh] max-w-md items-center px-4 py-10">
        <Card className="w-full p-4 text-center">
          <CardContent className="flex flex-col items-center gap-3 pt-4">
            <div className="text-4xl">💜</div>
            <h1 className="font-display text-xl text-ink">Obrigado pelo seu feedback!</h1>
            <p className="text-sm text-muted">
              Sua opinião ajuda a equipe da Manto Produções a ficar cada vez melhor.
            </p>
            {reviewUrl && (
              <motion.div
                initial={reducedMotion ? undefined : { opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25, delay: 0.15 }}
                className="mt-2 w-full space-y-2"
              >
                <p className="text-sm text-ink">
                  Sua avaliação 5 estrelas nos ajuda muito! Que tal deixar também no Google?
                </p>
                <Button asChild size="lg" className="w-full">
                  <a href={reviewUrl} target="_blank" rel="noopener noreferrer">
                    ⭐ Avaliar no Google
                  </a>
                </Button>
              </motion.div>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  const data = feedbackEvent.data!;
  const tagOptions = score === 5 ? data.positive_tags : data.attention_tags;
  const cardsTitle =
    score === 5 ? "Incrível! O que mais se destacou?" : "Obrigado! Onde podemos melhorar para a próxima?";

  return (
    <div className="mx-auto max-w-md px-4 py-8">
      <header className="mb-6 text-center">
        <div className="mb-2 text-3xl">💜</div>
        <div className="text-lg font-bold text-ink">{data.event_title}</div>
        {data.event_date && <div className="text-sm text-muted">{data.event_date}</div>}
      </header>

      {error && (
        <div className="mb-5 rounded-lg border border-red bg-red-soft p-3 text-center text-sm text-red" role="alert">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="mb-2 block text-sm font-bold text-muted" htmlFor="clientName">
            Seu nome
          </label>
          <input
            id="clientName"
            className="h-11 w-full rounded-md border border-line bg-panel px-3 text-sm text-ink"
            placeholder="Como podemos te chamar?"
            maxLength={200}
            value={clientName}
            onChange={(e) => setClientName(e.target.value)}
          />
        </div>

        <p className="text-center text-base font-bold text-ink">
          Como foi a experiência com a equipe da Manto Produções?
        </p>

        <StarRating score={score} onChange={handleScoreChange} />

        <AnimatePresence>
          {score > 0 && (
            <motion.div
              initial={reducedMotion ? undefined : { height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={reducedMotion ? undefined : { height: 0, opacity: 0 }}
              className="space-y-4 overflow-hidden"
            >
              <p className="text-center text-sm font-bold text-ink">{cardsTitle}</p>
              <TagChips options={tagOptions} selected={selectedTags} onChange={setSelectedTags} />

              <div>
                <label className="mb-2 block text-sm font-bold text-muted" htmlFor="comment">
                  Quer deixar um recado ou sugestão? (Opcional)
                </label>
                <textarea
                  id="comment"
                  className="min-h-24 w-full rounded-md border border-line bg-panel p-3 text-sm text-ink"
                  placeholder="Conte um pouco mais, se quiser..."
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                />
              </div>

              <Button type="submit" size="lg" className="w-full" loading={submitFeedback.isPending}>
                {submitFeedback.isPending ? "Enviando..." : "Enviar avaliação"}
              </Button>
            </motion.div>
          )}
        </AnimatePresence>
      </form>
    </div>
  );
}
