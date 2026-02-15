/* ============================
   Notifications — toasts + acceptance dialog
   ============================ */

import { motion, AnimatePresence } from 'framer-motion';
import {
    CheckCircle,
    XCircle,
    AlertTriangle,
    Info,
    X,
    Download,
} from 'lucide-react';
import type { Notification, TransferInfo } from '../types';
import { acceptTransfer, rejectTransfer } from '../api/client';

// --- Toasts ---

interface ToastProps {
    notifications: Notification[];
    onDismiss: (id: string) => void;
}

function getToastIcon(type: Notification['type']) {
    switch (type) {
        case 'success':
            return <CheckCircle className="toast-icon" />;
        case 'error':
            return <XCircle className="toast-icon" />;
        case 'warning':
            return <AlertTriangle className="toast-icon" />;
        case 'info':
            return <Info className="toast-icon" />;
    }
}

export function Toasts({ notifications, onDismiss }: ToastProps) {
    return (
        <div className="toast-container">
            <AnimatePresence>
                {notifications.map((n) => (
                    <motion.div
                        key={n.id}
                        className={`toast ${n.type}`}
                        initial={{ opacity: 0, x: 60, scale: 0.95 }}
                        animate={{ opacity: 1, x: 0, scale: 1 }}
                        exit={{ opacity: 0, x: 60, scale: 0.95 }}
                        transition={{ duration: 0.25 }}
                    >
                        {getToastIcon(n.type)}
                        <span className="toast-message">{n.message}</span>
                        <button
                            className="toast-close"
                            onClick={() => onDismiss(n.id)}
                        >
                            <X size={14} />
                        </button>
                    </motion.div>
                ))}
            </AnimatePresence>
        </div>
    );
}

// --- Acceptance Dialog ---

interface AcceptDialogProps {
    request: TransferInfo;
    onRespond: (transferId: string) => void;
}

function formatSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    const size = bytes / Math.pow(1024, i);
    return `${size.toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
}

export function AcceptDialog({ request, onRespond }: AcceptDialogProps) {
    const handleAccept = async () => {
        await acceptTransfer(request.transfer_id);
        onRespond(request.transfer_id);
    };

    const handleReject = async () => {
        await rejectTransfer(request.transfer_id);
        onRespond(request.transfer_id);
    };

    return (
        <motion.div
            className="accept-dialog-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
        >
            <motion.div
                className="accept-dialog"
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                transition={{ duration: 0.2 }}
            >
                <div className="dialog-icon">
                    <Download size={24} />
                </div>
                <h3>Incoming File</h3>
                <div className="file-detail">
                    <strong>{request.file_name}</strong>
                    <br />
                    {formatSize(request.file_size)} from{' '}
                    <strong>{request.peer_device_name}</strong>
                </div>
                <div className="dialog-actions">
                    <button className="btn btn-danger" onClick={handleReject}>
                        Reject
                    </button>
                    <button className="btn btn-primary" onClick={handleAccept}>
                        Accept
                    </button>
                </div>
            </motion.div>
        </motion.div>
    );
}
