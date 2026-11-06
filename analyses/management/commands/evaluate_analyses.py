from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from analyses.models import AnalysisRequest, AnalysisEvaluation
from marketdata.models import Candle

class Command(BaseCommand):
    help = 'ارزیابی پسینی تحلیل‌های منتشرشده پس از ۲۴ ساعت و یک هفته (بر اساس آخرین کندل در دسترس).'
    def handle(self, *args, **options):
        now = timezone.now()
        created = 0
        for analysis in AnalysisRequest.objects.filter(status=AnalysisRequest.Status.PUBLISHED).select_related('symbol'):
            baseline_time = analysis.published_at or analysis.created_at
            reference = Candle.objects.filter(symbol=analysis.symbol, timeframe=analysis.timeframe, timestamp__lte=baseline_time).order_by('-timestamp').first()
            if not reference:
                continue
            for code, period in [('24h', timedelta(hours=24)), ('1w', timedelta(days=7))]:
                target_time = baseline_time + period
                if now < target_time or AnalysisEvaluation.objects.filter(analysis=analysis, horizon=code).exists():
                    continue
                target = Candle.objects.filter(symbol=analysis.symbol, timeframe=analysis.timeframe, timestamp__gte=target_time).order_by('timestamp').first()
                if not target:
                    continue
                ret = (Decimal(target.close) - Decimal(reference.close)) / Decimal(reference.close) * Decimal('100') if reference.close else Decimal('0')
                expected = str(analysis.result.get('market_trend', '')).lower()
                match = None
                if any(x in expected for x in ['bull', 'صعود', 'bullish']):
                    match = ret > 0
                elif any(x in expected for x in ['bear', 'نزول', 'bearish']):
                    match = ret < 0
                AnalysisEvaluation.objects.create(analysis=analysis, horizon=code, reference_price=reference.close,
                    evaluated_price=target.close, return_percent=ret, direction_match=match,
                    note='ارزیابی مکانیکی بر اساس آخرین کندل موجود؛ معادل توصیه یا بک‌تست معاملاتی نیست.')
                created += 1
        self.stdout.write(self.style.SUCCESS(f'{created} ارزیابی ثبت شد.'))
