export type SessionMode = "LIVE" | "PREPARED_REPLAY";
export type IncidentWorkflow = "OPEN" | "ACKNOWLEDGED" | "RESOLVED";
export type IncidentVerdict = "UNREVIEWED" | "CONFIRMED_ANOMALY" | "FALSE_ALARM";
export const INCIDENT_ACTIONS = [
  "ACKNOWLEDGE", "RESOLVE", "SET_VERDICT", "ADD_NOTE", "APPROVE_PLAYBOOK", "ESCALATE",
] as const;
export type IncidentAction = (typeof INCIDENT_ACTIONS)[number];

export type IncidentCommand =
  | { incident_id: string; action: "ACKNOWLEDGE" | "RESOLVE" | "APPROVE_PLAYBOOK" | "ESCALATE" }
  | { incident_id: string; action: "SET_VERDICT"; details: { verdict: Exclude<IncidentVerdict, "UNREVIEWED">; note?: string } }
  | { incident_id: string; action: "ADD_NOTE"; details: { note: string } };

export interface OperationalIncident {
  incident_id: string;
  category: "SURVEILLANCE" | "SENSOR_HEALTH";
  event_type: string;
  physical_zone_id: string | null;
  affected_camera_id: string | null;
  workflow_state: IncidentWorkflow;
  verdict: IncidentVerdict;
  severity: "CRITICAL" | "WARNING" | "INFO";
  is_surveillance_anomaly: boolean;
  confidence: number | null;
  facts: string[];
  created_at: number;
}

export interface OperationalState {
  active_session: {
    session_id: string;
    mode: SessionMode;
    policy_version_id: string;
    failure_reason: string | null;
    started_at: number;
  } | null;
  active_policy: {
    policy_version_id: string;
    profile_name: string;
    checksum: string;
  } | null;
  camera_health: Array<{
    camera_id: string;
    physical_zone_id: string | null;
    state: "CONNECTING" | "ONLINE" | "DEGRADED" | "OFFLINE";
    reason: string | null;
    recorded_at: number;
  }>;
  measurements: Array<{
    camera_id: string | null;
    inference_fps: number | null;
    dropped_frames: number | null;
    cpu_percent: number | null;
    ram_percent: number | null;
    network_kbps: number | null;
    alert_latency_ms: number | null;
  }>;
  incidents: OperationalIncident[];
  search_level: "METADATA" | "DETERMINISTIC_LEXICAL" | "SEMANTIC_TEXT" | "VLM_ENRICHED";
}
