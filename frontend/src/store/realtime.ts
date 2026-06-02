import { create } from "zustand";

export interface ProcessingFeedItem {
  id: string;
  filename: string;
  source: string;
  status: string;
  documentType?: string;
  timestamp: number;
  needsAttention?: boolean;
}

export interface RealtimeNotification {
  id: string;
  title: string;
  body: string;
  level: string;
  timestamp: number;
}

export interface SourceStatus {
  id: string;
  sourceType: string;
  status: string;
  lastSyncAt?: string;
}

interface RealtimeState {
  processingFeed: ProcessingFeedItem[];
  notifications: RealtimeNotification[];
  sourceStatuses: Record<string, SourceStatus>;
  addProcessingItem: (item: ProcessingFeedItem) => void;
  updateProcessingItem: (id: string, patch: Partial<ProcessingFeedItem>) => void;
  addNotification: (n: RealtimeNotification) => void;
  updateSourceStatus: (status: SourceStatus) => void;
  handleEvent: (event: { event_type: string; payload: Record<string, unknown> }) => void;
}

const MAX_FEED = 20;

export const useRealtimeStore = create<RealtimeState>((set, get) => ({
  processingFeed: [],
  notifications: [],
  sourceStatuses: {},

  addProcessingItem: (item) =>
    set((s) => ({
      processingFeed: [item, ...s.processingFeed].slice(0, MAX_FEED),
    })),

  updateProcessingItem: (id, patch) =>
    set((s) => ({
      processingFeed: s.processingFeed.map((i) => (i.id === id ? { ...i, ...patch } : i)),
    })),

  addNotification: (n) =>
    set((s) => ({
      notifications: [n, ...s.notifications].slice(0, 50),
    })),

  updateSourceStatus: (status) =>
    set((s) => ({
      sourceStatuses: { ...s.sourceStatuses, [status.id]: status },
    })),

  handleEvent: (event) => {
    const { event_type, payload } = event;
    if (event_type === "processing_status") {
      const docId = String(payload.document_id ?? crypto.randomUUID());
      const existing = get().processingFeed.find((i) => i.id === docId);
      const item: ProcessingFeedItem = {
        id: docId,
        filename: String(payload.filename ?? "documento"),
        source: String(payload.source ?? "upload"),
        status: String(payload.status ?? "processing"),
        documentType: payload.document_type as string | undefined,
        timestamp: Date.now(),
        needsAttention: payload.status === "needs_attention",
      };
      if (existing) {
        get().updateProcessingItem(docId, item);
      } else {
        get().addProcessingItem(item);
      }
    } else if (event_type === "notification") {
      get().addNotification({
        id: crypto.randomUUID(),
        title: String(payload.title ?? ""),
        body: String(payload.body ?? ""),
        level: String(payload.level ?? "info"),
        timestamp: Date.now(),
      });
    } else if (event_type === "source_status") {
      get().updateSourceStatus({
        id: String(payload.id ?? ""),
        sourceType: String(payload.source_type ?? ""),
        status: String(payload.status ?? ""),
        lastSyncAt: payload.last_sync_at as string | undefined,
      });
    }
  },
}));
