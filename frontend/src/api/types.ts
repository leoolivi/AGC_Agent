/** Backend API types — mirrors Python Pydantic models */

export interface InboxItem {
  id: string;
  event_type: string;
  agent_analysis: string;
  urgency: "immediate" | "today" | "this_week" | "low";
  suggested_actions: SuggestedAction[];
  status: string;
  chosen_action_id: string | null;
  created_at: string | null;
  expires_at: string | null;
}

export interface SuggestedAction {
  id: string;
  label: string;
  workflow_id?: string | null;
}

export interface Folder {
  id: string;
  user_id: string;
  name: string;
  parent_id: string | null;
  created_at: string;
}

export interface FolderCreate {
  name: string;
  parent_id: string | null;
}

export interface FolderUpdate {
  name?: string;
  parent_id?: string | null;
}

export interface DocumentItem {
  id: string;
  filename: string;
  content_type: string;
  document_type: string | null;
  parse_status: "pending" | "parsed" | "failed";
  created_at: string | null;
  folder_id: string | null;
}

export interface DocumentDetail extends DocumentItem {
  original_filename: string;
  size_bytes: number | null;
  document_type_confidence: number | null;
  extracted_metadata: Record<string, unknown>;
  tags: string[];
}

export interface Confirmation {
  id: string;
  task_id: string;
  description: string;
  data_for_review: Record<string, unknown>;
  risk_level: string;
  status: string;
  group_id: string | null;
  group_type: string | null;
  created_at: string | null;
}

export interface AuditEntry {
  id: string;
  action_type: string;
  tool_name: string | null;
  input_summary: string | null;
  output_summary: string | null;
  risk_score: number | null;
  status: string | null;
  llm_model: string | null;
  created_at: string | null;
}

export interface UploadResponse {
  id: string;
  filename: string;
  parse_status: string;
}

export interface DriveFile {
  id: string;
  name: string;
  mimeType: string;
  size?: string;
  modifiedTime?: string;
}

export interface MonitoredSource {
  id: string;
  source_type: "drive" | "gmail" | "calendar";
  config: Record<string, any>;
  status: "active" | "error" | "paused";
  last_sync_at: string | null;
  last_sync_count: number;
}
