// Mirrors aura_mas/core/bus.py dataclasses exactly — keep in sync with that
// file's field names/types, they are the real over-the-wire JSON shape.

export type Severity = "CRITICAL" | "WARNING" | "INFO";
export type AlertStatus = "OPEN" | "ACKNOWLEDGED" | "DISMISSED";

export interface Alert {
  alert_id: string;
  timestamp: number;
  scene_time_seconds?: number | null;
  severity: Severity;
  event_type: string;
  contributing_types?: string[];
  confidence: number;
  zone: string | null;
  sensors: string[];
  evidence: string[];
  fused_events: string[];
  explanation: string | null;
  status: AlertStatus;
  priority_score?: number | null;
  false_positive_risk?: number | null;
  priority_label?: "HIGH" | "MEDIUM" | "LOW" | null;
  priority_model_version?: string | null;
}

export interface AuraEvent {
  event_id: string;
  sensor_id: string;
  timestamp: number;
  scene_time_seconds?: number | null;
  event_type: string;
  confidence: number;
  modality: "video" | "audio";
  zone: string | null;
  track_id: number | null;
  evidence_path: string | null;
  extra: Record<string, unknown>;
}

export interface CoordinationTask {
  task_id: string;
  type: string;
  hypothesis_id: string;
  event_type: string;
  zone: string | null;
  origin_sensor: string;
  timestamp: number;
  scene_time_seconds?: number | null;
}

export interface CoordinationBid {
  task_id: string;
  agent_id: string;
  bid: number;
  timestamp: number;
}

export interface CoordinationAward {
  task_id: string;
  winner: string;
  timestamp: number;
}

export interface CoordinationVerification {
  task_id: string;
  agent_id: string;
  verified: boolean;
  verification_score: number;
  timestamp: number;
}

export interface ScenarioZone {
  name: string;
  type: string;
  polygon: number[][];
  max_occupancy?: number;
  flow_direction?: number[];
  down_aspect_ratio?: number;
  max_speed_zone_lengths_per_second?: number;
}

export interface ScenarioSensor {
  type: "camera" | "audio";
  id: string;
  source: string;
  zones?: ScenarioZone[];
  zone?: string;
  detection_conf?: number;
  loiter_seconds?: number;
  min_flow_px?: number;
  person_down_seconds?: number;
  rapid_window_seconds?: number;
  rapid_min_duration?: number;
}

export interface ScenarioManifest {
  name: string;
  duration_seconds: number;
  dataset?: string;
  split?: string;
  clip_id?: string;
  sensors: ScenarioSensor[];
  ground_truth?: Array<{
    event_type: string;
    zone: string;
    t_start: number;
    t_end: number;
  }>;
  notes?: string;
}

export type PreparedTimelineKind =
  | "event"
  | "task"
  | "bid"
  | "award"
  | "verification"
  | "alert"
  | "context";

export interface ReplayMetadata {
  title: string;
  anomaly_type: string;
  description: string;
  dataset: string;
  attribution: string;
  display_sources?: Record<string, string>;
  anomaly_key?: string;
  sample_id?: string;
  sample_label?: string;
  site_context?: string;
  tags?: string[];
  camera_count?: number;
  has_context?: boolean;
  detected_event_types?: string[];
}

export interface PreparedTimelineItem {
  kind: PreparedTimelineKind;
  scene_time_seconds: number | null;
  wall_offset_seconds: number;
  payload: Record<string, unknown>;
}

export interface PreparedReplay {
  schema_version: 1 | 2;
  scenario: string;
  mode: string;
  duration_seconds: number;
  source_run: string;
  metadata: ReplayMetadata;
  alerts: Alert[];
  timeline: PreparedTimelineItem[];
}

export interface ContextAnnotation {
  context_id: string;
  scenario: string;
  summary: string;
  object_labels: string[];
  safety_observations: string[];
  source: "deterministic" | "vlm";
  status: "generated" | "unavailable" | "failed";
  model: string | null;
  provider: string | null;
  source_frame_times: number[];
  generated_at: number;
}

export interface SearchResult {
  document_id: string;
  scenario: string;
  anomaly_key: string;
  title: string;
  summary: string;
  event_type: string | null;
  zone: string | null;
  sensors: string[];
  scene_time_seconds: number;
  evidence_path: string | null;
  context_source: "deterministic" | "vlm" | "alert" | "event";
  score: number;
}

export type CameraConnectionState = "CONNECTING" | "ONLINE" | "DEGRADED" | "OFFLINE";
export interface LiveCameraHealth {
  id: string;
  label: string;
  state: CameraConnectionState;
  last_frame_at: number | null;
  last_error: string | null;
  reconnect_attempts: number;
  stream: string;
}

export interface ReplayCatalogItem extends ReplayMetadata {
  scenario: string;
  mode: string;
  duration_seconds: number;
  replay_available: boolean;
}

/** One in-flight or resolved auction sequence, assembled client-side from
 * the four coordination topics keyed by task_id. */
export interface CoordinationRound {
  task: CoordinationTask;
  bids: CoordinationBid[];
  award: CoordinationAward | null;
  verification: CoordinationVerification | null;
}
