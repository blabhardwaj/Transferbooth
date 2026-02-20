/* ============================
   TransferCard — single file transfer display
   ============================ */

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
    ArrowUp,
    ArrowDown,
    Pause,
    Play,
    X,
    Zap,
    Clock,
    HardDrive,
} from 'lucide-react';
import type { TransferInfo } from '../types';

interface Props {
    transfer: TransferInfo;
    onPause: (id: string) => void;
    onResume: (id: string) => void;
    onCancel: (id: string) => void;
}

function formatSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    const size = bytes / Math.pow(1024, i);
    return `${size.toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
}

function formatSpeed(bps: number): string {
    if (bps === 0) return '—';
    const bits = bps * 8;
    const units = ['bps', 'Kbps', 'Mbps', 'Gbps'];
    const i = Math.floor(Math.log(bits) / Math.log(1024));
    const speed = bits / Math.pow(1024, i);
    return `${speed.toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
}

function formatETA(seconds: number): string {
    if (seconds <= 0) return '—';
    if (seconds < 60) return `${Math.ceil(seconds)}s`;
    if (seconds < 3600) {
        const m = Math.floor(seconds / 60);
        const s = Math.ceil(seconds % 60);
        return `${m}m ${s}s`;
    }
    const h = Math.floor(seconds / 3600);
    const m = Math.ceil((seconds % 3600) / 60);
    return `${h}h ${m}m`;
}

const isActive = (state: string) =>
    ['transferring', 'paused', 'paused_by_peer', 'connecting', 'pending', 'awaiting_acceptance'].includes(state);

export default function TransferCard({
    transfer,
    onPause,
    onResume,
    onCancel,
}: Props) {
    const isSending = transfer.direction === 'sending';
    const showControls = isActive(transfer.state);
    const showProgress = transfer.state !== 'pending' && transfer.state !== 'awaiting_acceptance';
    const [showCancelConfirm, setShowCancelConfirm] = useState(false);

    return (
        <motion.div
            className="transfer-card"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            layout
            transition={{ duration: 0.25 }}
        >
            {/* Header */}
            <div className="transfer-header">
                <div
                    className={`transfer-direction-icon ${isSending ? 'sending' : 'receiving'}`}
                >
                    {isSending ? <ArrowUp /> : <ArrowDown />}
                </div>

                <div className="transfer-file-info">
                    <div className="transfer-file-name" title={transfer.file_name}>
                        {transfer.file_name}
                    </div>
                    <div className="transfer-peer">
                        {isSending ? 'To' : 'From'} {transfer.peer_device_name} ·{' '}
                        {formatSize(transfer.file_size)}
                    </div>
                </div>

                <div className="transfer-controls">
                    {showControls && !showCancelConfirm && (
                        <>
                            {transfer.state === 'transferring' && (
                                <button
                                    className="btn btn-ghost btn-icon"
                                    onClick={() => onPause(transfer.transfer_id)}
                                    title="Pause"
                                >
                                    <Pause size={14} />
                                </button>
                            )}
                            {transfer.state === 'paused' && (
                                <button
                                    className="btn btn-ghost btn-icon"
                                    onClick={() => onResume(transfer.transfer_id)}
                                    title="Resume"
                                >
                                    <Play size={14} />
                                </button>
                            )}
                            {/* Do not show Resume if state is paused_by_peer */}
                            <button
                                className="btn btn-ghost btn-icon"
                                onClick={() => setShowCancelConfirm(true)}
                                title="Cancel"
                            >
                                <X size={14} />
                            </button>
                        </>
                    )}
                    {!showCancelConfirm && (
                        <span className={`state-badge ${transfer.state}`}>
                            {transfer.state.replace(/_/g, ' ')}
                        </span>
                    )}
                </div>
            </div>

            {/* Cancel Confirmation Dialog Overlay or In-Place Render */}
            {showCancelConfirm ? (
                <div className="cancel-confirm" style={{ padding: '0.5rem', textAlign: 'center', background: 'rgba(0,0,0,0.05)', borderRadius: '6px', margin: '0.5rem' }}>
                    <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.9rem' }}>Are you sure you want to cancel?</p>
                    <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
                        <button
                            className="btn btn-ghost"
                            style={{ flex: 1, padding: '0.25rem' }}
                            onClick={() => setShowCancelConfirm(false)}
                        >
                            No
                        </button>
                        <button
                            className="btn btn-danger"
                            style={{ flex: 1, padding: '0.25rem', background: '#e11d48', color: 'white' }}
                            onClick={() => {
                                setShowCancelConfirm(false);
                                onCancel(transfer.transfer_id);
                            }}
                        >
                            Yes
                        </button>
                    </div>
                </div>
            ) : (
                <>
                    {/* Progress Bar */}
                    {showProgress && (
                        <div className="progress-container">
                            <div className="progress-bar">
                                <div
                                    className="progress-fill"
                                    style={{ width: `${Math.min(transfer.progress_percent, 100)}%` }}
                                />
                            </div>
                            <div className="progress-label">
                                <span>{transfer.progress_percent.toFixed(1)}%</span>
                                <span>
                                    {formatSize(transfer.transferred_bytes)} / {formatSize(transfer.file_size)}
                                </span>
                            </div>
                        </div>
                    )}

                    {/* Stats */}
                    {(transfer.state === 'transferring' || transfer.state === 'paused' || transfer.state === 'paused_by_peer') && (
                        <div className="transfer-stats">
                            <div className="transfer-stat">
                                <Zap size={12} />
                                <span>{formatSpeed(transfer.speed_bps)}</span>
                            </div>
                            <div className="transfer-stat">
                                <Clock size={12} />
                                <span>{formatETA(transfer.eta_seconds)}</span>
                            </div>
                            <div className="transfer-stat">
                                <HardDrive size={12} />
                                <span>{formatSize(transfer.transferred_bytes)}</span>
                            </div>
                        </div>
                    )}
                </>
            )}
        </motion.div>
    );
}
