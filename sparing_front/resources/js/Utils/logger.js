/**
 * Production-safe logger utility
 * Only logs in development mode to prevent sensitive data exposure
 */

// Check if debug mode is enabled (explicitly set or in dev mode)
const debugEnabled = import.meta.env.VITE_DEBUG === 'true' ||
    (import.meta.env.DEV && import.meta.env.VITE_DEBUG !== 'false');

/**
 * Logger object with methods that only execute in development mode
 */
const logger = {
    /**
     * Log general information (only in development)
     * @param  {...any} args - Arguments to log
     */
    log(...args) {
        if (debugEnabled) {
            console.log(...args);
        }
    },

    /**
     * Log warnings (only in development)
     * @param  {...any} args - Arguments to log
     */
    warn(...args) {
        if (debugEnabled) {
            console.warn(...args);
        }
    },

    /**
     * Log errors (only in debug mode to hide sensitive info in production)
     * @param  {...any} args - Arguments to log
     */
    error(...args) {
        if (debugEnabled) {
            console.error(...args);
        }
    },

    /**
     * Log debug information (only in development)
     * @param  {...any} args - Arguments to log
     */
    debug(...args) {
        if (debugEnabled) {
            console.debug(...args);
        }
    },

    /**
     * Log information (only in development)
     * @param  {...any} args - Arguments to log
     */
    info(...args) {
        if (debugEnabled) {
            console.info(...args);
        }
    },

    /**
     * Log a group of messages (only in development)
     * @param {string} label - Group label
     */
    group(label) {
        if (debugEnabled) {
            console.group(label);
        }
    },

    /**
     * End a log group (only in development)
     */
    groupEnd() {
        if (debugEnabled) {
            console.groupEnd();
        }
    },

    /**
     * Log a table (only in development)
     * @param {any} data - Data to display as table
     */
    table(data) {
        if (debugEnabled) {
            console.table(data);
        }
    }
};

export default logger;
