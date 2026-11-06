(() => {
  'use strict';

  const root = document.getElementById('market-chart');
  if (!root) return;

  const $ = (id) => document.getElementById(id);
  const status = $('chart-status');
  const symbol = root.dataset.symbol;
  const timeframe = $('timeframe');
  const limit = $('limit');
  const priceField = $('price-field');
  const dateFrom = $('date-from');
  const dateTo = $('date-to');
  const searchInput = $('candle-search');
  const tableBody = $('candle-table-body');
  const tableInfo = $('candle-table-info');
  const fieldLabel = $('chart-field-label');

  if (!window.LightweightCharts) {
    status.textContent = 'کتابخانه نمودار بارگذاری نشد. اتصال مرورگر به unpkg.com یا cdn.jsdelivr.net را بررسی کنید.';
    return;
  }

  const chartOptions = (container, height) => ({
    width: Math.max(container.clientWidth, 300),
    height: height || container.clientHeight || 320,
    layout: { background: { color: '#101923' }, textColor: '#aebdca', fontFamily: 'Tahoma, sans-serif' },
    grid: { vertLines: { color: '#1d2a36' }, horzLines: { color: '#1d2a36' } },
    rightPriceScale: { borderColor: '#2b3947' },
    timeScale: { borderColor: '#2b3947', timeVisible: true, secondsVisible: false },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
  });

  const chart = LightweightCharts.createChart(root, chartOptions(root, 430));
  const candles = chart.addCandlestickSeries({
    upColor: '#2fb88b', downColor: '#e06d72',
    borderUpColor: '#2fb88b', borderDownColor: '#e06d72',
    wickUpColor: '#2fb88b', wickDownColor: '#e06d72',
  });
  const fieldLine = chart.addLineSeries({
    color: '#e4bd70', lineWidth: 2,
    priceLineVisible: false, lastValueVisible: true,
    crosshairMarkerVisible: true, visible: false,
  });
  const volume = chart.addHistogramSeries({
    priceFormat: { type: 'volume' }, priceScaleId: '', visible: true,
    lastValueVisible: false, priceLineVisible: false,
  });
  chart.priceScale('').applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });

  const smaSeries = chart.addLineSeries({ color: '#e7bf69', lineWidth: 2, priceLineVisible: false, lastValueVisible: false });
  const emaSeries = chart.addLineSeries({ color: '#8da9ff', lineWidth: 2, priceLineVisible: false, lastValueVisible: false, visible: false });
  const rsiRoot = $('rsi-chart');
  const macdRoot = $('macd-chart');
  const rsiChart = LightweightCharts.createChart(rsiRoot, chartOptions(rsiRoot, 160));
  const rsiLine = rsiChart.addLineSeries({ color: '#bd8be8', lineWidth: 2, priceLineVisible: false });
  const macdChart = LightweightCharts.createChart(macdRoot, chartOptions(macdRoot, 160));
  const macdLine = macdChart.addLineSeries({ color: '#70a7ff', lineWidth: 2, priceLineVisible: false });
  const signalLine = macdChart.addLineSeries({ color: '#e7bf69', lineWidth: 1, priceLineVisible: false });
  const histogram = macdChart.addHistogramSeries({ priceLineVisible: false, lastValueVisible: false });
  let srLines = [];
  let data = [];
  let initialRangeUsed = false;
  let dateRangeTouched = false;

  const fieldNames = {
    open: 'Open · قیمت بازشدن', high: 'High · بیشترین قیمت',
    low: 'Low · کمترین قیمت', close: 'Close · قیمت بسته‌شدن',
  };
  const fieldColors = { open: '#86a9ff', high: '#e7bf69', low: '#bd8be8', close: '#35bd91' };

  function movingAverage(values, times, period) {
    const out = [];
    for (let i = period - 1; i < values.length; i += 1) {
      let sum = 0;
      for (let j = i - period + 1; j <= i; j += 1) sum += values[j];
      out.push({ time: times[i], value: sum / period });
    }
    return out;
  }

  function ema(values, times, period) {
    if (!values.length) return [];
    const multiplier = 2 / (period + 1);
    const out = [];
    let previous = values[0];
    values.forEach((value, index) => {
      previous = index === 0 ? value : (value * multiplier) + (previous * (1 - multiplier));
      if (index >= period - 1) out.push({ time: times[index], value: previous });
    });
    return out;
  }

  function rsi(values, times, period = 14) {
    if (values.length <= period) return [];
    let gain = 0;
    let loss = 0;
    for (let i = 1; i <= period; i += 1) {
      const delta = values[i] - values[i - 1];
      gain += Math.max(delta, 0);
      loss += Math.max(-delta, 0);
    }
    let averageGain = gain / period;
    let averageLoss = loss / period;
    const calculate = () => averageLoss === 0 ? 100 : 100 - (100 / (1 + (averageGain / averageLoss)));
    const output = [{ time: times[period], value: calculate() }];
    for (let i = period + 1; i < values.length; i += 1) {
      const delta = values[i] - values[i - 1];
      averageGain = ((averageGain * (period - 1)) + Math.max(delta, 0)) / period;
      averageLoss = ((averageLoss * (period - 1)) + Math.max(-delta, 0)) / period;
      output.push({ time: times[i], value: calculate() });
    }
    return output;
  }

  function safeDateText(timestamp) {
    const date = new Date(timestamp * 1000);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleString('fa-IR', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
  }

  function renderCandleTable() {
    const query = (searchInput.value || '').trim().toLocaleLowerCase();
    const activeField = priceField.value;
    const matches = data.filter((item) => {
      if (!query) return true;
      const dateText = safeDateText(item.time).toLocaleLowerCase();
      const isoDate = new Date(item.time * 1000).toISOString().slice(0, 19).replace('T', ' ');
      const priceText = activeField === 'ohlc'
        ? [item.open, item.high, item.low, item.close].join(' ').toLocaleLowerCase()
        : String(item[activeField] ?? '').toLocaleLowerCase();
      return dateText.includes(query) || isoDate.includes(query) || priceText.includes(query);
    });
    const displayRows = matches.slice().reverse().slice(0, 250);
    tableBody.replaceChildren();
    if (!displayRows.length) {
      const row = document.createElement('tr');
      const cell = document.createElement('td');
      cell.colSpan = 6;
      cell.textContent = 'برای این جست‌وجو نتیجه‌ای پیدا نشد.';
      row.appendChild(cell);
      tableBody.appendChild(row);
    } else {
      const fragment = document.createDocumentFragment();
      displayRows.forEach((item) => {
        const row = document.createElement('tr');
        [safeDateText(item.time), item.open, item.high, item.low, item.close, item.volume].forEach((value) => {
          const cell = document.createElement('td');
          cell.textContent = String(value);
          row.appendChild(cell);
        });
        fragment.appendChild(row);
      });
      tableBody.appendChild(fragment);
    }
    const selectedLabel = activeField === 'ohlc' ? 'Open / High / Low / Close' : (fieldNames[activeField] || activeField);
    tableInfo.textContent = `${matches.length.toLocaleString('fa-IR')} ردیف مطابق فیلتر؛ ${displayRows.length.toLocaleString('fa-IR')} ردیف در جدول نمایش داده شده است. جست‌وجوی عددی در فیلد ${selectedLabel} انجام می‌شود.`;
  }

  function updatePriceView() {
    const field = priceField.value;
    const isCandles = field === 'ohlc';
    candles.applyOptions({ visible: isCandles });
    fieldLine.applyOptions({ visible: !isCandles, color: fieldColors[field] || '#e4bd70' });
    if (!isCandles) {
      fieldLine.setData(data.map((item) => ({ time: item.time, value: item[field] })));
      fieldLabel.textContent = `نمودار خطی ${fieldNames[field] || field}`;
    } else {
      fieldLabel.textContent = 'نمودار کندل کامل (Open / High / Low / Close)';
    }
    renderCandleTable();
  }

  function updateIndicators() {
    const closes = data.map((item) => item.close);
    const times = data.map((item) => item.time);
    smaSeries.setData(movingAverage(closes, times, 20));
    emaSeries.setData(ema(closes, times, 50));
    rsiLine.setData(rsi(closes, times, 14));

    const fast = ema(closes, times, 12);
    const slow = ema(closes, times, 26);
    const slowMap = new Map(slow.map((point) => [point.time, point.value]));
    const macd = fast.filter((point) => slowMap.has(point.time)).map((point) => ({ time: point.time, value: point.value - slowMap.get(point.time) }));
    macdLine.setData(macd);
    const macdValues = macd.map((point) => point.value);
    const macdTimes = macd.map((point) => point.time);
    const signal = ema(macdValues, macdTimes, 9);
    signalLine.setData(signal);
    const signalMap = new Map(signal.map((point) => [point.time, point.value]));
    histogram.setData(macd.filter((point) => signalMap.has(point.time)).map((point) => ({
      time: point.time,
      value: point.value - signalMap.get(point.time),
      color: point.value >= signalMap.get(point.time) ? '#2fb88b' : '#e06d72',
    })));
  }

  function updateSupportResistance(payload) {
    srLines.forEach((line) => candles.removePriceLine(line));
    srLines = [];
    if (!data.length || !$('show-sr').checked) return;
    (payload.support || []).slice(0, 3).forEach((price) => {
      srLines.push(candles.createPriceLine({ price, color: '#4cbd9b', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: true, title: 'S' }));
    });
    (payload.resistance || []).slice(0, 3).forEach((price) => {
      srLines.push(candles.createPriceLine({ price, color: '#e17c83', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: true, title: 'R' }));
    });
  }

  function getRangeParameters() {
    // Preserve the exact CSV timestamp boundaries on the first request. If the
    // user changes either date control, switch to the selected calendar range.
    if (!dateRangeTouched && !initialRangeUsed) {
      initialRangeUsed = true;
      return { from: root.dataset.from || '', to: root.dataset.to || '' };
    }
    const result = { from: '', to: '' };
    if (dateFrom.value) {
      const start = new Date(`${dateFrom.value}T00:00:00`);
      if (!Number.isNaN(start.getTime())) result.from = String(Math.floor(start.getTime() / 1000));
    }
    if (dateTo.value) {
      const end = new Date(`${dateTo.value}T23:59:59`);
      if (!Number.isNaN(end.getTime())) result.to = String(Math.floor(end.getTime() / 1000));
    }
    return result;
  }

  async function load() {
    status.textContent = 'در حال دریافت داده‌های قیمت…';
    const params = new URLSearchParams({
      symbol,
      timeframe: timeframe.value,
      limit: limit.value,
    });
    const range = getRangeParameters();
    if (range.from) params.set('from', range.from);
    if (range.to) params.set('to', range.to);

    try {
      const response = await fetch(`/api/candles/?${params.toString()}`, { headers: { Accept: 'application/json' } });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || 'خطا در دریافت داده‌های نمودار');
      data = Array.isArray(payload.candles) ? payload.candles : [];
      candles.setData(data);
      volume.setData(data.map((item) => ({
        time: item.time,
        value: item.volume,
        color: item.close >= item.open ? 'rgba(47,184,139,.42)' : 'rgba(224,109,114,.42)',
      })));
      updateIndicators();
      updatePriceView();
      updateSupportResistance(payload);
      smaSeries.applyOptions({ visible: $('show-sma').checked && data.length >= 20 });
      emaSeries.applyOptions({ visible: $('show-ema').checked && data.length >= 50 });
      volume.applyOptions({ visible: $('show-volume').checked });
      chart.timeScale().fitContent();
      rsiChart.timeScale().fitContent();
      macdChart.timeScale().fitContent();
      if (data.length) {
        status.textContent = `${payload.count.toLocaleString('fa-IR')} کندل برای ${symbol} / ${timeframe.value} بارگذاری شد. بازه: ${safeDateText(data[0].time)} تا ${safeDateText(data[data.length - 1].time)}.`;
      } else {
        status.textContent = 'در این نماد، تایم‌فریم یا بازه زمانی کندلی پیدا نشد. نماد و تایم‌فریم را بررسی کن یا ابتدا فایل CSV را وارد کن.';
      }
    } catch (error) {
      status.textContent = `خطا در دریافت نمودار: ${error.message}`;
      data = [];
      candles.setData([]);
      fieldLine.setData([]);
      volume.setData([]);
      renderCandleTable();
    }
  }

  $('refresh-chart').addEventListener('click', () => {
    dateRangeTouched = true;
    load();
  });
  timeframe.addEventListener('change', load);
  limit.addEventListener('change', load);
  priceField.addEventListener('change', updatePriceView);
  searchInput.addEventListener('input', renderCandleTable);
  [dateFrom, dateTo].forEach((input) => input.addEventListener('change', () => { dateRangeTouched = true; }));
  $('show-sma').addEventListener('change', (event) => smaSeries.applyOptions({ visible: event.target.checked && data.length >= 20 }));
  $('show-ema').addEventListener('change', (event) => emaSeries.applyOptions({ visible: event.target.checked && data.length >= 50 }));
  $('show-volume').addEventListener('change', (event) => volume.applyOptions({ visible: event.target.checked }));
  $('show-sr').addEventListener('change', () => load());

  const resize = () => {
    chart.applyOptions({ width: Math.max(root.clientWidth, 300) });
    rsiChart.applyOptions({ width: Math.max(rsiRoot.clientWidth, 300) });
    macdChart.applyOptions({ width: Math.max(macdRoot.clientWidth, 300) });
  };
  if ('ResizeObserver' in window) {
    const observer = new ResizeObserver(resize);
    [root, rsiRoot, macdRoot].forEach((node) => observer.observe(node));
  } else {
    window.addEventListener('resize', resize);
  }

  load();
})();
