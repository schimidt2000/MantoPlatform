/**
 * Data e hora "de parede" — sem fuso horário.
 *
 * O banco guarda `start_at`/`end_at` como *naive São Paulo* (ver
 * `app/calendar/service.py::parse_event_datetime`), e a API serializa com `.isoformat()`.
 * O que chega no React é, portanto, `"2026-08-15T19:30:00"` — **19:30 em São Paulo**, e não um
 * instante em UTC.
 *
 * `new Date("2026-08-15T19:30:00")` interpreta essa string como horário **local do navegador**;
 * chamar `.toISOString()` em seguida converte para UTC e devolve `"2026-08-15T22:30:00.000Z"`.
 * Foi exatamente esse caminho que fez o formulário de edição abrir todo evento com +3h e, ao
 * salvar, gravar o horário deslocado no banco e empurrá-lo para o Google Agenda.
 *
 * Regra: para **preencher formulário** (campos `<input type="date">` / `<input type="time">`) e
 * para **comparar datas**, recorte a string — nunca passe por `Date`.
 */

/** "2026-08-15T19:30:00" → "2026-08-15". Devolve "" para nulo/vazio. */
export function dataDeIsoLocal(iso: string | null | undefined): string {
  return iso ? iso.slice(0, 10) : "";
}

/** "2026-08-15T19:30:00" → "19:30". Devolve "" para nulo/vazio. */
export function horaDeIsoLocal(iso: string | null | undefined): string {
  return iso ? iso.slice(11, 16) : "";
}

/** Hoje em "YYYY-MM-DD" pelo relógio do usuário — o `toISOString()` erraria o dia à noite. */
export function hojeYmd(): string {
  const agora = new Date();
  const mes = String(agora.getMonth() + 1).padStart(2, "0");
  const dia = String(agora.getDate()).padStart(2, "0");
  return `${agora.getFullYear()}-${mes}-${dia}`;
}
