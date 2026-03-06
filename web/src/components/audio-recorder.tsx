import { useEffect, useRef, useState } from "react";

type AudioRecorderProps = {
  onRecordedFile: (file: File | null) => void;
  disabled?: boolean;
};

function formatSeconds(total: number): string {
  const mins = Math.floor(total / 60)
    .toString()
    .padStart(2, "0");
  const secs = Math.floor(total % 60)
    .toString()
    .padStart(2, "0");
  return `${mins}:${secs}`;
}

export function AudioRecorder({ onRecordedFile, disabled = false }: AudioRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [recordedName, setRecordedName] = useState("");
  const [error, setError] = useState("");
  const [isSupported] = useState(
    typeof window !== "undefined" &&
      typeof window.MediaRecorder !== "undefined" &&
      !!navigator.mediaDevices?.getUserMedia,
  );

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<number | null>(null);
  const startedAtRef = useRef<number | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  async function startRecording() {
    if (!isSupported || disabled || isRecording) return;
    try {
      setError("");
      chunksRef.current = [];
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        if (timerRef.current) {
          window.clearInterval(timerRef.current);
          timerRef.current = null;
        }
        setIsRecording(false);

        const mimeType = mediaRecorder.mimeType || "audio/webm";
        const extension = mimeType.includes("ogg") ? "ogg" : "webm";
        const fileName = `recorded-audio-${Date.now()}.${extension}`;
        const blob = new Blob(chunksRef.current, { type: mimeType });
        const file = new File([blob], fileName, { type: mimeType });

        onRecordedFile(file);
        setRecordedName(file.name);

        if (streamRef.current) {
          streamRef.current.getTracks().forEach((track) => track.stop());
          streamRef.current = null;
        }
      };

      startedAtRef.current = Date.now();
      setSeconds(0);
      timerRef.current = window.setInterval(() => {
        if (!startedAtRef.current) return;
        setSeconds((Date.now() - startedAtRef.current) / 1000);
      }, 250);

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Microphone access failed");
    }
  }

  function stopRecording() {
    if (!mediaRecorderRef.current || !isRecording) return;
    mediaRecorderRef.current.stop();
  }

  function clearRecording() {
    onRecordedFile(null);
    setRecordedName("");
    setSeconds(0);
  }

  if (!isSupported) {
    return <p className="status empty">Microphone recording is unavailable in this environment.</p>;
  }

  return (
    <div className="audio-recorder stack">
      <div className="row">
        {!isRecording ? (
          <button type="button" onClick={startRecording} disabled={disabled}>
            Start recording
          </button>
        ) : (
          <button type="button" onClick={stopRecording}>
            Stop recording ({formatSeconds(seconds)})
          </button>
        )}
        <button type="button" onClick={clearRecording} disabled={!recordedName || isRecording}>
          Clear recording
        </button>
      </div>
      <p>{recordedName ? `Recorded: ${recordedName}` : "No recorded clip yet."}</p>
      {error && <p className="status error">{error}</p>}
    </div>
  );
}
