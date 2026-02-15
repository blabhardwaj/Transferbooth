/* ============================
   FileSelector — multi-file picker + drag-and-drop
   ============================ */

import { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, X, File, Send } from 'lucide-react';
import type { Peer } from '../types';

interface Props {
    peer: Peer;
    onSend: (peer: Peer, filePaths: string[]) => void;
    onClose: () => void;
}

function formatSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    const size = bytes / Math.pow(1024, i);
    return `${size.toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
}

interface SelectedFile {
    name: string;
    size: number;
    path: string;
}

export default function FileSelector({ peer, onSend, onClose }: Props) {
    const [files, setFiles] = useState<SelectedFile[]>([]);
    const [dragging, setDragging] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    const handleFileSelect = useCallback(
        (e: React.ChangeEvent<HTMLInputElement>) => {
            const fileList = e.target.files;
            if (!fileList) return;

            const newFiles: SelectedFile[] = [];
            for (let i = 0; i < fileList.length; i++) {
                const f = fileList[i]!;
                newFiles.push({
                    name: f.name,
                    size: f.size,
                    // In a desktop app we'd get the full path.
                    // For the web UI, we store the name and the backend handles path resolution.
                    path: (f as unknown as { path?: string }).path ?? f.name,
                });
            }
            setFiles((prev) => [...prev, ...newFiles]);
        },
        [],
    );

    const removeFile = (index: number) => {
        setFiles((prev) => prev.filter((_, i) => i !== index));
    };

    const handleSend = () => {
        if (files.length === 0) return;
        onSend(
            peer,
            files.map((f) => f.path),
        );
        onClose();
    };

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        setDragging(true);
    };

    const handleDragLeave = () => {
        setDragging(false);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setDragging(false);
        const droppedFiles = e.dataTransfer.files;
        if (!droppedFiles) return;

        const newFiles: SelectedFile[] = [];
        for (let i = 0; i < droppedFiles.length; i++) {
            const f = droppedFiles[i]!;
            newFiles.push({
                name: f.name,
                size: f.size,
                path: (f as unknown as { path?: string }).path ?? f.name,
            });
        }
        setFiles((prev) => [...prev, ...newFiles]);
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

                <div
                    className={`drop-zone ${dragging ? 'dragging' : ''}`}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    onClick={() => inputRef.current?.click()}
                >
                    <Upload size={32} />
                    <p>
                        Drop files here or{' '}
                        <span className="browse-text">browse</span>
                    </p>
                </div>

                <input
                    ref={inputRef}
                    type="file"
                    multiple
                    style={{ display: 'none' }}
                    onChange={handleFileSelect}
                />

                {files.length > 0 && (
                    <div className="selected-files">
                        <AnimatePresence>
                            {files.map((f, i) => (
                                <motion.div
                                    key={`${f.name}-${i}`}
                                    className="selected-file"
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: 'auto' }}
                                    exit={{ opacity: 0, height: 0 }}
                                >
                                    <File size={14} />
                                    <span className="file-name">{f.name}</span>
                                    <span className="file-size">{formatSize(f.size)}</span>
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
                )}

                <div className="file-selector-actions">
                    <button className="btn btn-secondary" onClick={onClose}>
                        Cancel
                    </button>
                    <button
                        className="btn btn-primary"
                        onClick={handleSend}
                        disabled={files.length === 0}
                    >
                        <Send size={14} />
                        Send {files.length > 0 ? `(${files.length})` : ''}
                    </button>
                </div>
            </motion.div>
        </motion.div>
    );
}
