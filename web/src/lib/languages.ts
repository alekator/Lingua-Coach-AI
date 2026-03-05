export const POPULAR_LANGUAGES: Array<{ code: string; label: string }> = [
  { code: "en", label: "English" },
  { code: "es", label: "Spanish" },
  { code: "de", label: "German" },
  { code: "fr", label: "French" },
  { code: "ru", label: "Russian" },
  { code: "it", label: "Italian" },
  { code: "pt", label: "Portuguese" },
  { code: "ja", label: "Japanese" },
  { code: "ko", label: "Korean" },
  { code: "zh", label: "Chinese" },
  { code: "ar", label: "Arabic" },
  { code: "hi", label: "Hindi" },
  { code: "tr", label: "Turkish" },
  { code: "nl", label: "Dutch" },
  { code: "pl", label: "Polish" },
  { code: "uk", label: "Ukrainian" },
];

export function normalizeLanguageCode(value: string): string {
  return value.trim().toLowerCase();
}

export function languageLabelByCode(code: string): string {
  const normalized = normalizeLanguageCode(code);
  const found = POPULAR_LANGUAGES.find((item) => item.code === normalized);
  return found ? `${found.label} (${found.code})` : normalized;
}

