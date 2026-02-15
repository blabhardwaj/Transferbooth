/* ============================
   Settings — device name + save directory
   ============================ */

import { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Save } from 'lucide-react';
import { getSettings, updateSettings } from '../api/client';
import type { Settings as SettingsType } from '../types';

interface Props {
    onClose: () => void;
}

export default function Settings({ onClose }: Props) {
    const [settings, setSettings] = useState<SettingsType>({
        device_name: '',
        save_dir: '',
    });
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        getSettings().then(setSettings).catch(console.error);
    }, []);

    const handleSave = async () => {
        setSaving(true);
        try {
            await updateSettings(settings);
        } catch (err) {
            console.error('Failed to save settings:', err);
        }
        setSaving(false);
        onClose();
    };

    return (
        <div className="settings-panel">
            <div className="section-title">
                <SettingsIcon size={12} />
                <span>Settings</span>
            </div>

            <div className="settings-group">
                <label>Device Name</label>
                <input
                    className="settings-input"
                    value={settings.device_name}
                    onChange={(e) =>
                        setSettings({ ...settings, device_name: e.target.value })
                    }
                    placeholder="My Laptop"
                />
            </div>

            <div className="settings-group">
                <label>Save Directory</label>
                <input
                    className="settings-input"
                    value={settings.save_dir}
                    onChange={(e) =>
                        setSettings({ ...settings, save_dir: e.target.value })
                    }
                    placeholder="C:\Users\...\Downloads"
                />
            </div>

            <div className="file-selector-actions">
                <button className="btn btn-secondary" onClick={onClose}>
                    Cancel
                </button>
                <button
                    className="btn btn-primary"
                    onClick={handleSave}
                    disabled={saving}
                >
                    <Save size={14} />
                    Save
                </button>
            </div>
        </div>
    );
}
