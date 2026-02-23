import { useState, useEffect } from 'react';
import { Clock, Download, Upload } from 'lucide-react';
import { getHistory } from '../api/client';
import { motion, AnimatePresence } from 'framer-motion';

export default function TransferHistory() {
    const [history, setHistory] = useState<any[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        let mounted = true;
        const fetchHistory = async () => {
            try {
                const data = await getHistory();
                if (mounted) {
                    setHistory(data);
                }
            } catch (err) {
                console.error('Failed to fetch history:', err);
            } finally {
                if (mounted) setIsLoading(false);
            }
        };

        fetchHistory();
        return () => { mounted = false; };
    }, []);

    const formatBytes = (bytes: number) => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return new Intl.DateTimeFormat('en-US', {
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit'
        }).format(date);
    };

    if (isLoading) {
        return (
            <div className="empty-state">
                <Clock size={40} className="spin" />
                <p>Loading history...</p>
            </div>
        );
    }

    if (history.length === 0) {
        return (
            <div className="empty-state">
                <Clock size={40} />
                <p>Your transfer history is empty.</p>
            </div>
        );
    }

    return (
        <div className="transfer-list">
            <AnimatePresence>
                {history.map((record, i) => (
                    <motion.div
                        key={record.id}
                        className="transfer-card"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.05 }}
                    >
                        <div className="transfer-header">
                            <div className={`transfer-direction-icon ${record.direction}`}>
                                {record.direction === 'sending' ? <Upload /> : <Download />}
                            </div>
                            <div className="transfer-file-info">
                                <div className="transfer-file-name">{record.file_name}</div>
                                <div className="transfer-peer">
                                    {record.direction === 'sending' ? 'To: ' : 'From: '} {record.peer_name}
                                </div>
                            </div>
                            <div className={`state-badge ${record.status}`}>
                                {record.status}
                            </div>
                        </div>
                        <div className="transfer-stats">
                            <div className="transfer-stat">
                                <span>{formatBytes(record.file_size)}</span>
                            </div>
                            <div className="transfer-stat" style={{ marginLeft: 'auto' }}>
                                <span>{formatDate(record.timestamp)}</span>
                            </div>
                        </div>
                    </motion.div>
                ))}
            </AnimatePresence>
        </div>
    );
}
