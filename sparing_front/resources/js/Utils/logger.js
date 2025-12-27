/**
 * Production-safe logger utility
 * Only logs in development mode to prevent sensitive data exposure
 */

const isDev = import.meta.env.DEV || import.meta.env.MODE === 'development';

/**
 * Logger object with methods that only execute in development mode
 */
const logger = {
    /**
     * Log general information (only in development)
     * @param  {...any} args - Arguments to log
     */
    log(...args) {
        if (isDev) {
            console.log(...args);
        }
    },

    /**
     * Log warnings (only in development)
     * @param  {...any} args - Arguments to log
     */
    warn(...args) {
        if (isDev) {
            console.warn(...args);
        }
    },

    /**
     * Log errors (always logs - errors should be visible)
     * @param  {...any} args - Arguments to log
     */
    error(...args) {
        console.error(...args);
    },

    /**
     * Log debug information (only in development)
     * @param  {...any} args - Arguments to log
     */
    debug(...args) {
        if (isDev) {
            console.debug(...args);
        }
    },

    /**
     * Log information (only in development)
     * @param  {...any} args - Arguments to log
     */
    info(...args) {
        if (isDev) {
            console.info(...args);
        }
    },

    /**
     * Log a group of messages (only in development)
     * @param {string} label - Group label
     */
    group(label) {
        if (isDev) {
            console.group(label);
        }
    },

    /**
     * End a log group (only in development)
     */
    groupEnd() {
        if (isDev) {
            console.groupEnd();
        }
    },

    /**
     * Log a table (only in development)
     * @param {any} data - Data to display as table
     */
    table(data) {
        if (isDev) {
            console.table(data);
        }
    }
};

export default logger;
