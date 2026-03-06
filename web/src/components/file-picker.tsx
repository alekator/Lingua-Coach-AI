import { useRef, useState } from "react";
import { t, uiLocaleFromNativeLang } from "../lib/i18n";
import { useAppStore } from "../store/app-store";

type FilePickerProps = {
  id: string;
  ariaLabel: string;
  accept?: string;
  disabled?: boolean;
  onFileChange: (file: File | null) => void;
};

export function FilePicker({ id, ariaLabel, accept, disabled, onFileChange }: FilePickerProps) {
  const nativeLang = useAppStore((s) => s.activeWorkspaceNativeLang);
  const locale = uiLocaleFromNativeLang(nativeLang);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [fileName, setFileName] = useState("");

  return (
    <div className="file-picker">
      <input
        ref={inputRef}
        id={id}
        aria-label={ariaLabel}
        className="file-picker-native"
        type="file"
        accept={accept}
        disabled={disabled}
        onChange={(event) => {
          const selected = event.target.files?.[0] ?? null;
          setFileName(selected?.name ?? "");
          onFileChange(selected);
        }}
      />
      <button type="button" className="file-picker-trigger" onClick={() => inputRef.current?.click()} disabled={disabled}>
        {t(locale, "file_picker_choose")}
      </button>
      <span className="file-picker-name">{fileName || t(locale, "file_picker_empty")}</span>
    </div>
  );
}
