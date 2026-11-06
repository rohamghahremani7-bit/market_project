from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timezone as datetime_timezone
from urllib.parse import urlencode
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .forms import CsvImportForm
from .models import Symbol, Candle, CsvImportLog
from .serializers import SymbolSerializer
from .services import import_candles_csv
from accounts.permissions import operator_required

@operator_required
def import_csv(request):
    form = CsvImportForm(request.POST or None, request.FILES or None)
    result = None
    if request.method == 'POST' and form.is_valid():
        try:
            result = import_candles_csv(form.cleaned_data['file'], form.cleaned_data['symbol'],
                                        form.cleaned_data['timeframe'], request.user)
            messages.success(request, f'ورود فایل پایان یافت: {result.inserted_rows} کندل جدید، '
                             f'{result.duplicate_rows} تکراری و {result.invalid_rows} ردیف نامعتبر.')
            if result.chart_from_ts is not None and result.chart_to_ts is not None:
                chart_query = urlencode({
                    'timeframe': result.timeframe,
                    'from': result.chart_from_ts,
                    'to': result.chart_to_ts,
                    'source': 'csv',
                    'filename': result.filename,
                })
                result.chart_url = f"{reverse('chart_detail', kwargs={'symbol_code': result.symbol.code})}?{chart_query}"
            form = CsvImportForm()
        except ValueError as exc:
            messages.error(request, str(exc))
    logs = CsvImportLog.objects.select_related('symbol', 'user')[:10]
    return render(request, 'marketdata/import_csv.html', {'form': form, 'result': result, 'logs': logs})

@login_required
def chart_home(request):
    symbols = Symbol.objects.filter(is_active=True)
    return render(request, 'marketdata/chart_home.html', {'symbols': symbols})

@login_required
def chart_detail(request, symbol_code):
    symbol = get_object_or_404(Symbol, code=symbol_code.upper(), is_active=True)
    timeframes = Candle.Timeframe.choices
    valid_timeframes = set(Candle.Timeframe.values)
    selected_timeframe = request.GET.get('timeframe', '1h')
    if selected_timeframe not in valid_timeframes:
        selected_timeframe = '1h'

    def safe_epoch(value):
        try:
            parsed = int(value)
            # Keep chart URLs within Python/JavaScript's sensible date range.
            if parsed < 0 or parsed > 4102444800:
                return None
            return parsed
        except (TypeError, ValueError):
            return None

    from_ts = safe_epoch(request.GET.get('from'))
    to_ts = safe_epoch(request.GET.get('to'))
    if from_ts is not None and to_ts is not None and from_ts > to_ts:
        from_ts, to_ts = to_ts, from_ts

    local_tz = timezone.get_current_timezone()
    from_date = datetime.fromtimestamp(from_ts, tz=local_tz).date().isoformat() if from_ts is not None else ''
    to_date = datetime.fromtimestamp(to_ts, tz=local_tz).date().isoformat() if to_ts is not None else ''
    context = {
        'symbol': symbol,
        'timeframes': timeframes,
        'selected_timeframe': selected_timeframe,
        'from_ts': from_ts or '',
        'to_ts': to_ts or '',
        'from_date': from_date,
        'to_date': to_date,
        'csv_source': request.GET.get('source') == 'csv',
        'csv_filename': request.GET.get('filename', '')[:255],
    }
    return render(request, 'marketdata/chart_detail.html', context)

@api_view(['GET'])
@permission_classes([AllowAny])
def candles_api(request):
    symbol_code = request.query_params.get('symbol', '').upper()
    timeframe = request.query_params.get('timeframe', '1h')
    if not symbol_code:
        return Response({'error': 'پارامتر symbol الزامی است.'}, status=400)
    if timeframe not in Candle.Timeframe.values:
        return Response({'error': 'تایم‌فریم نامعتبر است.'}, status=400)
    symbol = get_object_or_404(Symbol, code=symbol_code, is_active=True)
    try:
        limit = min(max(int(request.query_params.get('limit', 1000)), 1), settings.MAX_CANDLES_PER_REQUEST)
    except (TypeError, ValueError):
        return Response({'error': 'limit باید عدد صحیح باشد.'}, status=400)

    def parse_epoch_parameter(name):
        raw_value = request.query_params.get(name)
        if raw_value in (None, ''):
            return None
        try:
            value = int(raw_value)
            if value < 0 or value > 4102444800:
                raise ValueError
            return datetime.fromtimestamp(value, tz=datetime_timezone.utc)
        except (TypeError, ValueError, OverflowError, OSError):
            raise ValueError(f'پارامتر {name} باید زمان Unix معتبر برحسب ثانیه باشد.')

    try:
        start_at = parse_epoch_parameter('from')
        end_at = parse_epoch_parameter('to')
    except ValueError as exc:
        return Response({'error': str(exc)}, status=400)
    if start_at and end_at and start_at > end_at:
        return Response({'error': 'زمان شروع نباید بعد از زمان پایان باشد.'}, status=400)

    qs = Candle.objects.filter(symbol=symbol, timeframe=timeframe)
    if start_at:
        qs = qs.filter(timestamp__gte=start_at)
    if end_at:
        qs = qs.filter(timestamp__lte=end_at)
    qs = qs.order_by('-timestamp')[:limit]
    data = list(reversed(list(qs)))
    candles = [{'time': int(c.timestamp.timestamp()), 'open': float(c.open), 'high': float(c.high),
                'low': float(c.low), 'close': float(c.close), 'volume': c.tick_volume} for c in data]
    if data:
        highs = sorted((float(c.high) for c in data), reverse=True)
        lows = sorted(float(c.low) for c in data)
        resistance = highs[:3]
        support = lows[:3]
    else:
        resistance, support = [], []
    return Response({'symbol': symbol.code, 'timeframe': timeframe, 'candles': candles,
                     'support': support, 'resistance': resistance, 'count': len(candles),
                     'range_from': candles[0]['time'] if candles else None,
                     'range_to': candles[-1]['time'] if candles else None})

@api_view(['GET'])
@permission_classes([AllowAny])
def symbols_api(request):
    return Response(SymbolSerializer(Symbol.objects.filter(is_active=True), many=True).data)
