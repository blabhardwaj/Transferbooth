import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, File as FileIcon, Send, FolderOpen } from 'lucide-react';
import type { Peer } from '../types';
import { selectFiles } from '../api/client';

interface Props {
    peer: Peer;
    onSend: (peer: Peer, filePaths: string[]) => void;
    onClose: () => void;
}

export default function FileSelector({ peer, onSend, onClose }: Props) {
    const [filePaths, setFilePaths] = useState<string[]>([]);
    const [isLoading, setIsLoading] = useState(false);

    const handleBrowse = async () => {
        setIsLoading(true);
        try {
            const paths = await selectFiles();
            setFilePaths((prev) => [...prev, ...paths]);
        } catch (err) {
            console.error('Failed to select files:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const removeFile = (index: number) => {
        setFilePaths((prev) => prev.filter((_, i) => i !== index));
    };

    const handleSend = () => {
        if (filePaths.length === 0) return;
        onSend(peer, filePaths);
        setFilePaths([]); // Clear functionality
        onClose();
    };

    const getFileName = (path: string) => {
        // Handle both Windows and Unix paths
        return path.split(/[/\\]/).pop() || path;
    };

    return (
        <motion.div
            className="file-selector-overlay"
            onClick={onClose}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
        >
            <motion.div
                className="file-selector"
                onClick={(e) => e.stopPropagation()}
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.95, opacity: 0 }}
                transition={{ duration: 0.2 }}
            >
                <h3>Send files to {peer.device_name}</h3>

                <div className="file-selector-content">
                    {filePaths.length === 0 ? (
                        <div className="empty-state" onClick={handleBrowse}>
                            <div className="icon-circle">
                                <FolderOpen size={32} />
                            </div>
                            <p>Click to select files from your computer</p>
                            <button className="btn btn-secondary" disabled={isLoading}>
                                {isLoading ? 'Opening...' : 'Browse Files'}
                            </button>
                        </div>
                    ) : (
                        <div className="selected-files-list">
                            <div className="list-header">
                                <span>Selected Files ({filePaths.length})</span>
                                <button className="btn btn-ghost btn-sm" onClick={handleBrowse}>
                                    + Add More
                                </button>
                            </div>
                            <div className="files-scroll-area">
                                <AnimatePresence>
                                    {filePaths.map((path, i) => (
                                        <motion.div
                                            key={`${path}-${i}`}
                                            className="selected-file-row"
                                            initial={{ opacity: 0, x: -10 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            exit={{ opacity: 0, height: 0 }}
                                        >
                                            <FileIcon size={16} className="file-icon" />
                                            <span className="file-path" title={path}>
                                                {getFileName(path)}
                                                <span className="full-path">{path}</span>
                                            </span>
                                            <button
                                                className="remove-btn"
                                                onClick={() => removeFile(i)}
                                            >
                                                <X size={14} />
                                            </button>
                                        </motion.div>
                                    ))}
                                </AnimatePresence>
                            </div>
                        </div>
                    )}
                </div>

                <div className="file-selector-actions">
                    <button className="btn btn-secondary" onClick={onClose}>
                        Cancel
                    </button>
                    <button
                        className="btn btn-primary"
                        onClick={handleSend}
                        disabled={filePaths.length === 0}
                    >
                        <Send size={14} />
                        Send {filePaths.length > 0 ? `(${filePaths.length})` : ''}
                    </button>
                </div>
            </motion.div>
        </motion.div>
    );
}

