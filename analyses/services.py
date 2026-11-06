import json
from django.conf import settings
from django.utils import timezone
from marketdata.models import Candle
from .models import AnalysisRequest, AnalysisVersion, PromptTemplate
from .providers import get_provider

SYSTEM_PROMPT = '''You are a cautious technical market analyst. Analyze only the supplied OHLCV context. Do not claim certainty, do not promise profit, and do not issue personalized financial advice. Every scenario must be conditional and include invalidation. Return one valid JSON object only, with keys: market_trend, market_structure, price_action, support_resistance, liquidity_zones, bullish_scenario, bearish_scenario, entry_zone, stop_loss_invalidation, targets, confidence, risk_analysis, summary. Use concise structured values. confidence must be an integer 0-100. Explicitly state when data is insufficient. Keep bullish and bearish alternatives balanced. Never invent current prices or levels not derived from the supplied data.'''


LANGUAGE_INSTRUCTIONS = {
    'fa': 'تمام متن‌های قابل‌خواندن برای انسان را فقط به زبان فارسی بنویس. نام کلیدهای JSON باید دقیقاً انگلیسی و مطابق قرارداد خروجی باقی بمانند. confidence باید عدد صحیح باشد.',
    'en': 'Write all human-readable text values in English only. Keep JSON keys exactly as specified. confidence must remain an integer.',
    'both': (
        'Write every human-readable text value bilingually in Persian and English within the same JSON value. '
        'Use this exact convention: فارسی: ...\nEnglish: .... '
        'Keep JSON keys exactly as specified and keep confidence as an integer from 0 to 100. '
        'Do not translate or alter the JSON keys.'
    ),
}

def get_default_prompt_template(purpose='price_action'):
    selected = PromptTemplate.objects.filter(
        purpose=purpose, is_active=True, is_default=True
    ).first()
    if selected:
        return selected
    # If the administrator has not marked a default, use the most recently updated active template.
    return PromptTemplate.objects.filter(
        purpose=purpose, is_active=True
    ).order_by('-updated_at', '-pk').first()

def build_effective_system_prompt(template=None):
    base_prompt = template.system_prompt.strip() if template else SYSTEM_PROMPT
    language = template.output_language if template else 'both'
    language_instruction = LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS['both'])
    return f'{base_prompt}\n\nOUTPUT LANGUAGE POLICY:\n{language_instruction}'

def _number(value):
    return float(value)

def _timeframe_snapshot(symbol, timeframe, limit):
    rows = list(Candle.objects.filter(symbol=symbol, timeframe=timeframe).order_by('-timestamp')[:limit])
    rows.reverse()
    if not rows:
        return {'available': False, 'timeframe': timeframe, 'count': 0}
    closes = [_number(x.close) for x in rows]
    highs = [_number(x.high) for x in rows]
    lows = [_number(x.low) for x in rows]
    first, last = closes[0], closes[-1]
    delta_pct = ((last - first) / first * 100) if first else 0
    mean = sum(closes) / len(closes)
    variance = sum((x - mean) ** 2 for x in closes) / len(closes)
    def ema_last(values, period):
        if len(values) < period:
            return None
        k = 2 / (period + 1)
        current = sum(values[:period]) / period
        for value in values[period:]:
            current = value * k + current * (1 - k)
        return round(current, 8)
    rsi_value = None
    if len(closes) > 14:
        changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [max(x, 0) for x in changes]
        losses = [max(-x, 0) for x in changes]
        avg_gain = sum(gains[:14]) / 14
        avg_loss = sum(losses[:14]) / 14
        for i in range(14, len(gains)):
            avg_gain = (avg_gain * 13 + gains[i]) / 14
            avg_loss = (avg_loss * 13 + losses[i]) / 14
        rsi_value = round(100 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss), 2)
    ema12, ema26 = ema_last(closes, 12), ema_last(closes, 26)
    macd_value = round(ema12 - ema26, 8) if ema12 is not None and ema26 is not None else None
    return {
        'available': True, 'timeframe': timeframe, 'count': len(rows),
        'first_timestamp': rows[0].timestamp.isoformat(), 'last_timestamp': rows[-1].timestamp.isoformat(),
        'first_close': round(first, 8), 'last_close': round(last, 8),
        'change_percent': round(delta_pct, 4), 'range_high': max(highs), 'range_low': min(lows),
        'close_mean': round(mean, 8), 'close_stddev': round(variance ** 0.5, 8),
        'indicators': {'sma20': round(sum(closes[-20:]) / 20, 8) if len(closes) >= 20 else None,
                       'ema50': ema_last(closes, 50), 'rsi14': rsi_value, 'macd_12_26': macd_value},
        'recent_candles': [{'time': x.timestamp.isoformat(), 'o': _number(x.open), 'h': _number(x.high),
                            'l': _number(x.low), 'c': _number(x.close), 'v': x.tick_volume} for x in rows[-settings.AI_MAX_CANDLES:]],
    }

