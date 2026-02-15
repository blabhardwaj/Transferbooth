/* ============================
   App — Root component
   ============================ */

import { useState, useCallback } from 'react';
import { AnimatePresence } from 'framer-motion';
import { Settings as SettingsIcon, ArrowUpDown } from 'lucide-react';

import { useWebSocket } from './api/websocket';
import { createTransfer, pauseTransfer, resumeTransfer, cancelTransfer } from './api/client';
import { useDevices } from './hooks/useDevices';
import { useTransfers } from './hooks/useTransfers';

import DeviceList from './components/DeviceList';
import FileSelector from './components/FileSelector';
import TransferQueue from './components/TransferQueue';
import { Toasts, AcceptDialog } from './components/Notifications';
import Settings from './components/Settings';

import type { Peer } from './types';

function App() {
    const { connected, subscribe } = useWebSocket();
    const devices = useDevices(subscribe);
    const {
        transfers,
        pendingRequests,
        notifications,
        dismissRequest,
        dismissNotification,
    } = useTransfers(subscribe);

    const [selectedPeer, setSelectedPeer] = useState<Peer | null>(null);
    const [showFileSelector, setShowFileSelector] = useState(false);
    const [showSettings, setShowSettings] = useState(false);

    const handleDeviceSelect = useCallback((peer: Peer) => {
        setSelectedPeer(peer);
        setShowFileSelector(true);
    }, []);

    const handleSendFiles = useCallback(
        async (peer: Peer, filePaths: string[]) => {
            try {
                await createTransfer(peer.device_id, filePaths);
            } catch (err) {
                console.error('Failed to create transfer:', err);
            }
        },
        [],
    );

    const handlePause = useCallback(async (id: string) => {
        try {
            await pauseTransfer(id);
        } catch (err) {
            console.error('Failed to pause:', err);
        }
    }, []);

    const handleResume = useCallback(async (id: string) => {
        try {
            await resumeTransfer(id);
        } catch (err) {
            console.error('Failed to resume:', err);
        }
    }, []);

    const handleCancel = useCallback(async (id: string) => {
        try {
            await cancelTransfer(id);
        } catch (err) {
            console.error('Failed to cancel:', err);
        }
    }, []);

    const currentRequest = pendingRequests[0];

    return (
        <div className="app">
            {/* Sidebar */}
            <aside className="sidebar">
                <div className="sidebar-header">
                    <h1>Transfer Booth</h1>
                    <div className="subtitle">Fast, secure LAN file transfer</div>
                    <div className="connection-status">
                        <span className={`status-dot ${connected ? 'connected' : ''}`} />
                        <span>{connected ? 'Connected' : 'Connecting…'}</span>
                    </div>
                </div>

                <div className="sidebar-content">
                    {showSettings ? (
                        <Settings onClose={() => setShowSettings(false)} />
                    ) : (
                        <DeviceList
                            devices={devices}
                            selectedId={selectedPeer?.device_id ?? null}
                            onSelect={handleDeviceSelect}
                        />
                    )}
                </div>

                <div className="sidebar-footer">
                    <button
                        className="settings-btn"
                        onClick={() => setShowSettings(!showSettings)}
                    >
                        <SettingsIcon size={16} />
                        <span>{showSettings ? 'Back to Devices' : 'Settings'}</span>
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <main className="main-content">
                <div className="main-header">
                    <h2>
                        <ArrowUpDown
                            size={16}
                            style={{ marginRight: 8, verticalAlign: 'middle', opacity: 0.5 }}
                        />
                        Transfers
                    </h2>
                </div>

                <div className="main-body">
                    <TransferQueue
                        transfers={transfers}
                        onPause={handlePause}
                        onResume={handleResume}
                        onCancel={handleCancel}
                    />
                </div>
            </main>

            {/* Modals */}
            <AnimatePresence>
                {showFileSelector && selectedPeer && (
                    <FileSelector
                        peer={selectedPeer}
                        onSend={handleSendFiles}
                        onClose={() => setShowFileSelector(false)}
                    />
                )}
            </AnimatePresence>

            <AnimatePresence>
                {currentRequest && (
                    <AcceptDialog
                        request={currentRequest}
                        onRespond={dismissRequest}
                    />
                )}
            </AnimatePresence>

            {/* Toasts */}
            <Toasts
                notifications={notifications}
                onDismiss={dismissNotification}
            />
        </div>
    );
}

export default App;
