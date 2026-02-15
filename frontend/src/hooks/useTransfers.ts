/* ============================
   useTransfers — manages transfer list from WebSocket events
   ============================ */

import { useState, useEffect } from 'react';
import type { TransferInfo, Notification } from '../types';
import { getTransfers } from '../api/client';

let notifCounter = 0;

export function useTransfers(
    subscribe: (event: string, handler: (data: Record<string, unknown>) => void) => () => void,
) {
    const [transfers, setTransfers] = useState<TransferInfo[]>([]);
    const [pendingRequests, setPendingRequests] = useState<TransferInfo[]>([]);
    const [notifications, setNotifications] = useState<Notification[]>([]);

    // Fetch initial list
    useEffect(() => {
        getTransfers()
            .then(setTransfers)
            .catch((err) => console.error('Failed to fetch transfers:', err));
    }, []);

    // Subscribe to real-time updates
    useEffect(() => {
        const unsub1 = subscribe('transfer_progress', (data) => {
            const info = data as unknown as TransferInfo;
            setTransfers((prev) =>
                prev.map((t) => (t.transfer_id === info.transfer_id ? info : t)),
            );
        });

        const unsub2 = subscribe('transfer_state', (data) => {
            const info = data as unknown as TransferInfo;
            setTransfers((prev) => {
                const exists = prev.find((t) => t.transfer_id === info.transfer_id);
                if (exists) {
                    return prev.map((t) =>
                        t.transfer_id === info.transfer_id ? info : t,
                    );
                }
                return [...prev, info];
            });
        });

        const unsub3 = subscribe('transfer_request', (data) => {
            const info = data as unknown as TransferInfo;
            setPendingRequests((prev) => [...prev, info]);
        });

        const unsub4 = subscribe('notification', (data) => {
            const notif = data as { type: Notification['type']; message: string };
            const notification: Notification = {
                id: `notif-${++notifCounter}`,
                type: notif.type,
                message: notif.message,
                timestamp: Date.now(),
            };
            setNotifications((prev) => [...prev, notification]);

            // Auto-remove after 6 seconds
            setTimeout(() => {
                setNotifications((prev) =>
                    prev.filter((n) => n.id !== notification.id),
                );
            }, 6000);
        });

        return () => {
            unsub1();
            unsub2();
            unsub3();
            unsub4();
        };
    }, [subscribe]);

    const dismissRequest = (transferId: string) => {
        setPendingRequests((prev) =>
            prev.filter((r) => r.transfer_id !== transferId),
        );
    };

    const dismissNotification = (id: string) => {
        setNotifications((prev) => prev.filter((n) => n.id !== id));
    };

    return {
        transfers,
        pendingRequests,
        notifications,
        dismissRequest,
        dismissNotification,
    };
}
