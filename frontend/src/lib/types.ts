// Mirrors aura_mas/core/bus.py dataclasses exactly — keep in sync with that
// file's field names/types, they are the real over-the-wire JSON shape.

export type Severity = "CRITICAL" | "WARNING" | "INFO";
export type AlertStatus = "OPEN" | "ACKNOWLEDGED" | "DISMISSED";

export interface Alert {
  alert_id: string;
  timestamp: number;
  severity: Severity;
  event_type: string;
  confidence: number;
  zone: string | null;
  sensors: string[];
  evidence: string[];
  fused_events: string[];
  explanation: string | null;
  status: AlertStatus;
}

export interface AuraEvent {
  event_id: string;
  sensor_id: string;
  timestamp: number;
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
}

export interface ScenarioSensor {
  type: "camera" | "audio";
  id: string;
  source: string;
  zones?: ScenarioZone[];
  zone?: string;
}

export interface ScenarioManifest {
  name: string;
  duration_seconds: number;
  sensors: ScenarioSensor[];
  ground_truth?: Array<{
    event_type: string;
    zone: string;
    t_start: number;
    t_end: number;
  }>;
  notes?: string;
}

/** One in-flight or resolved auction sequence, assembled client-side from
 * the four coordination topics keyed by task_id. */
export interface CoordinationRound {
  task: CoordinationTask;
  bids: CoordinationBid[];
  award: CoordinationAward | null;
  verification: CoordinationVerification | null;
}
