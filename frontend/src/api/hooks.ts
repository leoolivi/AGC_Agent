/** Typed React Query hooks for backend API */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import type {
  Confirmation,
  DocumentItem,
  InboxItem,
  UnreadCount,
  UploadResponse,
  Folder,
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

export function useDocuments(folderId?: string | null) {
  return useQuery<DocumentItem[]>({
    queryKey: ["documents", folderId],
    queryFn: async () => {
      const params = folderId ? { folder_id: folderId } : {};
      const res = await api.get<DocumentItem[]>("/api/v1/documents", { params });
      return res.data;
    },
  });
}

export function useUploadDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ file, folderId }: { file: File; folderId?: string | null }) => {
      const form = new FormData();
      form.append("file", file);
      const url = folderId
        ? `/api/v1/documents/upload?folder_id=${folderId}`
        : "/api/v1/documents/upload";
      const res = await api.post<UploadResponse>(url, form);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

export function useUpdateDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      docId,
      filename,
      folderId,
    }: {
      docId: string;
      filename?: string;
      folderId?: string | null;
    }) => {
      const res = await api.patch(`/api/v1/documents/${docId}`, {
        filename,
        folder_id: folderId === null ? "root" : folderId,
      });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

// ─── Folders ───

export function useFolder(folderId?: string | null) {
  return useQuery<Folder | null>({
    queryKey: ["folder", folderId],
    queryFn: async () => {
      if (!folderId || folderId === "root") return null;
      const res = await api.get<Folder>(`/api/v1/folders/${folderId}`);
      return res.data;
    },
    enabled: !!folderId && folderId !== "root",
  });
}

export function useFolders(parentId?: string | null) {
  return useQuery<Folder[]>({
    queryKey: ["folders", parentId],
    queryFn: async () => {
      const params = parentId ? { parent_id: parentId } : {};
      const res = await api.get<Folder[]>("/api/v1/folders", { params });
      return res.data;
    },
  });
}

export function useCreateFolder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ name, parentId }: { name: string; parentId: string | null }) => {
      const res = await api.post<Folder>("/api/v1/folders", {
        name,
        parent_id: parentId,
      });
      return res.data;
    },
    onSuccess: (_, variables) => {
      qc.invalidateQueries({ queryKey: ["folders", variables.parentId] });
    },
  });
}

export function useUpdateFolder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      folderId,
      name,
      parentId,
    }: {
      folderId: string;
      name?: string;
      parentId?: string | null;
    }) => {
      const res = await api.patch<Folder>(`/api/v1/folders/${folderId}`, {
        name,
        parent_id: parentId === null ? "root" : parentId,
      });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["folders"] });
    },
  });
}

export function useDeleteFolder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (folderId: string) => {
      await api.delete(`/api/v1/folders/${folderId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["folders"] });
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
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
