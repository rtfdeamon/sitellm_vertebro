(function (global) {
  const statsCanvas = document.getElementById('statsCanvas');
  const statsTooltip = document.getElementById('statsTooltip');
  const statsEmpty = document.getElementById('statsEmpty');
  const statsSummary = document.getElementById('statsSummary');
  const statsSubtitle = document.getElementById('statsSubtitle');
  const statsRefreshBtn = document.getElementById('statsRefresh');
  const statsExportBtn = document.getElementById('statsExport');

  const STATS_DAYS = 14;

  const formatTemplate = (template, params = {}) => {
    if (typeof template !== 'string') return '';
    return template.replace(/\{(\w+)\}/g, (_, token) => {
      if (Object.prototype.hasOwnProperty.call(params, token)) {
        const replacement = params[token];
        return replacement === null || replacement === undefined ? '' : String(replacement);
      }
      return '';
    });
  };

  const translate = (key, fallback = '', params = undefined) => {
    if (typeof global.t === 'function') {
      try {
        return params ? global.t(key, params) : global.t(key);
      } catch (error) {
        console.warn('stats_translate_failed', error);
      }
    }
    if (fallback) {
      return formatTemplate(fallback, params);
    }
    return key;
  };

  const statsGraphState = {
    data: [],
    currentPoints: [],
    startPoints: [],
    targetPoints: [],
    animationId: null,
    startTime: 0,
    duration: 520,
    hoverIndex: null,
    width: 0,
    height: 0,
    pixelRatio: global.devicePixelRatio || 1,
    lastSignature: '',
    renderedPoints: [],
  };

  const formatDateISO = (date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  const ensureStatsCanvas = () => {
    if (!statsCanvas) return null;
    const rect = statsCanvas.getBoundingClientRect();
    const width = rect.width || statsCanvas.parentElement?.clientWidth || 400;
    const height = rect.height || statsCanvas.parentElement?.clientHeight || 200;
    const dpr = global.devicePixelRatio || 1;
    const scaledWidth = Math.round(width * dpr);
    const scaledHeight = Math.round(height * dpr);
    if (statsCanvas.width !== scaledWidth || statsCanvas.height !== scaledHeight) {
      statsCanvas.width = scaledWidth;
      statsCanvas.height = scaledHeight;
    }
    statsGraphState.width = width;
    statsGraphState.height = height;
    statsGraphState.pixelRatio = dpr;
    return { width, height, dpr };
  };

  const buildStatsPoints = (stats) => {
    if (!stats || !stats.length) return [];
    const dims = ensureStatsCanvas();
    if (!dims) return [];
    const { width, height } = dims;
    const paddingX = 28;
    const paddingTop = 40;
    const paddingBottom = 24;
    const innerWidth = Math.max(width - paddingX * 2, 10);
    const innerHeight = Math.max(height - paddingTop - paddingBottom, 10);
    const maxValue = Math.max(...stats.map((item) => item.count || 0), 1);
    const step = stats.length > 1 ? innerWidth / (stats.length - 1) : 0;
    return stats.map((item, idx) => ({
      x: paddingX + step * idx,
      y: height - paddingBottom - ((item.count || 0) / maxValue) * innerHeight,
      value: item.count || 0,
      date: item.date,
    }));
  };

  const drawStatsGraph = (points) => {
    if (!statsCanvas) return;
    const dims = ensureStatsCanvas();
    if (!dims) return;
    const { width, height, dpr } = dims;
    const ctx = statsCanvas.getContext('2d');
    const paddingX = 28;
    const paddingTop = 40;
    const paddingBottom = 24;
    const baseline = height - paddingBottom;

    ctx.save();
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);

    ctx.strokeStyle = 'rgba(148, 163, 184, 0.12)';
    ctx.lineWidth = 1;
    ctx.setLineDash([6, 6]);
    const gridSteps = 4;
    for (let i = 0; i <= gridSteps; i += 1) {
      const y = paddingTop + ((baseline - paddingTop) / gridSteps) * i;
      ctx.beginPath();
      ctx.moveTo(paddingX, y);
      ctx.lineTo(width - paddingX, y);
      ctx.stroke();
    }
    ctx.setLineDash([]);

    if (points.length) {
      ctx.beginPath();
      ctx.moveTo(points[0].x, baseline);
      points.forEach((pt) => ctx.lineTo(pt.x, pt.y));
      ctx.lineTo(points[points.length - 1].x, baseline);
      ctx.closePath();
      const gradient = ctx.createLinearGradient(0, paddingTop, 0, baseline);
      gradient.addColorStop(0, 'rgba(96, 165, 250, 0.32)');
      gradient.addColorStop(1, 'rgba(96, 165, 250, 0.04)');
      ctx.fillStyle = gradient;
      ctx.fill();

      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      for (let i = 1; i < points.length; i += 1) {
        ctx.lineTo(points[i].x, points[i].y);
      }
      ctx.strokeStyle = 'rgba(96, 165, 250, 0.9)';
      ctx.lineWidth = 2;
      ctx.stroke();

      points.forEach((pt, idx) => {
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, idx === statsGraphState.hoverIndex ? 4.6 : 3.2, 0, Math.PI * 2);
        ctx.fillStyle = idx === statsGraphState.hoverIndex ? '#ffffff' : 'rgba(96, 165, 250, 0.86)';
        ctx.fill();
      });

      const highlightIndex = statsGraphState.hoverIndex ?? points.length - 1;
      if (points[highlightIndex]) {
        const pt = points[highlightIndex];
        ctx.beginPath();
        ctx.moveTo(pt.x, paddingTop);
        ctx.lineTo(pt.x, baseline);
        ctx.strokeStyle = 'rgba(96, 165, 250, 0.28)';
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    }

    ctx.restore();
    statsGraphState.renderedPoints = points;
  };

  const animateStatsGraphTo = (points, animate = true) => {
    if (!animate) {
      statsGraphState.currentPoints = points;
      drawStatsGraph(points);
      return;
    }
    const previous = statsGraphState.currentPoints;
    if (!previous.length || previous.length !== points.length) {
      statsGraphState.currentPoints = points;
      drawStatsGraph(points);
      return;
    }
    const startPoints = previous.map((pt) => ({ ...pt }));
    const targetPoints = points.map((pt) => ({ ...pt }));
    const duration = statsGraphState.duration;
    statsGraphState.startPoints = startPoints;
    statsGraphState.targetPoints = targetPoints;
    statsGraphState.startTime = performance.now();
    if (statsGraphState.animationId) global.cancelAnimationFrame(statsGraphState.animationId);

    const step = (timestamp) => {
      const elapsed = timestamp - statsGraphState.startTime;
      const progress = Math.min(1, elapsed / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      const blended = startPoints.map((start, idx) => {
        const target = targetPoints[idx];
        return {
          ...target,
          x: start.x + (target.x - start.x) * eased,
          y: start.y + (target.y - start.y) * eased,
        };
      });
      statsGraphState.currentPoints = blended;
      drawStatsGraph(blended);
      if (progress < 1) {
        statsGraphState.animationId = global.requestAnimationFrame(step);
      } else {
        statsGraphState.animationId = null;
      }
    };
    statsGraphState.animationId = global.requestAnimationFrame(step);
  };

  const handleStatsHover = (event) => {
    if (!statsCanvas || !statsGraphState.renderedPoints?.length) return;
    const rect = statsCanvas.getBoundingClientRect();
    const clientX = event.touches?.[0]?.clientX ?? event.clientX;
    const x = clientX - rect.left;
    let closest = 0;
    let minDist = Number.POSITIVE_INFINITY;
    statsGraphState.renderedPoints.forEach((pt, idx) => {
      const dist = Math.abs(pt.x - x);
      if (dist < minDist) {
        minDist = dist;
        closest = idx;
      }
    });
    statsGraphState.hoverIndex = closest;
    drawStatsGraph(
      statsGraphState.currentPoints.length ? statsGraphState.currentPoints : statsGraphState.renderedPoints,
    );
    if (statsTooltip && statsGraphState.data[closest]) {
      const dataPoint = statsGraphState.data[closest];
      const point = statsGraphState.renderedPoints[closest];
      statsTooltip.textContent = `${dataPoint.date}: ${dataPoint.count}`;
      statsTooltip.classList.add('show');

      const containerWidth =
        statsGraphState.width ||
        statsCanvas?.parentElement?.clientWidth ||
        statsTooltip.parentElement?.clientWidth ||
        0;
      const tooltipWidth = statsTooltip.offsetWidth || 0;
      const margin = 12;
      let left = point.x - tooltipWidth / 2;
      if (containerWidth && tooltipWidth) {
        const maxLeft = Math.max(margin, containerWidth - margin - tooltipWidth);
        left = Math.max(margin, Math.min(left, maxLeft));
      }
      if (!Number.isFinite(left)) left = point.x;
      statsTooltip.style.left = `${left}px`;

      if (tooltipWidth) {
        const arrowOffset = Math.min(
          Math.max(point.x - left, 8),
          tooltipWidth - 8,
        );
        statsTooltip.style.setProperty('--arrow-offset', `${arrowOffset}px`);
      } else {
        statsTooltip.style.removeProperty('--arrow-offset');
      }

      const clampedY = Math.max(point.y, 32);
      statsTooltip.style.top = `${clampedY}px`;
    }
  };

  const clearStatsHover = () => {
    statsGraphState.hoverIndex = null;
    drawStatsGraph(statsGraphState.currentPoints);
    if (statsTooltip) {
      statsTooltip.classList.remove('show');
      statsTooltip.style.removeProperty('--arrow-offset');
    }
  };

  const renderStatsChart = (stats, { animate = true } = {}) => {
    if (!statsCanvas) return;
    statsGraphState.hoverIndex = null;
    if (statsTooltip) {
      statsTooltip.classList.remove('show');
      statsTooltip.style.removeProperty('--arrow-offset');
    }

    const hasData = Array.isArray(stats) && stats.length > 0;
    if (statsEmpty) statsEmpty.style.display = hasData ? 'none' : 'grid';

    if (!hasData) {
      statsGraphState.data = [];
      statsGraphState.currentPoints = [];
      drawStatsGraph([]);
      if (statsSummary) {
        const emptyText = translate('statsNoData', 'No data');
        statsSummary.dataset.summaryTotal = '';
        statsSummary.dataset.summaryAverage = '';
        statsSummary.dataset.summaryHasAverage = 'false';
        statsSummary.dataset.lastText = emptyText;
        statsSummary.textContent = emptyText;
      }
      if (statsSubtitle) {
        statsSubtitle.dataset.rangeMode = 'relative';
        statsSubtitle.dataset.rangeDays = String(STATS_DAYS);
        statsSubtitle.textContent = translate('statsRangeLastDays', 'Last {days} days', { days: STATS_DAYS });
      }
      return;
    }

    statsGraphState.data = stats;
    const signature = stats.map((item) => `${item.date}:${item.count || 0}`).join('|');
    const shouldAnimate = animate && statsGraphState.lastSignature && statsGraphState.lastSignature !== signature;
    statsGraphState.lastSignature = signature;

    const points = buildStatsPoints(stats);
    statsGraphState.currentPoints = statsGraphState.currentPoints.length ? statsGraphState.currentPoints : points;
    animateStatsGraphTo(points, shouldAnimate);

    const total = stats.reduce((sum, item) => sum + (item.count || 0), 0);
    const average = total && stats.length ? (total / stats.length).toFixed(1) : null;
    if (statsSummary) {
      const hasAverage = Boolean(total && average);
      const text = total
        ? translate(
            hasAverage ? 'statsSummaryTotalAverage' : 'statsSummaryTotal',
            hasAverage
              ? `Total ${total} requests · per day ${average}`
              : `Total ${total} requests`,
            { total, average },
          )
        : translate('statsNoData', 'No data');
      statsSummary.dataset.summaryTotal = total ? String(total) : '';
      statsSummary.dataset.summaryAverage = hasAverage ? String(average) : '';
      statsSummary.dataset.summaryHasAverage = hasAverage ? 'true' : 'false';
      statsSummary.dataset.lastText = text;
      statsSummary.textContent = text;
    }
    if (statsSubtitle) {
      const first = stats[0]?.date;
      const last = stats[stats.length - 1]?.date;
      if (first && last && stats.length > 1) {
        statsSubtitle.dataset.rangeMode = 'explicit';
        statsSubtitle.dataset.rangeStart = first;
        statsSubtitle.dataset.rangeEnd = last;
        statsSubtitle.textContent = `${first} — ${last}`;
      } else {
        statsSubtitle.dataset.rangeMode = 'relative';
        statsSubtitle.dataset.rangeDays = String(STATS_DAYS);
        statsSubtitle.textContent = translate('statsRangeLastDays', 'Last {days} days', { days: STATS_DAYS });
      }
    }
  };

  const loadRequestStats = async () => {
    if (!statsCanvas) return;
    const previousSummary = statsSummary ? (statsSummary.dataset.lastText || statsSummary.textContent) : '';
    if (statsSummary) statsSummary.textContent = translate('statsLoading', 'Loading…');
    if (statsEmpty) statsEmpty.textContent = translate('statsLoadingShort', 'Loading…');
    const params = new URLSearchParams();
    if (global.currentProject) params.set('project', global.currentProject);
    const end = new Date();
    const start = new Date(end);
    start.setDate(end.getDate() - (STATS_DAYS - 1));
    params.set('start', formatDateISO(start));
    params.set('end', formatDateISO(end));
    try {
      const resp = await fetch(`/api/v1/admin/stats/requests?${params.toString()}`);
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();
      if (statsEmpty) statsEmpty.textContent = translate('statsNoData', 'No data');
      renderStatsChart(data.stats || [], { animate: true });
    } catch (error) {
      console.error(error);
      if (statsEmpty) {
        statsEmpty.textContent = translate('statsLoadError', 'Load error');
        statsEmpty.style.display = 'grid';
      }
      drawStatsGraph([]);
      if (statsSummary) {
        statsSummary.textContent = translate('statsLoadError', 'Load error');
      }
      setTimeout(() => {
        if (statsSummary && statsSummary.textContent === translate('statsLoadError', 'Load error')) {
          statsSummary.textContent = previousSummary || '—';
        }
      }, 3000);
    }
  };

  const exportRequestStats = async () => {
    if (!statsExportBtn) return;
    const params = new URLSearchParams();
    if (global.currentProject) params.set('project', global.currentProject);
    const end = new Date();
    const start = new Date(end);
    start.setDate(end.getDate() - (STATS_DAYS - 1));
    params.set('start', formatDateISO(start));
    params.set('end', formatDateISO(end));
    const previousSummary = statsSummary ? (statsSummary.dataset.lastText || statsSummary.textContent) : '';
    try {
      if (statsSummary) statsSummary.textContent = translate('statsCsvPreparing', 'Preparing CSV…');
      const resp = await fetch(`/api/v1/admin/stats/requests/export?${params.toString()}`);
      if (!resp.ok) {
        const message = await resp.text();
        throw new Error(message || `HTTP ${resp.status}`);
      }
      const blob = await resp.blob();
      const href = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = href;
      link.download = `request-stats-${global.currentProject || 'all'}.csv`;
      document.body.appendChild(link);
      link.click();
      global.requestAnimationFrame(() => {
        document.body.removeChild(link);
        URL.revokeObjectURL(href);
      });
      if (statsSummary) {
        statsSummary.textContent = translate('statsCsvExported', 'CSV exported');
        setTimeout(() => {
          if (statsSummary.textContent === translate('statsCsvExported', 'CSV exported')) {
            statsSummary.textContent = previousSummary || '—';
          }
        }, 2600);
      }
    } catch (error) {
      console.error(error);
      if (statsSummary) {
        statsSummary.textContent = `${translate('statsExportError', 'Export error')}: ${error.message || error}`;
        setTimeout(() => {
          if (statsSummary.textContent?.startsWith(translate('statsExportError', 'Export error'))) {
            statsSummary.textContent = previousSummary || '—';
          }
        }, 3600);
      }
    }
  };

  const handleResize = () => {
    if (!statsCanvas || !statsGraphState.data.length) return;
    const points = buildStatsPoints(statsGraphState.data);
    statsGraphState.currentPoints = points;
    drawStatsGraph(points);
  };

  const handleLanguageApplied = () => {
    renderStatsChart(statsGraphState.data, { animate: false });
  };

  const bindEvents = () => {
    if (statsCanvas) {
      statsCanvas.addEventListener('mousemove', handleStatsHover);
      statsCanvas.addEventListener('mouseleave', clearStatsHover);
      statsCanvas.addEventListener('touchstart', handleStatsHover, { passive: true });
      statsCanvas.addEventListener('touchmove', handleStatsHover, { passive: true });
      statsCanvas.addEventListener('touchend', clearStatsHover);
    }
    global.addEventListener('resize', handleResize);
    if (statsRefreshBtn) statsRefreshBtn.addEventListener('click', loadRequestStats);
    if (statsExportBtn) statsExportBtn.addEventListener('click', exportRequestStats);
  };

  const init = () => {
    if (global.StatsModule?.__initialized) return;
    bindEvents();
    global.StatsModule = {
      STATS_DAYS,
      renderStatsChart,
      loadRequestStats,
      exportRequestStats,
      clearStatsHover,
      handleLanguageApplied,
      __initialized: true,
    };
    global.loadRequestStats = loadRequestStats;
    global.exportRequestStats = exportRequestStats;
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})(window);
