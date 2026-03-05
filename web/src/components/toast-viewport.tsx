import { useToastStore } from "../store/toast-store";

export function ToastViewport() {
  const toasts = useToastStore((s) => s.toasts);
  const remove = useToastStore((s) => s.remove);

  return (
    <div className="toast-viewport">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast toast-${toast.kind}`}>
          <span>{toast.message}</span>
          <button type="button" onClick={() => remove(toast.id)}>
            x
          </button>
        </div>
      ))}
    </div>
  );
}
