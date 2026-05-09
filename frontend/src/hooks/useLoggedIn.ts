"use client";

import { useSyncExternalStore } from "react";
import { getLoggedInSnapshot, subscribeAuth } from "@/lib/auth";

/** True iff `shopguard.token` exists (synced with login/logout/events). */
export function useLoggedIn(): boolean {
  return useSyncExternalStore(subscribeAuth, getLoggedInSnapshot, () => false);
}
