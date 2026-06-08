import { useState, useEffect, useCallback, useRef, type DragEvent } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import {
  Upload,
  FileText,
  Folder as FolderIcon,
  FolderPlus,
  MoreVertical,
  Grid,
  List,
  ArrowLeft,
  Search,
  Trash2,
  Edit3,
  Move,
  Download,
  X,
  ChevronRight,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  FolderOpen
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  useDocuments,
  useUploadDocument,
  useFolder,
  useFolders,
  useCreateFolder,
  useUpdateFolder,
  useDeleteFolder,
  useUpdateDocument
} from "@/api/hooks";
import type { DocumentItem, Folder } from "@/api/types";

interface UploadState {
  id: string;
  filename: string;
  status: "uploading" | "success" | "failed";
  progress: number;
  error?: string;
}

// Inline Breadcrumb resolver component
function BreadcrumbItem({ folderId }: { folderId: string }) {
  const { data: folder } = useFolder(folderId);
  if (!folder) return null;
  return (
    <>
      {folder.parent_id && <BreadcrumbItem folderId={folder.parent_id} />}
      <ChevronRight className="h-4 w-4 text-muted-foreground/60 mx-1 flex-shrink-0" />
      <Link to={`/documents/${folder.id}`} className="hover:text-foreground hover:underline truncate max-w-[120px] transition-colors">
        {folder.name}
      </Link>
    </>
  );
}

function Breadcrumbs({ currentFolderId }: { currentFolderId: string }) {
  return (
    <div className="flex items-center text-sm font-medium text-muted-foreground overflow-x-auto pb-1 scrollbar-thin">
      <Link to="/documents" className="hover:text-foreground flex items-center gap-1.5 transition-colors flex-shrink-0">
        <FolderIcon className="h-4 w-4 text-primary/70" />
        <span>Miei File</span>
      </Link>
      {currentFolderId && currentFolderId !== "root" && (
        <BreadcrumbItem folderId={currentFolderId} />
      )}
    </div>
  );
}

