import type ar from "../../messages/ar.json";
import type en from "../../messages/en.json";

// A translation key missing from either language fails the type check.
type Extends<A extends B, B> = A;
export type MessagesMatch = [Extends<typeof en, typeof ar>, Extends<typeof ar, typeof en>];

declare module "next-intl" {
  interface AppConfig {
    Messages: typeof en;
  }
}
