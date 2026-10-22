/** Copia um texto e devolve se a área de transferência aceitou (o navegador pode recusar). */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
