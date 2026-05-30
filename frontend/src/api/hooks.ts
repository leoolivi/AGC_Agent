/** Typed React Query hooks for backend API */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import type {
  Confirmation,
  DocumentItem,
  InboxItem,
  UnreadCount,
  UploadResponse,
} from "./types";

// ─── Inbox ───

export function useInbox(status?: string) {
  return useQuery<InboxItem[]>({
    queryKey: ["inbox", status],
    queryFn: async () => {
      const params = status ? { status_filter: status } : {};
      const res = await api.get<InboxItem[]>("/api/v1/inbox", { params });
      return res.data;
    },
  });
}

export function useUnreadCount() {
  return useQuery<UnreadCount>({
    queryKey: ["inbox", "unread"],
    queryFn: async () => (await api.get<UnreadCount>("/api/v1/inbox/unread-count")).data,
    refetchInterval: 30_000,
  });
}

export function useActOnInbox() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ itemId, actionId }: { itemId: string; actionId: string }) => {
      await api.post(`/api/v1/inbox/${itemId}/act`, { action_id: actionId });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["inbox"] }),
  });
}

export function useDismissInbox() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (itemId: string) => {
      await api.post(`/api/v1/inbox/${itemId}/dismiss`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["inbox"] }),
  });
}

// ─── Documents ───

export function useDocuments() {
  return useQuery<DocumentItem[]>({
    queryKey: ["documents"],
    queryFn: async () => (await api.get<DocumentItem[]>("/api/v1/documents")).data,
  });
}

export function useUploadDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const res = await api.post<UploadResponse>("/api/v1/documents/upload", form);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }),
  });
}

// ─── Confirmations ───

export function useConfirmations() {
  return useQuery<Confirmation[]>({
    queryKey: ["confirmations"],
    queryFn: async () => (await api.get<Confirmation[]>("/api/v1/confirmations")).data,
  });
}

export function useApproveConfirmation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/api/v1/confirmations/${id}/approve`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["confirmations"] }),
  });
}

export function useRejectConfirmation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, comment }: { id: string; comment?: string }) => {
      await api.post(`/api/v1/confirmations/${id}/reject`, { user_comment: comment });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["confirmations"] }),
  });
}
