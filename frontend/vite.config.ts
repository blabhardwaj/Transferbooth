import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Instance 1 config — proxies to backend on port 8765
export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
        proxy: {
            '/api': {
                target: 'http://localhost:8765',
                changeOrigin: true,
            },
            '/ws': {
                target: 'ws://localhost:8765',
                ws: true,
            },
        },
    },
});
