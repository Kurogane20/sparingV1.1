/**
 * Data Analysis Utility
 * Rule-based analysis for water quality parameters
 */

// Baku Mutu Standards (Indonesian regulations)
export const standards = {
    ph: { min: 6.0, max: 9.0, unit: '' },
    tss: { max: 100, unit: 'mg/L' },
    cod: { max: 200, unit: 'mg/L' },
    nh3n: { max: 10, unit: 'mg/L' },
    debit: { min: 0, unit: 'L/min' },
    voltage: { min: 200, max: 240, unit: 'V' },
    current: { min: 0, max: 10, unit: 'A' },
    temp: { min: 20, max: 40, unit: '°C' },
};

// Parameter labels
export const paramLabels = {
    ph: 'pH',
    tss: 'TSS',
    cod: 'COD',
    nh3n: 'NH3-N',
    debit: 'Debit Air',
    voltage: 'Tegangan',
    current: 'Arus Listrik',
    temp: 'Temperatur',
};

/**
 * Calculate trend from historical data
 */
export function calculateTrend(data, field) {
    if (!data || data.length < 2) return { direction: 'stable', percentage: 0 };

    const values = data.map(d => d[field]).filter(v => v != null);
    if (values.length < 2) return { direction: 'stable', percentage: 0 };

    const firstHalf = values.slice(0, Math.floor(values.length / 2));
    const secondHalf = values.slice(Math.floor(values.length / 2));

    const avgFirst = firstHalf.reduce((a, b) => a + b, 0) / firstHalf.length;
    const avgSecond = secondHalf.reduce((a, b) => a + b, 0) / secondHalf.length;

    if (avgFirst === 0) return { direction: 'stable', percentage: 0 };

    const change = ((avgSecond - avgFirst) / avgFirst) * 100;

    if (Math.abs(change) < 5) return { direction: 'stable', percentage: Math.abs(change) };
    if (change > 0) return { direction: 'increasing', percentage: change };
    return { direction: 'decreasing', percentage: Math.abs(change) };
}

/**
 * Calculate compliance percentage
 */
export function calculateCompliance(data, field) {
    if (!data || data.length === 0) return { percentage: 0, compliantCount: 0, total: 0 };

    const std = standards[field];
    if (!std) return { percentage: 100, compliantCount: data.length, total: data.length };

    const values = data.map(d => d[field]).filter(v => v != null);
    if (values.length === 0) return { percentage: 0, compliantCount: 0, total: 0 };

    let compliant = 0;
    values.forEach(v => {
        if (std.min !== undefined && std.max !== undefined) {
            if (v >= std.min && v <= std.max) compliant++;
        } else if (std.max !== undefined) {
            if (v <= std.max) compliant++;
        } else if (std.min !== undefined) {
            if (v >= std.min) compliant++;
        }
    });

    return {
        percentage: Math.round((compliant / values.length) * 100),
        compliantCount: compliant,
        total: values.length,
    };
}

/**
 * Detect anomalies using IQR method
 */
export function detectAnomalies(data, field) {
    if (!data || data.length < 4) return { hasAnomalies: false, anomalies: [], count: 0 };

    const values = data.map(d => d[field]).filter(v => v != null).sort((a, b) => a - b);
    if (values.length < 4) return { hasAnomalies: false, anomalies: [], count: 0 };

    const q1 = values[Math.floor(values.length * 0.25)];
    const q3 = values[Math.floor(values.length * 0.75)];
    const iqr = q3 - q1;
    const lowerBound = q1 - 1.5 * iqr;
    const upperBound = q3 + 1.5 * iqr;

    const anomalies = data.filter(d => {
        const v = d[field];
        return v != null && (v < lowerBound || v > upperBound);
    });

    return {
        hasAnomalies: anomalies.length > 0,
        anomalies: anomalies.slice(0, 5), // Return max 5
        count: anomalies.length,
        bounds: { lower: lowerBound, upper: upperBound },
    };
}

/**
 * Calculate statistics
 */