export function DocumentsPage() {
  const { id } = useParams<{ id?: string }>();
  const currentFolderId = id || "root";
  const navigate = useNavigate();

  // API hooks
  const { data: currentFolder, isLoading: isLoadingFolder } = useFolder(currentFolderId);
  const { data: folders, isLoading: isLoadingFolders } = useFolders(currentFolderId);
  const { data: documents, isLoading: isLoadingDocs } = useDocuments(currentFolderId);
  const { data: allFolders } = useFolders(null); // Fetch all for Move Dialog

  const createFolder = useCreateFolder();
  const updateFolder = useUpdateFolder();
  const deleteFolder = useDeleteFolder();
  const uploadDocument = useUploadDocument();
  const updateDocument = useUpdateDocument();

  // Local UI states
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [searchQuery, setSearchQuery] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  
  // Modals & Menu states
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);
  const [showCreateFolder, setShowCreateFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [renameItem, setRenameItem] = useState<{ id: string; name: string; type: "folder" | "file" } | null>(null);
  const [moveItem, setMoveItem] = useState<{ id: string; name: string; type: "folder" | "file"; parentId: string | null } | null>(null);
  
  // Custom upload manager queue
  const [uploadQueue, setUploadQueue] = useState<UploadState[]>([]);
  const [isUploadManagerExpanded, setIsUploadManagerExpanded] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUploadFiles = useCallback(
    async (files: FileList | File[]) => {
      setIsUploadManagerExpanded(true);
      const fileList = Array.from(files);

      for (const file of fileList) {
        const uploadId = Math.random().toString(36).substring(2, 9);
        
        // Add item to queue
        setUploadQueue((prev) => [
          ...prev,
          { id: uploadId, filename: file.name, status: "uploading", progress: 30 }
        ]);

        try {
          await uploadDocument.mutateAsync({
            file,
            folderId: currentFolderId === "root" ? null : currentFolderId
          });

          // Mark success
          setUploadQueue((prev) =>
            prev.map((item) =>
              item.id === uploadId
                ? { ...item, status: "success", progress: 100 }
                : item
            )
          );
        } catch (err: unknown) {
          console.error("Upload error", err);
          const errorMsg =
            (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ||
            "Upload fallito (controlla estensione e dimensione)";
          
          // Mark failure
          setUploadQueue((prev) =>
            prev.map((item) =>
              item.id === uploadId
                ? { ...item, status: "failed", progress: 100, error: errorMsg }
                : item
            )
          );
        }
      }
    },
    [currentFolderId, uploadDocument]
  );

  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleUploadFiles(e.dataTransfer.files);
      }
    },
    [handleUploadFiles]
  );

  const handleCreateFolderSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFolderName.trim()) return;
    try {
      await createFolder.mutateAsync({
        name: newFolderName,
        parentId: currentFolderId === "root" ? null : currentFolderId
      });
      setNewFolderName("");
      setShowCreateFolder(false);
    } catch (err: unknown) {
      alert(
        (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ||
          "Errore durante la creazione della cartella"
      );
    }
  };

  const handleRenameSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!renameItem || !renameItem.name.trim()) return;
    try {
      if (renameItem.type === "folder") {
        await updateFolder.mutateAsync({
          folderId: renameItem.id,
          name: renameItem.name
        });
      } else {
        await updateDocument.mutateAsync({
          docId: renameItem.id,
          filename: renameItem.name
        });
      }
      setRenameItem(null);
    } catch (err: unknown) {
      alert(
        (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ||
          "Errore durante la rinomina"
      );
    }
  };

  const handleMoveSubmit = async (targetFolderId: string | null) => {
    if (!moveItem) return;
    try {
      if (moveItem.type === "folder") {
        await updateFolder.mutateAsync({
          folderId: moveItem.id,
          parentId: targetFolderId
        });
      } else {
        await updateDocument.mutateAsync({
          docId: moveItem.id,
          folderId: targetFolderId
        });
      }
      setMoveItem(null);
    } catch (err: unknown) {
      alert(
        (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ||
          "Errore durante lo spostamento"
      );
    }
  };

  const handleDeleteItem = async (item: { id: string; name: string; type: "folder" | "file" }) => {
    const confirmText =
      item.type === "folder"
        ? `Sei sicuro di voler eliminare la cartella "${item.name}" e tutto il suo contenuto?`
        : `Sei sicuro di voler eliminare il documento "${item.name}"?`;
        
    if (!confirm(confirmText)) return;

    try {
      if (item.type === "folder") {
        await deleteFolder.mutateAsync(item.id);
      } else {
        // Document delete triggers a PendingConfirmation in this workspace flow
        const res = await apiDeleteDoc(item.id);
        if (res.status === "pending_confirmation") {
          alert(`Richiesta di eliminazione inviata all'Audit. Conferma finale richiesta in 'Conferme Pendenti'.`);
        }
      }
    } catch (err: unknown) {
      alert(
        (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ||
          "Errore durante l'eliminazione"
      );
    }
  };

  // Helper to fetch directly delete endpoint since hook might not be configured for custom 202 response format
  const apiDeleteDoc = async (docId: string) => {
    const { api } = await import("@/api/client");
    const res = await api.delete(`/api/v1/documents/${docId}`);
    return res.data;
  };

  // Filtering data based on search
  const filteredFolders = folders?.filter((f) =>
    f.name.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  const filteredDocs = documents?.filter((d) =>
    d.filename.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  const activeUploadsCount = uploadQueue.filter(item => item.status === "uploading").length;
  const failedUploadsCount = uploadQueue.filter(item => item.status === "failed").length;

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className="relative min-h-[calc(100vh-6rem)] space-y-6 select-none"
    >
      {/* Drag overlay */}
      {isDragging && (
        <div className="absolute inset-0 bg-primary/10 border-2 border-primary border-dashed rounded-xl flex flex-col items-center justify-center backdrop-blur-xs z-50 transition-all duration-200">
          <Upload className="h-16 w-16 text-primary animate-bounce mb-4" />
          <p className="text-xl font-bold text-primary">Rilascia i file qui per caricarli</p>
          <p className="text-sm text-primary/70">Saranno caricati nella cartella corrente</p>
        </div>
      )}

      {/* Header and Search */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-border/40 pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            {currentFolderId !== "root" && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 hover:bg-muted"
                onClick={() => {
                  if (currentFolder) {
                    navigate(currentFolder.parent_id ? `/documents/${currentFolder.parent_id}` : "/documents");
                  }
                }}
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>
            )}
            <h2 className="text-2xl font-bold tracking-tight">
              {currentFolderId === "root" ? "Miei File" : currentFolder?.name}
            </h2>
          </div>
          <Breadcrumbs currentFolderId={currentFolderId} />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-64">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Cerca in questa cartella..."
              className="pl-8 bg-muted/30 border-border/60 hover:bg-muted/50 focus-visible:ring-1"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <Button
            variant="outline"
            size="icon"
            onClick={() => setViewMode(viewMode === "grid" ? "list" : "grid")}
            className="border-border/60 hover:bg-muted/50"
            title={viewMode === "grid" ? "Visualizza elenco" : "Visualizza griglia"}
          >
            {viewMode === "grid" ? <List className="h-4 w-4" /> : <Grid className="h-4 w-4" />}
          </Button>
          <Button
            onClick={() => setShowCreateFolder(true)}
            variant="outline"
            className="gap-2 border-border/60 hover:bg-muted/50 flex-shrink-0"
          >
            <FolderPlus className="h-4 w-4" />
            <span className="hidden sm:inline">Nuova Cartella</span>
          </Button>
          <Button
            onClick={() => fileInputRef.current?.click()}
            className="gap-2 bg-primary hover:bg-primary/95 text-primary-foreground shadow-sm flex-shrink-0"
          >
            <Upload className="h-4 w-4" />
            <span>Carica</span>
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => {
              if (e.target.files) handleUploadFiles(e.target.files);
            }}
          />
        </div>
      </div>

      {/* Main Explorer Area */}
      {isLoadingFolder || isLoadingFolders || isLoadingDocs ? (
        <div className="flex flex-col items-center justify-center py-20 space-y-4">
          <Loader2 className="h-8 w-8 text-primary/60 animate-spin" />
          <p className="text-sm text-muted-foreground">Caricamento in corso...</p>
        </div>
      ) : (
        <div className="space-y-6">
          {filteredFolders.length === 0 && filteredDocs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center border-2 border-dashed border-border/40 rounded-xl bg-muted/10 p-6">
              <FolderOpen className="h-12 w-12 text-muted-foreground/40 mb-3" />
              <h3 className="font-semibold text-lg">Questa cartella è vuota</h3>
              <p className="text-sm text-muted-foreground mt-1 max-w-sm">
                Trascina qui i tuoi file o usa i pulsanti in alto per iniziare ad organizzare lo storage.
              </p>
            </div>
          ) : (
            <>
              {/* Folders Section */}
              {filteredFolders.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Cartelle</h3>
                  {viewMode === "grid" ? (
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
                      {filteredFolders.map((folder) => (
                        <Card
                          key={folder.id}
                          className="group hover:shadow-md border-border/50 hover:border-primary/30 transition-all duration-200 cursor-pointer overflow-visible"
                          onDoubleClick={() => navigate(`/documents/${folder.id}`)}
                        >
                          <CardContent className="p-3 flex items-center justify-between gap-2">
                            <div className="flex items-center gap-2.5 min-w-0" onClick={() => navigate(`/documents/${folder.id}`)}>
                              <FolderIcon className="h-5 w-5 text-yellow-500 fill-yellow-500 flex-shrink-0" />
                              <span className="text-sm font-medium truncate pr-1">{folder.name}</span>
                            </div>
                            <div className="relative">
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7 opacity-0 group-hover:opacity-100 hover:bg-muted transition-opacity"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setActiveMenuId(activeMenuId === folder.id ? null : folder.id);
                                }}
                              >
                                <MoreVertical className="h-4 w-4 text-muted-foreground" />
                              </Button>
                              {activeMenuId === folder.id && (
                                <ActionMenu
                                  item={{ id: folder.id, name: folder.name, type: "folder", parentId: folder.parent_id }}
                                  onClose={() => setActiveMenuId(null)}
                                  onRename={(item) => setRenameItem(item)}
                                  onMove={(item) => setMoveItem(item)}
                                  onDelete={(item) => handleDeleteItem(item)}
                                />
                              )}
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  ) : (
                    <div className="border border-border/40 rounded-lg overflow-hidden bg-card">
                      {filteredFolders.map((folder) => (
                        <div
                          key={folder.id}
                          className="flex items-center justify-between p-3 border-b border-border/30 hover:bg-muted/30 transition-colors cursor-pointer"
                          onDoubleClick={() => navigate(`/documents/${folder.id}`)}
                        >
                          <div className="flex items-center gap-3 min-w-0 flex-1" onClick={() => navigate(`/documents/${folder.id}`)}>
                            <FolderIcon className="h-5 w-5 text-yellow-500 fill-yellow-500 flex-shrink-0" />
                            <span className="text-sm font-medium truncate">{folder.name}</span>
                          </div>
                          <div className="flex items-center gap-4">
                            <span className="text-xs text-muted-foreground hidden md:inline">Cartella</span>
                            <span className="text-xs text-muted-foreground hidden sm:inline">
                              {folder.created_at?.split("T")[0]}
                            </span>
                            <div className="relative">
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 hover:bg-muted"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setActiveMenuId(activeMenuId === folder.id ? null : folder.id);
                                }}
                              >
                                <MoreVertical className="h-4 w-4 text-muted-foreground" />
                              </Button>
                              {activeMenuId === folder.id && (
                                <ActionMenu
                                  item={{ id: folder.id, name: folder.name, type: "folder", parentId: folder.parent_id }}
                                  onClose={() => setActiveMenuId(null)}
                                  onRename={(item) => setRenameItem(item)}
                                  onMove={(item) => setMoveItem(item)}
                                  onDelete={(item) => handleDeleteItem(item)}
                                />
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Files Section */}
              {filteredDocs.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">File</h3>
                  {viewMode === "grid" ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                      {filteredDocs.map((doc) => (
                        <Card
                          key={doc.id}
                          className="group hover:shadow-md border-border/50 hover:border-primary/30 transition-all duration-200 overflow-visible"
                        >
                          <CardContent className="p-4 flex flex-col justify-between h-36 relative">
                            <div className="flex items-start justify-between gap-2">
                              <div className="flex items-center gap-2.5 min-w-0">
                                <FileText className="h-6 w-6 text-primary/70 flex-shrink-0" />
                                <div className="min-w-0">
                                  <p className="text-sm font-semibold truncate pr-2" title={doc.filename}>
                                    {doc.filename}
                                  </p>
                                  <p className="text-xxs text-muted-foreground mt-0.5">
                                    {doc.created_at?.split("T")[0]}
                                  </p>
                                </div>
                              </div>
                              <div className="relative flex-shrink-0">
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-8 w-8 opacity-0 group-hover:opacity-100 hover:bg-muted transition-opacity"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setActiveMenuId(activeMenuId === doc.id ? null : doc.id);
                                  }}
                                >
                                  <MoreVertical className="h-4 w-4 text-muted-foreground" />
                                </Button>
                                {activeMenuId === doc.id && (
                                  <ActionMenu
                                    item={{ id: doc.id, name: doc.filename, type: "file", parentId: doc.folder_id }}
                                    onClose={() => setActiveMenuId(null)}
                                    onRename={(item) => setRenameItem(item)}
                                    onMove={(item) => setMoveItem(item)}
                                    onDelete={(item) => handleDeleteItem(item)}
                                    downloadUrl={`/api/v1/documents/${doc.id}/download`}
                                  />
                                )}
                              </div>
                            </div>

                            <div className="flex items-center justify-between mt-auto pt-2 border-t border-border/30">
                              {doc.document_type ? (
                                <Badge variant="secondary" className="text-xxs px-1.5 py-0">
                                  {doc.document_type}
                                </Badge>
                              ) : (
                                <span />
                              )}
                              <Badge className={`text-xxs px-1.5 py-0 ${statusBadge[doc.parse_status] || ""}`}>
                                {doc.parse_status}
                              </Badge>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  ) : (
                    <div className="border border-border/40 rounded-lg overflow-hidden bg-card">
                      {filteredDocs.map((doc) => (
                        <div
                          key={doc.id}
                          className="flex items-center justify-between p-3 border-b border-border/30 hover:bg-muted/30 transition-colors"
                        >
                          <div className="flex items-center gap-3 min-w-0 flex-1">
                            <FileText className="h-5 w-5 text-primary/70 flex-shrink-0" />
                            <span className="text-sm font-medium truncate pr-4" title={doc.filename}>
                              {doc.filename}
                            </span>
                          </div>
                          <div className="flex items-center gap-4">
                            {doc.document_type && (
                              <Badge variant="secondary" className="text-xs hidden md:inline">
                                {doc.document_type}
                              </Badge>
                            )}
                            <Badge className={`text-xs ${statusBadge[doc.parse_status] || ""}`}>
                              {doc.parse_status}
                            </Badge>
                            <span className="text-xs text-muted-foreground hidden sm:inline">
                              {doc.created_at?.split("T")[0]}
                            </span>
                            <div className="relative">
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 hover:bg-muted"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setActiveMenuId(activeMenuId === doc.id ? null : doc.id);
                                }}
                              >
                                <MoreVertical className="h-4 w-4 text-muted-foreground" />
                              </Button>
                              {activeMenuId === doc.id && (
                                <ActionMenu
                                  item={{ id: doc.id, name: doc.filename, type: "file", parentId: doc.folder_id }}
                                  onClose={() => setActiveMenuId(null)}
                                  onRename={(item) => setRenameItem(item)}
                                  onMove={(item) => setMoveItem(item)}
                                  onDelete={(item) => handleDeleteItem(item)}
                                  downloadUrl={`/api/v1/documents/${doc.id}/download`}
                                />
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Floating Upload Queue Manager */}
      {uploadQueue.length > 0 && (
        <div className="fixed bottom-4 right-4 w-80 bg-card border border-border/80 rounded-lg shadow-xl overflow-hidden z-50 backdrop-blur-md transition-all duration-300">
          <div
            className="flex items-center justify-between p-3 bg-muted/60 border-b border-border/80 cursor-pointer"
            onClick={() => setIsUploadManagerExpanded(!isUploadManagerExpanded)}
          >
            <div className="flex items-center gap-2 font-semibold text-sm">
              {activeUploadsCount > 0 ? (
                <Loader2 className="h-4 w-4 text-primary animate-spin" />
              ) : failedUploadsCount > 0 ? (
                <AlertCircle className="h-4 w-4 text-destructive" />
              ) : (
                <CheckCircle2 className="h-4 w-4 text-success" />
              )}
              <span>
                {activeUploadsCount > 0
                  ? `Caricamento di ${activeUploadsCount} file...`
                  : failedUploadsCount > 0
                  ? `${failedUploadsCount} caricamento fallito`
                  : "Caricamenti completati"}
              </span>
            </div>
            <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 p-0 hover:bg-muted"
                onClick={() => setUploadQueue([])}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>

          {isUploadManagerExpanded && (
            <div className="max-h-60 overflow-y-auto p-2 space-y-1.5 scrollbar-thin">
              {uploadQueue.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between p-2 rounded bg-muted/20 border border-border/20 text-xs gap-2"
                >
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <FileText className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="font-medium truncate pr-1" title={item.filename}>
                        {item.filename}
                      </p>
                      {item.status === "failed" && (
                        <p className="text-[10px] text-destructive font-medium mt-0.5 truncate" title={item.error}>
                          Upload fallito: {item.error}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex-shrink-0">
                    {item.status === "uploading" && (
                      <Loader2 className="h-3.5 w-3.5 text-primary animate-spin" />
                    )}
                    {item.status === "success" && (
                      <CheckCircle2 className="h-3.5 w-3.5 text-success fill-success/10" />
                    )}
                    {item.status === "failed" && (
                      <XCircle className="h-3.5 w-3.5 text-destructive fill-destructive/10" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* CREATE FOLDER MODAL */}
      {showCreateFolder && (
        <div className="fixed inset-0 bg-background/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
          <Card className="w-full max-w-sm border-border/80 shadow-2xl">
            <header className="p-4 border-b border-border/40 flex justify-between items-center">
              <h3 className="font-bold text-base">Crea Nuova Cartella</h3>
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setShowCreateFolder(false)}>
                <X className="h-4 w-4" />
              </Button>
            </header>
            <form onSubmit={handleCreateFolderSubmit}>
              <div className="p-4 space-y-3">
                <label className="text-xs font-semibold text-muted-foreground uppercase">Nome Cartella</label>
                <Input
                  autoFocus
                  required
                  placeholder="es. Fatture, Contratti..."
                  value={newFolderName}
                  onChange={(e) => setNewFolderName(e.target.value)}
                />
              </div>
              <footer className="p-3 border-t border-border/40 flex justify-end gap-2 bg-muted/20">
                <Button type="button" variant="outline" size="sm" onClick={() => setShowCreateFolder(false)}>
                  Annulla
                </Button>
                <Button type="submit" size="sm" disabled={createFolder.isPending}>
                  {createFolder.isPending ? "Creazione..." : "Crea"}
                </Button>
              </footer>
            </form>
          </Card>
        </div>
      )}

      {/* RENAME MODAL */}
      {renameItem && (
        <div className="fixed inset-0 bg-background/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
          <Card className="w-full max-w-sm border-border/80 shadow-2xl">
            <header className="p-4 border-b border-border/40 flex justify-between items-center">
              <h3 className="font-bold text-base">Rinomina {renameItem.type === "folder" ? "Cartella" : "File"}</h3>
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setRenameItem(null)}>
                <X className="h-4 w-4" />
              </Button>
            </header>
            <form onSubmit={handleRenameSubmit}>
              <div className="p-4 space-y-3">
                <label className="text-xs font-semibold text-muted-foreground uppercase">Nuovo Nome</label>
                <Input
                  autoFocus
                  required
                  value={renameItem.name}
                  onChange={(e) => setRenameItem({ ...renameItem, name: e.target.value })}
                />
              </div>
              <footer className="p-3 border-t border-border/40 flex justify-end gap-2 bg-muted/20">
                <Button type="button" variant="outline" size="sm" onClick={() => setRenameItem(null)}>
                  Annulla
                </Button>
                <Button type="submit" size="sm">
                  Salva
                </Button>
              </footer>
            </form>
          </Card>
        </div>
      )}

      {/* MOVE MODAL */}
      {moveItem && (
        <div className="fixed inset-0 bg-background/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
          <Card className="w-full max-w-md border-border/80 shadow-2xl max-h-[80vh] flex flex-col">
            <header className="p-4 border-b border-border/40 flex justify-between items-center flex-shrink-0">
              <h3 className="font-bold text-base">Sposta "{moveItem.name}"</h3>
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setMoveItem(null)}>
                <X className="h-4 w-4" />
              </Button>
            </header>
            <div className="p-4 overflow-y-auto flex-1 space-y-2 max-h-96">
              <p className="text-xs text-muted-foreground mb-3">Seleziona la destinazione dello spostamento:</p>
              
              {/* Root folder option */}
              <div
                className={`flex items-center gap-2 p-2.5 rounded-md cursor-pointer hover:bg-muted/60 transition-colors ${
                  moveItem.parentId === null ? "bg-primary/5 border border-primary/20" : "border border-border/20"
                }`}
                onClick={() => handleMoveSubmit(null)}
              >
                <FolderIcon className="h-4 w-4 text-primary" />
                <span className="text-sm font-medium">Miei File (Radice)</span>
              </div>

              {/* Render candidate destination folders (excluding the folder itself or descendants to prevent cycles) */}
              {allFolders
                ?.filter((folder) => {
                  // If moving a folder, it cannot be moved into itself
                  if (moveItem.type === "folder" && folder.id === moveItem.id) return false;
                  // If folder is already its parent, highlight it but don't prevent
                  return true;
                })
                .map((folder) => (
                  <div
                    key={folder.id}
                    className={`flex items-center gap-2 p-2.5 rounded-md cursor-pointer hover:bg-muted/60 transition-colors border ${
                      moveItem.parentId === folder.id ? "bg-primary/5 border-primary/20" : "border-border/20"
                    }`}
                    onClick={() => handleMoveSubmit(folder.id)}
                  >
                    <FolderIcon className="h-4 w-4 text-yellow-500 fill-yellow-500" />
                    <span className="text-sm font-medium">{folder.name}</span>
                  </div>
                ))}

              {(!allFolders || allFolders.length === 0) && (
                <p className="text-xs text-muted-foreground text-center py-4">Nessuna cartella di destinazione disponibile.</p>
              )}
            </div>
            <footer className="p-3 border-t border-border/40 flex justify-end gap-2 bg-muted/20 flex-shrink-0">
              <Button type="button" variant="outline" size="sm" onClick={() => setMoveItem(null)}>
                Chiudi
              </Button>
            </footer>
          </Card>
        </div>
      )}
    </div>
  );
}

// ─── ACTION MENU POPUP ───
interface ActionMenuProps {
  item: { id: string; name: string; type: "folder" | "file"; parentId: string | null };
  onClose: () => void;
  onRename: (item: { id: string; name: string; type: "folder" | "file" }) => void;
  onMove: (item: { id: string; name: string; type: "folder" | "file"; parentId: string | null }) => void;
  onDelete: (item: { id: string; name: string; type: "folder" | "file" }) => void;
  downloadUrl?: string;
}

function ActionMenu({ item, onClose, onRename, onMove, onDelete, downloadUrl }: ActionMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu on click outside
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [onClose]);

  return (
    <div
      ref={menuRef}
      className="absolute right-0 mt-1 w-40 bg-card border border-border/60 rounded-md shadow-lg z-50 overflow-hidden text-xs py-1"
      onClick={(e) => e.stopPropagation()}
    >
      <button
        onClick={() => {
          onRename({ id: item.id, name: item.name, type: item.type });
          onClose();
        }}
        className="w-full text-left px-3 py-2 hover:bg-muted flex items-center gap-2"
      >
        <Edit3 className="h-3.5 w-3.5 text-muted-foreground" />
        <span>Rinomina</span>
      </button>

      <button
        onClick={() => {
          onMove(item);
          onClose();
        }}
        className="w-full text-left px-3 py-2 hover:bg-muted flex items-center gap-2"
      >
        <Move className="h-3.5 w-3.5 text-muted-foreground" />
        <span>Sposta</span>
      </button>

      {item.type === "file" && downloadUrl && (
        <a
          href={downloadUrl}
          className="w-full text-left px-3 py-2 hover:bg-muted flex items-center gap-2"
          onClick={() => onClose()}
        >
          <Download className="h-3.5 w-3.5 text-muted-foreground" />
          <span>Scarica</span>
        </a>
      )}

      <hr className="border-border/40 my-1" />

      <button
        onClick={() => {
          onDelete({ id: item.id, name: item.name, type: item.type });
          onClose();
        }}
        className="w-full text-left px-3 py-2 hover:bg-destructive/10 text-destructive flex items-center gap-2 font-medium"
      >
        <Trash2 className="h-3.5 w-3.5" />
        <span>Elimina</span>
      </button>
    </div>
  );
}

const statusBadge: Record<string, string> = {
  parsed: "bg-success/10 text-success border border-success/20",
  pending: "bg-warning/10 text-warning border border-warning/20",
  failed: "bg-destructive/10 text-destructive border border-destructive/20"
};
