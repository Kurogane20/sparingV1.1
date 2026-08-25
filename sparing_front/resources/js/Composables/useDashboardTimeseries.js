import { computed, getCurrentScope, onScopeDispose, ref } from 'vue';
import { normalizeTimeseriesPayload } from '../Utils/dashboardTimeseries.js';

const PRESETS = new Set(['1h', '6h', '12h', 'today', '24h', '7d']);
const CUSTOM_PRESET = 'custom';
const FIELDS = 'ph,tss,debit';

function getRangeValue(range, names) {
  for (const name of names) {
    const value = range?.[name];
    if (typeof value === 'string' && value) return value;
    if (value instanceof Date && !Number.isNaN(value.getTime())) return value.toISOString();
  }
  return null;
}

export function buildRequestParams(selectedPreset = 'today', range = {}) {
  if (selectedPreset === CUSTOM_PRESET) {
    const dateFrom = getRangeValue(range, ['dateFrom', 'date_from', 'from']);
    const dateTo = getRangeValue(range, ['dateTo', 'date_to', 'to']);
    if (!dateFrom || !dateTo) throw new RangeError('Custom ranges require both date_from and date_to.');
    return { date_from: dateFrom, date_to: dateTo, fields: FIELDS };
  }

  if (!PRESETS.has(selectedPreset)) throw new RangeError(`Unknown dashboard preset: ${selectedPreset}`);
  return { preset: selectedPreset, fields: FIELDS };
}

function readSiteUid(source) {
  if (typeof source === 'function') return source();
  if (source && typeof source === 'object' && 'value' in source) return source.value;
  return source;
}

function hasFiniteValues(snapshot) {
  return ['ph', 'tss', 'debit'].some((field) => snapshot.series[field].points
    .some((point) => typeof point.value === 'number' && Number.isFinite(point.value)));
}

function settledState(snapshot) {
  if (!hasFiniteValues(snapshot)) return 'empty';
  return snapshot.meta.is_partial === true ? 'partial' : 'ready';
}

function isAbortError(error) {
  return error?.name === 'AbortError'
    || error?.code === 'ERR_CANCELED'
    || error?.__CANCEL__ === true;
}

function actionableErrorMessage(error, refreshing) {
  const detail = error?.response?.data?.detail ?? error?.response?.data?.message;
  if (typeof detail === 'string' && detail.trim()) return detail.trim();
  return refreshing
    ? 'Unable to refresh monitoring data. Please try again.'
    : 'Unable to load monitoring data. Please try again.';
}

function normalizeRange(range = {}) {
  return {
    dateFrom: getRangeValue(range, ['dateFrom', 'date_from', 'from']),
    dateTo: getRangeValue(range, ['dateTo', 'date_to', 'to']),
  };
}

export function useDashboardTimeseries({ siteUid, fetchTimeseries, pollMs = 30000 }) {
  if (typeof fetchTimeseries !== 'function') throw new TypeError('fetchTimeseries must be a function.');

  const preset = ref('today');
  const customRange = ref({ dateFrom: null, dateTo: null });
  const snapshot = ref(null);
  const state = ref('idle');
  const errorMessage = ref('');
  const requestInFlight = ref(false);
  const isLoading = computed(() => state.value === 'loading');
  const isRefreshing = computed(() => requestInFlight.value && snapshot.value !== null);
  const isStale = computed(() => state.value === 'stale');

  let requestToken = 0;
  let activeController = null;
  let snapshotSiteUid = null;
  let pollingInterval = null;

  const cancelActiveRequest = () => {
    if (!activeController) return;
    activeController.abort();
    activeController = null;
    requestInFlight.value = false;
  };

  const invalidateSelection = () => {
    requestToken += 1;
    cancelActiveRequest();
    if (!snapshot.value) {
      state.value = 'idle';
      errorMessage.value = '';
    } else if (state.value !== 'stale') {
      state.value = settledState(snapshot.value);
    }
  };

  const load = async ({ reason = 'manual' } = {}) => {
    const currentSiteUid = readSiteUid(siteUid);
    if (!currentSiteUid) {
      if (reason !== 'poll') {
        requestToken += 1;
        cancelActiveRequest();
        snapshot.value = null;
        snapshotSiteUid = null;
        state.value = 'idle';
        errorMessage.value = '';
      }
      return;
    }

    if (reason === 'poll' && activeController) return;

    let params;
    try {
      params = buildRequestParams(preset.value, customRange.value);
    } catch (error) {
      if (reason !== 'poll') {
        requestToken += 1;
        cancelActiveRequest();
        state.value = snapshot.value ? 'stale' : 'error';
        errorMessage.value = 'Choose both dates for a custom range.';
      }
      return;
    }

    if (reason !== 'poll') {
      requestToken += 1;
      cancelActiveRequest();
      if (snapshot.value && snapshotSiteUid !== currentSiteUid) {
        snapshot.value = null;
        snapshotSiteUid = null;
      }
    }

    const token = requestToken;
    const controller = new AbortController();
    activeController = controller;
    requestInFlight.value = true;
    errorMessage.value = '';
    if (!snapshot.value) state.value = 'loading';

    try {
      const payload = await fetchTimeseries(currentSiteUid, params, controller.signal);
      if (token !== requestToken || activeController !== controller) return;

      const normalized = normalizeTimeseriesPayload(payload);
      snapshot.value = normalized;
      snapshotSiteUid = currentSiteUid;
      state.value = settledState(normalized);
      errorMessage.value = '';
    } catch (error) {
      if (token !== requestToken || activeController !== controller) return;
      if (isAbortError(error)) {
        state.value = snapshot.value ? settledState(snapshot.value) : 'idle';
        errorMessage.value = '';
        return;
      }

      const refreshing = snapshot.value !== null;
      state.value = refreshing ? 'stale' : 'error';
      errorMessage.value = actionableErrorMessage(error, refreshing);
    } finally {
      if (token === requestToken && activeController === controller) {
        activeController = null;
        requestInFlight.value = false;
      }
    }
  };

  const retry = () => load();

  const setPreset = (nextPreset) => {
    if (nextPreset !== CUSTOM_PRESET && !PRESETS.has(nextPreset)) {
      throw new RangeError(`Unknown dashboard preset: ${nextPreset}`);
    }
    preset.value = nextPreset;
    if (nextPreset === CUSTOM_PRESET && (!customRange.value.dateFrom || !customRange.value.dateTo)) {
      invalidateSelection();
      return Promise.resolve();
    }
    return load();
  };

  const setCustomRange = (nextRange) => {
    customRange.value = normalizeRange(nextRange);
    preset.value = CUSTOM_PRESET;
    if (!customRange.value.dateFrom || !customRange.value.dateTo) {
      invalidateSelection();
      return Promise.resolve();
    }
    return load();
  };

  const startPolling = () => {
    if (pollingInterval !== null) return;
    pollingInterval = globalThis.setInterval(() => {
      void load({ reason: 'poll' });
    }, pollMs);
  };

  const stopPolling = () => {
    if (pollingInterval !== null) {
      globalThis.clearInterval(pollingInterval);
      pollingInterval = null;
    }
    requestToken += 1;
    cancelActiveRequest();
    if (state.value === 'loading') state.value = 'idle';
  };

  if (getCurrentScope()) onScopeDispose(stopPolling);

  return {
    preset,
    customRange,
    snapshot,
    state,
    errorMessage,
    isLoading,
    isRefreshing,
    isStale,
    load,
    retry,
    setPreset,
    setCustomRange,
    startPolling,
    stopPolling,
  };
}
