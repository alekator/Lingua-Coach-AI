import { LanguagePicker } from "./language-picker";

type LanguagePairSelectorProps = {
  nativeLang: string;
  targetLang: string;
  onNativeLangChange: (value: string) => void;
  onTargetLangChange: (value: string) => void;
  ariaPrefix: string;
};

const PRESET_PAIRS: Array<{ native: string; target: string; label: string }> = [
  { native: "ru", target: "en", label: "RU -> EN" },
  { native: "de", target: "en", label: "DE -> EN" },
  { native: "es", target: "en", label: "ES -> EN" },
  { native: "pt", target: "en", label: "PT -> EN" },
  { native: "fr", target: "en", label: "FR -> EN" },
];

export function LanguagePairSelector({
  nativeLang,
  targetLang,
  onNativeLangChange,
  onTargetLangChange,
  ariaPrefix,
}: LanguagePairSelectorProps) {
  return (
    <div className="stack">
      <div className="row">
        <button
          type="button"
          aria-label={`${ariaPrefix} swap languages`}
          onClick={() => {
            onNativeLangChange(targetLang);
            onTargetLangChange(nativeLang);
          }}
        >
          Swap native/target
        </button>
      </div>
      <div className="row">
        {PRESET_PAIRS.map((pair) => (
          <button
            key={pair.label}
            type="button"
            aria-label={`${ariaPrefix} preset ${pair.label}`}
            onClick={() => {
              onNativeLangChange(pair.native);
              onTargetLangChange(pair.target);
            }}
          >
            {pair.label}
          </button>
        ))}
      </div>
      <LanguagePicker
        label="Native language"
        ariaLabel={`${ariaPrefix} native language`}
        value={nativeLang}
        onChange={onNativeLangChange}
      />
      <LanguagePicker
        label="Target language"
        ariaLabel={`${ariaPrefix} target language`}
        value={targetLang}
        onChange={onTargetLangChange}
      />
    </div>
  );
}

