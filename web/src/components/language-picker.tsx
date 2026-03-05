import { useEffect, useMemo, useState } from "react";
import { POPULAR_LANGUAGES, normalizeLanguageCode } from "../lib/languages";

type LanguagePickerProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  ariaLabel?: string;
};

const CUSTOM_VALUE = "__custom__";

export function LanguagePicker({ label, value, onChange, ariaLabel }: LanguagePickerProps) {
  const normalized = normalizeLanguageCode(value);
  const isPopular = useMemo(
    () => POPULAR_LANGUAGES.some((item) => item.code === normalized),
    [normalized],
  );
  const [mode, setMode] = useState<string>(isPopular ? normalized : CUSTOM_VALUE);
  const [customCode, setCustomCode] = useState<string>(isPopular ? "" : normalized);

  useEffect(() => {
    if (isPopular) {
      setMode(normalized);
      setCustomCode("");
      return;
    }
    setMode(CUSTOM_VALUE);
    setCustomCode(normalized);
  }, [isPopular, normalized]);

  return (
    <label>
      {label}
      <select
        aria-label={ariaLabel ?? label}
        value={mode}
        onChange={(e) => {
          const next = e.target.value;
          setMode(next);
          if (next !== CUSTOM_VALUE) {
            onChange(next);
          } else {
            onChange(customCode || "");
          }
        }}
      >
        {POPULAR_LANGUAGES.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.label} ({lang.code})
          </option>
        ))}
        <option value={CUSTOM_VALUE}>Custom language code</option>
      </select>
      {mode === CUSTOM_VALUE && (
        <input
          aria-label={`${ariaLabel ?? label} custom`}
          placeholder="e.g. sv, cs, vi"
          value={customCode}
          onChange={(e) => {
            const next = normalizeLanguageCode(e.target.value);
            setCustomCode(next);
            onChange(next);
          }}
        />
      )}
    </label>
  );
}

