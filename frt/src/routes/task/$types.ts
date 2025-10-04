import type { TranslationTask } from "$lib/server/db/schema";

export interface PageData {
  tid: string;
}

export interface LayoutData {
  // Add any layout data types here
}

// Re-export the TranslationTask type for client-side use
export type { TranslationTask };
