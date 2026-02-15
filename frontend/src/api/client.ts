/* ============================
   REST API client
   ============================ */

import type { Peer, TransferInfo, Settings } from '../types';

const BASE = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
    const res = await fetch(`${BASE}${url}`, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? 'Request failed');
    }
    return res.json() as Promise<T>;
}

// --- Devices ---
export async function getDevices(): Promise<Peer[]> {
    const data = await request<{ devices: Peer[] }>('/devices');
    return data.devices;
}

// --- Transfers ---
export async function getTransfers(): Promise<TransferInfo[]> {
    const data = await request<{ transfers: TransferInfo[] }>('/transfers');
    return data.transfers;
}

export async function createTransfer(
    peerId: string,
    filePaths: string[],
): Promise<TransferInfo[]> {
    const data = await request<{ transfers: TransferInfo[] }>('/transfers', {
        method: 'POST',
        body: JSON.stringify({ peer_id: peerId, file_paths: filePaths }),
    });
    return data.transfers;
}

export async function pauseTransfer(id: string): Promise<void> {
    await request(`/transfers/${id}/pause`, { method: 'POST' });
}

export async function resumeTransfer(id: string): Promise<void> {
    await request(`/transfers/${id}/resume`, { method: 'POST' });
}

export async function cancelTransfer(id: string): Promise<void> {
    await request(`/transfers/${id}/cancel`, { method: 'POST' });
}

export async function acceptTransfer(id: string): Promise<void> {
    await request(`/transfers/${id}/accept`, { method: 'POST' });
}

export async function rejectTransfer(id: string): Promise<void> {
    await request(`/transfers/${id}/reject`, { method: 'POST' });
}

// --- Settings ---
export async function getSettings(): Promise<Settings> {
    return request<Settings>('/settings');
}

export async function updateSettings(
    settings: Partial<Settings>,
): Promise<void> {
    await request('/settings', {
        method: 'PUT',
        body: JSON.stringify(settings),
    });
}
