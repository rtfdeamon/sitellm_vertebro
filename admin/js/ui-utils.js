(function (global) {
  const existing = global.UIUtils || {};

  const formatBytes = (value) => {
    const numeric = Number(value);
    if (!Number.isFinite(numeric) || numeric <= 0) return '0 B';
    const UNITS = ['B', 'KB', 'MB', 'GB', 'TB'];
    let bytes = numeric;
    let unitIndex = 0;
    while (bytes >= 1024 && unitIndex < UNITS.length - 1) {
      bytes /= 1024;
      unitIndex += 1;
    }
    const precision = unitIndex === 0 ? 0 : bytes < 10 ? 1 : 0;
    return `${bytes.toFixed(precision)} ${UNITS[unitIndex]}`;
  };

  const formatBytesOptional = (value) => {
    const numeric = Number(value || 0);
    return numeric > 0 ? formatBytes(numeric) : '—';
  };

  const formatTimestamp = (value) => {
    if (value === null || value === undefined) return '—';
    let timestamp = Number(value);
    if (!Number.isFinite(timestamp)) return '—';
    if (timestamp < 1e11) {
      timestamp *= 1000;
    }
    const date = new Date(timestamp);
    if (Number.isNaN(date.getTime())) return '—';
    return date.toLocaleString();
  };

  const pulseCard = (card) => {
    if (!card) return;
    card.classList.remove('updated');
    void card.offsetWidth; // trigger reflow
    card.classList.add('updated');
    setTimeout(() => card.classList.remove('updated'), 1800);
  };

  const getDefaultWidgetPath = (project) => {
    const slug = typeof project === 'string' ? project.trim().toLowerCase() : '';
    if (!slug) return '';
    return `/widget?project=${encodeURIComponent(slug)}`;
  };

  const resolveWidgetHref = (path) => {
    if (!path) return null;
    const raw = String(path).trim();
    if (!raw) return null;
    if (/^[a-z]+:\/\//i.test(raw)) return raw;
    if (raw.startsWith('//')) return `${global.location.protocol}${raw}`;
    if (raw.startsWith('/')) return `${global.location.origin}${raw}`;
    return `${global.location.origin}/${raw.replace(/^\/+/, '')}`;
  };

  global.UIUtils = {
    ...existing,
    formatBytes,
    formatBytesOptional,
    formatTimestamp,
    pulseCard,
    getDefaultWidgetPath,
    resolveWidgetHref,
  };
})(window);
