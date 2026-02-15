/* ============================
   useDevices — manages peer list from WebSocket events
   ============================ */

import { useState, useEffect } from 'react';
import type { Peer } from '../types';
import { getDevices } from '../api/client';

export function useDevices(
    subscribe: (event: string, handler: (data: Record<string, unknown>) => void) => () => void,
) {
    const [devices, setDevices] = useState<Peer[]>([]);

    // Fetch initial list
    useEffect(() => {
        getDevices()
            .then(setDevices)
            .catch((err) => console.error('Failed to fetch devices:', err));
    }, []);

    // Subscribe to real-time updates
    useEffect(() => {
        const unsub1 = subscribe('peer_discovered', (data) => {
            const peer = data as unknown as Peer;
            setDevices((prev) => {
                const exists = prev.find((p) => p.device_id === peer.device_id);
                if (exists) {
                    return prev.map((p) =>
                        p.device_id === peer.device_id ? peer : p,
                    );
                }
                return [...prev, peer];
            });
        });

        const unsub2 = subscribe('peer_lost', (data) => {
            const peerId = (data as { device_id: string }).device_id;
            setDevices((prev) => prev.filter((p) => p.device_id !== peerId));
        });

        return () => {
            unsub1();
            unsub2();
        };
    }, [subscribe]);

    return devices;
}
