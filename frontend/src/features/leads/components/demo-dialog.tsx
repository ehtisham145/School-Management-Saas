"use client";

import dynamic from "next/dynamic";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ComponentProps,
  type ReactNode,
} from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { Spinner } from "@/components/ui/spinner";
import type { Plan } from "../api";

// The form code is only downloaded when someone opens it.
const DemoForm = dynamic(() => import("./demo-form").then((module) => module.DemoForm), {
  ssr: false,
  loading: () => (
    <div className="flex justify-center py-12 text-navy">
      <Spinner className="size-6" />
    </div>
  ),
});

const DemoDialogContext = createContext<((plan?: Plan) => void) | null>(null);

export function DemoDialogProvider({ children }: { children: ReactNode }) {
  const t = useTranslations("Leads.demo");
  const tLang = useTranslations("Marketing.lang");

  const [state, setState] = useState<{ open: boolean; plan?: Plan; session: number }>({
    open: false,
    session: 0,
  });

  const openDialog = useCallback((plan?: Plan) => {
    setState((current) => ({ open: true, plan, session: current.session + 1 }));
  }, []);

  const closeDialog = useCallback(() => {
    setState((current) => ({ ...current, open: false }));
  }, []);

  const value = useMemo(() => openDialog, [openDialog]);

  return (
    <DemoDialogContext.Provider value={value}>
      {children}
      <Modal
        open={state.open}
        onClose={closeDialog}
        title={t("title")}
        description={t("description")}
        closeLabel={tLang("close")}
      >
        {state.open && <DemoForm key={state.session} plan={state.plan} onClose={closeDialog} />}
      </Modal>
    </DemoDialogContext.Provider>
  );
}

type DemoButtonProps = ComponentProps<typeof Button> & { plan?: Plan };

/** Opens the Book a demo form. Works anywhere inside the marketing layout. */
export function DemoButton({ plan, ...props }: DemoButtonProps) {
  const openDialog = useContext(DemoDialogContext);

  return <Button type="button" onClick={() => openDialog?.(plan)} {...props} />;
}