def collect_market_context(symbol, timeframe):
    # محدودسازی ورودی: تاریخچه نامحدود به API ارسال نمی‌شود.
    preferred = [timeframe, '1d', '4h', '1h', '15m', '5m']
    ordered = list(dict.fromkeys(preferred))
    snapshots = {}
    for tf in ordered[:6]:
        snapshots[tf] = _timeframe_snapshot(symbol, tf, 120 if tf == timeframe else 60)
    primary = snapshots.get(timeframe, {})
    if not primary.get('available'):
        raise ValueError(f'برای {symbol.code} در تایم‌فریم {timeframe} داده کندلی وجود ندارد.')
    return {'symbol': symbol.code, 'requested_timeframe': timeframe, 'multi_timeframe': snapshots,
            'generated_at': timezone.now().isoformat(), 'data_note': 'Only bounded, recent OHLCV summaries are supplied.'}

def _parse_result(raw):
    text = raw.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError('پاسخ هوش مصنوعی باید یک شیء JSON باشد.')
    required = ['market_trend', 'market_structure', 'price_action', 'support_resistance',
                'liquidity_zones', 'bullish_scenario', 'bearish_scenario', 'entry_zone',
                'stop_loss_invalidation', 'targets', 'confidence', 'risk_analysis', 'summary']
    for key in required:
        data.setdefault(key, 'اطلاعات کافی ارائه نشده است.')
    try:
        data['confidence'] = max(0, min(100, int(data['confidence'])))
    except (TypeError, ValueError):
        data['confidence'] = 0
    return data

def generate_analysis(*, symbol, timeframe, horizon, notes, user, prompt_template=None):
    context = collect_market_context(symbol, timeframe)

    if prompt_template is not None:
        if prompt_template.purpose != 'price_action' or not prompt_template.is_active:
            raise ValueError('قالب انتخاب‌شده برای تحلیل Price Action فعال یا مجاز نیست.')
        selected_template = prompt_template
    else:
        selected_template = get_default_prompt_template('price_action')

    effective_system_prompt = build_effective_system_prompt(selected_template)
    model = (
        selected_template.model_override.strip()
        if selected_template and selected_template.model_override.strip()
        else settings.OPENAI_MODEL
    )
    payload = {
        'task': 'price_action_market_analysis',
        'horizon': horizon,
        'operator_notes': notes[:1200],
        'market_data': context,
        'instruction': 'Build conditional 24-hour scenarios.' if horizon == '24h' else 'Build conditional one-week scenarios.',
    }
    if selected_template:
        payload['prompt_template'] = {
            'key': selected_template.key,
            'title': selected_template.title,
            'revision': selected_template.revision,
        }
        if selected_template.user_prompt_template.strip():
            payload['additional_prompt_instructions'] = selected_template.user_prompt_template.strip()

    prompt_snapshot = effective_system_prompt
    if selected_template and selected_template.user_prompt_template.strip():
        prompt_snapshot += '\n\nADDITIONAL USER PROMPT INSTRUCTIONS:\n' + selected_template.user_prompt_template.strip()

    request = AnalysisRequest.objects.create(
        symbol=symbol,
        timeframe=timeframe,
        horizon=horizon,
        status=AnalysisRequest.Status.DRAFT,
        provider=settings.AI_PROVIDER,
        model_name=model,
        prompt_snapshot=prompt_snapshot,
        prompt_template=selected_template,
        prompt_revision=selected_template.revision if selected_template else None,
        market_snapshot=context,
        created_by=user,
    )
    try:
        provider = get_provider()
        raw = provider.generate(
            model=model,
            system_prompt=effective_system_prompt,
            user_prompt=json.dumps(payload, ensure_ascii=False, separators=(',', ':')),
        )
        result = _parse_result(raw)
        request.result = result
        request.confidence = result.get('confidence', 0)
        request.status = (
            AnalysisRequest.Status.PENDING_REVIEW
            if settings.AI_REQUIRE_ADMIN_APPROVAL
            else AnalysisRequest.Status.PUBLISHED
        )
        if request.status == AnalysisRequest.Status.PUBLISHED:
            request.published_at = timezone.now()
        request.save(update_fields=['result', 'confidence', 'status', 'published_at', 'updated_at'])
        AnalysisVersion.objects.create(
            analysis=request,
            version_number=1,
            result_snapshot=result,
            note='نسخه اولیه تولیدشده توسط AI',
            changed_by=user,
        )
    except Exception as exc:
        request.status = AnalysisRequest.Status.FAILED
        request.error_message = str(exc)[:2000]
        request.save(update_fields=['status', 'error_message', 'updated_at'])
        raise
    return request

def save_analysis_version(analysis, user, note='ویرایش تحلیل'):
    latest = analysis.versions.order_by('-version_number').first()
    number = (latest.version_number if latest else 0) + 1
    return AnalysisVersion.objects.create(analysis=analysis, version_number=number,
        result_snapshot=analysis.result, note=note, changed_by=user)
