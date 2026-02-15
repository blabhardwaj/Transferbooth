/* ============================
   TransferQueue — list of all transfers
   ============================ */

import { AnimatePresence } from 'framer-motion';
import { ArrowUpDown } from 'lucide-react';
import type { TransferInfo } from '../types';
import TransferCard from './TransferCard';

interface Props {
    transfers: TransferInfo[];
    onPause: (id: string) => void;
    onResume: (id: string) => void;
    onCancel: (id: string) => void;
}

export default function TransferQueue({
    transfers,
    onPause,
    onResume,
    onCancel,
}: Props) {
    const active = transfers.filter((t) =>
        ['pending', 'connecting', 'transferring', 'paused', 'awaiting_acceptance'].includes(t.state),
    );
    const completed = transfers.filter((t) =>
        ['completed', 'failed', 'cancelled', 'rejected'].includes(t.state),
    );

    if (transfers.length === 0) {
        return (
            <div className="empty-state" style={{ paddingTop: '120px' }}>
                <ArrowUpDown size={48} />
                <p>No transfers yet. Select a device and send some files!</p>
            </div>
        );
    }

    return (
        <div>
            {active.length > 0 && (
                <>
                    <div className="section-title">
                        <span>Active Transfers</span>
                        <span className="count">{active.length}</span>
                    </div>
                    <div className="transfer-list">
                        <AnimatePresence mode="popLayout">
                            {active.map((t) => (
                                <TransferCard
                                    key={t.transfer_id}
                                    transfer={t}
                                    onPause={onPause}
                                    onResume={onResume}
                                    onCancel={onCancel}
                                />
                            ))}
                        </AnimatePresence>
                    </div>
                </>
            )}

            {completed.length > 0 && (
                <>
                    <div
                        className="section-title"
                        style={{ marginTop: active.length > 0 ? '24px' : 0 }}
                    >
                        <span>History</span>
                        <span className="count">{completed.length}</span>
                    </div>
                    <div className="transfer-list">
                        <AnimatePresence mode="popLayout">
                            {completed.map((t) => (
                                <TransferCard
                                    key={t.transfer_id}
                                    transfer={t}
                                    onPause={onPause}
                                    onResume={onResume}
                                    onCancel={onCancel}
                                />
                            ))}
                        </AnimatePresence>
                    </div>
                </>
            )}
        </div>
    );
}
