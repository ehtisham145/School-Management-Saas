"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { X } from "lucide-react";

type ModalProps = {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  closeLabel: string;
  children: ReactNode;
};

/**
 * Built on the native dialog, which traps focus, closes on Escape and returns
 * focus to the button that opened it.
 */
export function Modal({ open, onClose, title, description, closeLabel, children }: ModalProps) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;

    if (open && !dialog.open) {
      dialog.showModal();
    } else if (!open && dialog.open) {
      dialog.close();
    }

    // Next.js keeps a page alive after leaving it (cacheComponents), and an open
    // dialog would stay on top of the next page and block every click.
    return () => {
      if (dialog.open) dialog.close();
    };
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-labelledby="modal-title"
      onClose={() => {
        // The event arrives late, so a dialog already reopened is not closed by it.
        if (!ref.current?.open) onClose();
      }}
      onClick={(event) => {
        if (event.target === ref.current) onClose();
      }}
      className="modal-dialog m-auto w-[calc(100%-32px)] max-w-[600px] rounded-card bg-bg p-0 text-ink shadow-soft"
    >
      <div className="max-h-[calc(100dvh-48px)] overflow-y-auto p-5 sm:p-6">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h2 id="modal-title" className="text-xl text-navy-deep">
              {title}
            </h2>
            {description && <p className="mt-1.5 text-sm text-ink-soft">{description}</p>}
          </div>
          <button
            type="button"
            aria-label={closeLabel}
            onClick={onClose}
            className="flex size-9 shrink-0 cursor-pointer items-center justify-center rounded-control text-ink-soft hover:bg-navy-soft hover:text-navy"
          >
            <X aria-hidden="true" className="size-5" />
          </button>
        </div>
        {children}
      </div>
    </dialog>
  );
}
