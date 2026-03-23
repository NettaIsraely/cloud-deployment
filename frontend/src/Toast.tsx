import { useEffect, useState } from "react";

export type ToastType = "success" | "error";

export interface ToastItem {
  id: number;
  type: ToastType;
  message: string;
}

const TOAST_DURATION_MS = 4000;

export function ToastContainer({
  toasts,
  remove,
}: {
  toasts: ToastItem[];
  remove: (id: number) => void;
}) {
  return (
    <div className="toast-container" aria-live="polite">
      {toasts.map((t) => (
        <ToastItem key={t.id} item={t} onRemove={() => remove(t.id)} />
      ))}
    </div>
  );
}

function ToastItem({ item, onRemove }: { item: ToastItem; onRemove: () => void }) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const show = requestAnimationFrame(() => setVisible(true));
    const t = setTimeout(() => {
      setVisible(false);
      setTimeout(onRemove, 200);
    }, TOAST_DURATION_MS);
    return () => {
      cancelAnimationFrame(show);
      clearTimeout(t);
    };
  }, [onRemove]);
  return (
    <div
      className={`toast toast-${item.type} ${visible ? "toast-visible" : ""}`}
      role="alert"
    >
      {item.message}
    </div>
  );
}

let nextId = 0;
export function useToasts() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const add = (type: ToastType, message: string) => {
    const id = ++nextId;
    setToasts((prev) => [...prev, { id, type, message }]);
  };
  const remove = (id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };
  return { toasts, add, remove };
}
