/* ============================
   Transfer Booth — TypeScript types
   ============================ */

// --- Peer / Device ---
export interface Peer {
    device_id: string;
    device_name: string;
    ip_address: string;
    api_port: number;
    platform: 'windows' | 'darwin' | 'linux';
    last_seen: number;
}

// --- Transfer ---
export type TransferState =
    | 'pending'
    | 'awaiting_acceptance'
    | 'rejected'
    | 'connecting'
    | 'transferring'
    | 'paused'
    | 'completed'
    | 'failed'
    | 'cancelled';

export type TransferDirection = 'sending' | 'receiving';

export interface TransferInfo {
    transfer_id: string;
    file_name: string;
    file_size: number;
    transferred_bytes: number;
    state: TransferState;
    direction: TransferDirection;
    peer_device_id: string;
    peer_device_name: string;
    speed_bps: number;
    progress_percent: number;
    eta_seconds: number;
    error_message: string | null;
}

// --- WebSocket events ---
export type WSEventType =
    | 'peer_discovered'
    | 'peer_lost'
    | 'transfer_request'
    | 'transfer_progress'
    | 'transfer_state'
    | 'notification';

export interface WSMessage {
    event: WSEventType;
    data: Record<string, unknown>;
}

export interface Notification {
    id: string;
    type: 'success' | 'error' | 'warning' | 'info';
    message: string;
    timestamp: number;
}

// --- Settings ---
export interface Settings {
    device_name: string;
    save_dir: string;
}
