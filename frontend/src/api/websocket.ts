/* ============================
   WebSocket connection manager
   ============================ */

import { useEffect, useRef, useCallback, useState } from 'react';
import type { WSMessage } from '../types';

type EventHandler = (data: Record<string, unknown>) => void;

/**
 * Custom hook for WebSocket connection with auto-reconnect.
 */
export function useWebSocket() {
    const wsRef = useRef<WebSocket | null>(null);
    const handlersRef = useRef<Map<string, Set<EventHandler>>>(new Map());
    const [connected, setConnected] = useState(false);
    const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

        ws.onopen = () => {
            setConnected(true);
            console.log('[WS] Connected');
        };

        ws.onmessage = (evt) => {
            try {
                const msg: WSMessage = JSON.parse(evt.data);
                const eventHandlers = handlersRef.current.get(msg.event);
                if (eventHandlers) {
                    eventHandlers.forEach((handler) => handler(msg.data));
                }
            } catch (e) {
                console.warn('[WS] Failed to parse message', e);
            }
        };

        ws.onclose = () => {
            setConnected(false);
            console.log('[WS] Disconnected — reconnecting in 2s');
            reconnectTimer.current = setTimeout(connect, 2000);
        };

        ws.onerror = () => {
            ws.close();
        };

        wsRef.current = ws;
    }, []);

    useEffect(() => {
        connect();
        return () => {
            clearTimeout(reconnectTimer.current);
            wsRef.current?.close();
        };
    }, [connect]);

    const subscribe = useCallback(
        (event: string, handler: EventHandler) => {
            if (!handlersRef.current.has(event)) {
                handlersRef.current.set(event, new Set());
            }
            handlersRef.current.get(event)!.add(handler);

            // Return unsubscribe function
            return () => {
                handlersRef.current.get(event)?.delete(handler);
            };
        },
        [],
    );

    return { connected, subscribe };
}
