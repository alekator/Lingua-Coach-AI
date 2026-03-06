type AudioPlayerProps = {
  audioUrl?: string | null;
  label?: string;
};

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

function resolveAudioUrl(url: string): string {
  try {
    return new URL(url, API_BASE).toString();
  } catch {
    return url;
  }
}

export function AudioPlayer({ audioUrl, label = "Coach audio reply" }: AudioPlayerProps) {
  if (!audioUrl) return null;
  if (audioUrl.startsWith("offline://")) {
    let reason = "Audio is unavailable for this turn.";
    if (audioUrl.includes("tts-unavailable")) {
      reason = "Audio is temporarily unavailable: TTS runtime failed for this response.";
    } else if (audioUrl.includes("tts-language-limited")) {
      reason = "Audio is unavailable for selected target language in current TTS mode.";
    } else if (audioUrl.includes("budget-blocked")) {
      reason = "Audio is blocked by current usage budget limits.";
    }
    return (
      <div className="audio-player stack">
        <p>{label}: unavailable</p>
        <p className="status error">{reason}</p>
      </div>
    );
  }
  const src = resolveAudioUrl(audioUrl);
  return (
    <div className="audio-player stack">
      <p>
        {label}: <a href={src} target="_blank" rel="noreferrer">{src}</a>
      </p>
      <audio controls preload="none" src={src}>
        Your browser does not support audio playback.
      </audio>
    </div>
  );
}