export function calculateStats(data, field) {
    if (!data || data.length === 0) return null;

    const values = data.map(d => d[field]).filter(v => v != null);
    if (values.length === 0) return null;

    const sum = values.reduce((a, b) => a + b, 0);
    const avg = sum / values.length;
    const min = Math.min(...values);
    const max = Math.max(...values);
    const sorted = [...values].sort((a, b) => a - b);
    const median = sorted.length % 2 === 0
        ? (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2
        : sorted[Math.floor(sorted.length / 2)];

    // Standard deviation
    const squareDiffs = values.map(v => Math.pow(v - avg, 2));
    const avgSquareDiff = squareDiffs.reduce((a, b) => a + b, 0) / values.length;
    const stdDev = Math.sqrt(avgSquareDiff);

    return { avg, min, max, median, stdDev, count: values.length };
}

/**
 * Generate recommendations based on analysis
 */
export function generateRecommendations(field, stats, compliance, trend, anomalies) {
    const recommendations = [];
    const std = standards[field];
    const label = paramLabels[field];

    // Compliance recommendations
    if (compliance.percentage < 70) {
        recommendations.push({
            type: 'danger',
            text: `${label} sering melebihi baku mutu. Lakukan tindakan korektif segera.`,
        });
    } else if (compliance.percentage < 90) {
        recommendations.push({
            type: 'warning',
            text: `${label} kadang melebihi baku mutu. Tingkatkan monitoring.`,
        });
    }

    // Trend recommendations
    if (trend.direction === 'increasing' && trend.percentage > 15) {
        if (['tss', 'cod', 'nh3n'].includes(field)) {
            recommendations.push({
                type: 'warning',
                text: `${label} menunjukkan tren meningkat. Periksa sumber pencemaran.`,
            });
        }
    }

    // Anomaly recommendations
    if (anomalies.hasAnomalies && anomalies.count > 3) {
        recommendations.push({
            type: 'warning',
            text: `Ditemukan ${anomalies.count} data anomali. Periksa kalibrasi sensor.`,
        });
    }

    // Parameter-specific recommendations
    if (field === 'ph') {
        if (stats && stats.avg < 6.5) {
            recommendations.push({
                type: 'info',
                text: 'pH cenderung asam. Pertimbangkan penambahan basa untuk netralisasi.',
            });
        } else if (stats && stats.avg > 8.5) {
            recommendations.push({
                type: 'info',
                text: 'pH cenderung basa. Monitor kadar alkalinitas.',
            });
        }
    }

    if (field === 'tss' && stats && stats.avg > 80) {
        recommendations.push({
            type: 'info',
            text: 'TSS tinggi. Evaluasi efektivitas sistem sedimentasi.',
        });
    }

    if (field === 'cod' && stats && stats.avg > 150) {
        recommendations.push({
            type: 'info',
            text: 'COD tinggi. Tingkatkan aerasi atau waktu tinggal di IPAL.',
        });
    }

    if (field === 'voltage') {
        if (stats && (stats.min < 200 || stats.max > 240)) {
            recommendations.push({
                type: 'warning',
                text: 'Tegangan tidak stabil. Periksa sumber listrik dan stabilizer.',
            });
        }
    }

    // Positive feedback
    if (compliance.percentage >= 95 && !anomalies.hasAnomalies && Math.abs(trend.percentage) < 10) {
        recommendations.push({
            type: 'success',
            text: `${label} dalam kondisi optimal. Pertahankan kinerja saat ini.`,
        });
    }

    return recommendations;
}

/**
 * Get status badge based on compliance
 */
export function getComplianceStatus(percentage) {
    if (percentage >= 90) return { status: 'good', label: 'BAIK', color: '#10b981' };
    if (percentage >= 70) return { status: 'warning', label: 'PERHATIAN', color: '#f59e0b' };
    return { status: 'danger', label: 'KRITIS', color: '#ef4444' };
}

/**
 * Get trend icon and label
 */
export function getTrendInfo(trend) {
    if (trend.direction === 'increasing') {
        return { icon: '↗️', label: `Meningkat (+${trend.percentage.toFixed(1)}%)` };
    }
    if (trend.direction === 'decreasing') {
        return { icon: '↘️', label: `Menurun (-${trend.percentage.toFixed(1)}%)` };
    }
    return { icon: '→', label: 'Stabil' };
}

/**
 * Generate full analysis report for a parameter
 */
export function analyzeParameter(data, field) {
    const stats = calculateStats(data, field);
    const compliance = calculateCompliance(data, field);
    const trend = calculateTrend(data, field);
    const anomalies = detectAnomalies(data, field);
    const recommendations = generateRecommendations(field, stats, compliance, trend, anomalies);
    const status = getComplianceStatus(compliance.percentage);
    const trendInfo = getTrendInfo(trend);

    return {
        field,
        label: paramLabels[field],
        standard: standards[field],
        stats,
        compliance,
        trend,
        trendInfo,
        anomalies,
        recommendations,
        status,
    };
}

/**
 * Generate complete analysis for all parameters
 */
export function generateFullAnalysis(data) {
    const parameters = ['ph', 'tss', 'cod', 'nh3n', 'debit', 'voltage', 'current', 'temp'];
    const analyses = {};

    parameters.forEach(field => {
        analyses[field] = analyzeParameter(data, field);
    });

    // Generate summary
    const allCompliance = Object.values(analyses).map(a => a.compliance.percentage);
    const avgCompliance = allCompliance.reduce((a, b) => a + b, 0) / allCompliance.length;

    const criticalParams = Object.values(analyses).filter(a => a.status.status === 'danger');
    const warningParams = Object.values(analyses).filter(a => a.status.status === 'warning');

    const summary = {
        overallCompliance: Math.round(avgCompliance),
        overallStatus: avgCompliance >= 90 ? 'good' : avgCompliance >= 70 ? 'warning' : 'danger',
        criticalCount: criticalParams.length,
        warningCount: warningParams.length,
        totalAnomalies: Object.values(analyses).reduce((sum, a) => sum + a.anomalies.count, 0),
        dataPoints: data.length,
    };

    return { analyses, summary };
}
