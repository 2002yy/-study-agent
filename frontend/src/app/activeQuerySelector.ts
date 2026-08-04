export type ActiveQueryInput = {
  input: string;
  lastRagQuery?: string;
};

/**
 * Resolve the cross-domain query used by Sources search and controlled tools.
 * Current user input wins; when the composer is empty, reuse the latest RAG query.
 */
export function selectActiveQuery({
  input,
  lastRagQuery,
}: ActiveQueryInput): string {
  const currentInput = input.trim();
  if (currentInput) return currentInput;
  return lastRagQuery?.trim() ?? "";
}
