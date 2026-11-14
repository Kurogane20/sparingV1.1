import assert from 'node:assert/strict';
import test from 'node:test';
import {
  dayStrip, durationText, loggerAlertTitle, recoveryText, summaryText,
} from '../resources/js/Utils/loggerDiagnosis.js';

const NOW = Date.parse('2026-11-04T03:00:00Z'); // 10:00 WIB

test('summary counts states in a fixed order and skips zeros', () => {
  const rows = ['normal', 'down', 'normal', 'attention', 'down', 'normal', 'problem', 'down'].map((state) => ({ state }));
  assert.equal(summaryText(rows), '3 normal · 1 perhatian · 1 bermasalah · 3 mati');
  assert.equal(summaryText([]), 'Belum ada logger');
});

test('durations read like the backend', () => {
  assert.equal(durationText(161), '2 jam 41 menit');
  assert.equal(durationText(1500), '1 hari 1 jam');
  assert.equal(durationText(120), '2 jam');
  assert.equal(durationText(0.4), 'kurang dari 1 menit');
});

test('recovery text names the readings lost by an ended down incident only', () => {
  const base = { kind: 'down', ended_at: '2026-10-29T09:43:00Z', data_expected: 81 };
  assert.equal(recoveryText({ ...base, data_recovered: 79 }), '2 bacaan hilang');
  assert.equal(recoveryText({ ...base, data_recovered: 81 }), '');
  assert.equal(recoveryText({ ...base, data_recovered: 0 }), '81 bacaan hilang');
  assert.equal(recoveryText({ ...base, ended_at: null, data_recovered: 0 }), '');
  assert.equal(recoveryText({ ...base, kind: 'rejected', data_recovered: 0 }), '');
});

test('the 30-day strip sums down minutes per local day', () => {
  const cells = dayStrip([
    { kind: 'down', started_at: '2026-10-29T07:02:00Z', ended_at: '2026-10-29T09:43:00Z' }, // 14:02–16:43 WIB
    { kind: 'down', started_at: '2026-11-01T16:00:00Z', ended_at: '2026-11-01T18:00:00Z' }, // 23:00–01:00 WIB
    { kind: 'down', started_at: '2026-11-02T17:00:00', ended_at: null },                    // naive UTC: 3 Nov 00:00 WIB, still open
    { kind: 'rejected', started_at: '2026-10-29T17:00:00Z', ended_at: '2026-10-30T17:00:00Z' },
  ], { timeZone: 'Asia/Jakarta', now: NOW });
  assert.equal(cells.length, 30);
  assert.equal(cells.at(-1).date, '2026-11-04');
  const day = Object.fromEntries(cells.map((cell) => [cell.date, cell]));
  assert.equal(day['2026-10-29'].minutes, 161);
  assert.equal(day['2026-10-29'].level, 'long');
  assert.equal(day['2026-10-29'].text, '29 Okt: gangguan 2 jam 41 menit');
  assert.equal(day['2026-10-30'].level, 'none');
  assert.equal(day['2026-10-30'].text, '30 Okt: tanpa gangguan');
  assert.equal(day['2026-11-01'].minutes, 60);
  assert.equal(day['2026-11-02'].minutes, 60);
  assert.equal(day['2026-11-03'].level, 'full');
  assert.equal(day['2026-11-04'].minutes, 600);
  assert.equal(day['2026-11-04'].level, 'full'); // the whole day so far
});

test('overlapping down incidents count once in the strip', () => {
  const cells = dayStrip([
    { kind: 'down', started_at: '2026-10-29T07:02:00Z', ended_at: '2026-10-29T09:43:00Z' },
    { kind: 'down', started_at: '2026-10-29T08:00:00Z', ended_at: '2026-10-29T10:00:00Z' },
  ], { timeZone: 'Asia/Jakarta', now: NOW });
  const day = cells.find((cell) => cell.date === '2026-10-29');
  assert.equal(day.minutes, 178); // 07:02–10:00 UTC, not 161 + 120
});

test('logger alarm titles cover the new fields and sensors', () => {
  assert.equal(loggerAlertTitle({ field: 'logger_down' }), 'Logger tidak terjangkau');
  assert.equal(loggerAlertTitle({ field: 'rejected_partial' }), 'Sebagian kiriman ditolak server');
  assert.equal(loggerAlertTitle({ field: 'send_fail_klhk' }), 'Kirim ke KLHK gagal');
  assert.equal(loggerAlertTitle({ field: 'sensor_cod' }), 'Sensor COD gagal dibaca');
  assert.equal(loggerAlertTitle({ field: 'something_new' }), 'Kejadian logger');
});
