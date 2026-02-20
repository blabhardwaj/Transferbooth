/* ============================
   DeviceList — shows discovered LAN peers
   ============================ */

import { motion, AnimatePresence } from 'framer-motion';
import { Monitor, Laptop, Apple, Wifi, Lock } from 'lucide-react';
import type { Peer } from '../types';

interface Props {
    devices: Peer[];
    selectedId: string | null;
    onSelect: (peer: Peer) => void;
}

function getPlatformIcon(platform: string) {
    switch (platform) {
        case 'darwin':
            return <Apple />;
        case 'linux':
            return <Monitor />;
        default:
            return <Laptop />;
    }
}

export default function DeviceList({ devices, selectedId, onSelect }: Props) {
    return (
        <div>
            <div className="section-title">
                <Wifi size={12} />
                <span>Devices</span>
                <span className="count">{devices.length}</span>
            </div>

            {devices.length === 0 ? (
                <div className="empty-state">
                    <Wifi size={40} />
                    <p>Looking for devices on your network…</p>
                </div>
            ) : (
                <div className="device-list">
                    <AnimatePresence mode="popLayout">
                        {devices.map((peer) => (
                            <motion.div
                                key={peer.device_id}
                                className={`device-card ${selectedId === peer.device_id ? 'selected' : ''}`}
                                onClick={() => onSelect(peer)}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -20 }}
                                transition={{ duration: 0.25 }}
                                layout
                            >
                                <div className="device-icon">
                                    {getPlatformIcon(peer.platform)}
                                </div>
                                <div className="device-info">
                                    <div className="device-name" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                        {peer.device_name}
                                        {peer.is_trusted && <span title="Trusted Peer"><Lock size={14} color="#10b981" /></span>}
                                    </div>
                                    <div className="device-meta">{peer.ip_address}</div>
                                </div>
                                <div className="online-dot" />
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>
            )}
        </div>
    );
}
