import json
from django.db.models import Q
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from accounts.permissions import operator_required
from marketdata.models import Symbol
from .forms import AnalysisCreateForm
from .models import AnalysisRequest, AnalysisBookmark
from .services import generate_analysis, save_analysis_version

@login_required
def analysis_list(request):
    qs = AnalysisRequest.objects.filter(status=AnalysisRequest.Status.PUBLISHED).select_related('symbol', 'created_by')
    if request.user.is_operator:
        if request.user.is_admin_role:
            qs = AnalysisRequest.objects.all().select_related('symbol', 'created_by')
        else:
            qs = AnalysisRequest.objects.filter(Q(status=AnalysisRequest.Status.PUBLISHED) | Q(created_by=request.user)).select_related('symbol', 'created_by')
    symbol_code = request.GET.get('symbol', '').upper()
    if symbol_code:
        qs = qs.filter(symbol__code=symbol_code)
    return render(request, 'analyses/analysis_list.html', {'analyses': qs, 'symbols': Symbol.objects.filter(is_active=True), 'selected_symbol': symbol_code})

@operator_required
def analysis_create(request):
    form = AnalysisCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            analysis = generate_analysis(symbol=form.cleaned_data['symbol'], timeframe=form.cleaned_data['timeframe'],
                horizon=form.cleaned_data['horizon'], notes=form.cleaned_data['notes'], user=request.user,
                prompt_template=form.cleaned_data.get('prompt_template'))
            if analysis.status == AnalysisRequest.Status.PUBLISHED:
                messages.success(request, 'تحلیل تولید و منتشر شد.')
            else:
                messages.success(request, 'تحلیل تولید شد و برای بازبینی ثبت شد.')
            return redirect('analysis_detail', pk=analysis.pk)
        except Exception as exc:
            messages.error(request, f'تولید تحلیل انجام نشد: {exc}')
    return render(request, 'analyses/analysis_form.html', {'form': form, 'api_ready': bool(settings.OPENAI_API_KEY)})

@login_required
def analysis_detail(request, pk):
    analysis = get_object_or_404(AnalysisRequest.objects.select_related('symbol', 'created_by', 'reviewed_by').prefetch_related('versions'), pk=pk)
    if analysis.status != AnalysisRequest.Status.PUBLISHED and not (request.user.is_admin_role or request.user == analysis.created_by):
        return redirect('analysis_list')
    bookmarked = request.user.is_authenticated and AnalysisBookmark.objects.filter(user=request.user, analysis=analysis).exists()
    result_text = json.dumps(analysis.result, ensure_ascii=False, indent=2)
    return render(request, 'analyses/analysis_detail.html', {'analysis': analysis, 'bookmarked': bookmarked,
                  'result_text': result_text, 'require_admin_approval': settings.AI_REQUIRE_ADMIN_APPROVAL})

@login_required
@require_POST
def analysis_bookmark(request, pk):
    analysis = get_object_or_404(AnalysisRequest, pk=pk, status=AnalysisRequest.Status.PUBLISHED)
    bookmark, created = AnalysisBookmark.objects.get_or_create(user=request.user, analysis=analysis)
    if not created:
        bookmark.delete()
        messages.info(request, 'تحلیل از نشان‌شده‌ها حذف شد.')
    else:
        messages.success(request, 'تحلیل ذخیره شد.')
    return redirect('analysis_detail', pk=analysis.pk)

@operator_required
@require_POST
def analysis_action(request, pk):
    analysis = get_object_or_404(AnalysisRequest, pk=pk)
    if not request.user.is_admin_role and analysis.created_by_id != request.user.pk:
        messages.error(request, 'فقط سازنده تحلیل یا مدیر سامانه می‌تواند آن را تغییر دهد.')
        return redirect('analysis_list')
    if analysis.status == AnalysisRequest.Status.PUBLISHED and not request.user.is_admin_role:
        messages.error(request, 'ویرایش تحلیل منتشرشده فقط برای مدیر مجاز است.')
        return redirect('analysis_detail', pk=pk)
    action = request.POST.get('action')
    if 'result_json' in request.POST and request.POST['result_json'].strip():
        try:
            edited = json.loads(request.POST['result_json'])
            if not isinstance(edited, dict):
                raise ValueError('خروجی باید یک JSON object باشد.')
            if edited != analysis.result:
                analysis.result = edited
                try:
                    analysis.confidence = max(0, min(100, int(edited.get('confidence', analysis.confidence))))
                except (TypeError, ValueError):
                    pass
                analysis.save(update_fields=['result', 'confidence', 'updated_at'])
                save_analysis_version(analysis, request.user, 'ثبت نسخه ویرایش‌شده')
        except Exception as exc:
            messages.error(request, f'ساختار JSON معتبر نیست: {exc}')
            return redirect('analysis_detail', pk=pk)
    if action == 'publish':
        if settings.AI_REQUIRE_ADMIN_APPROVAL and not request.user.is_admin_role:
            messages.error(request, 'انتشار این تحلیل به تأیید مدیر نیاز دارد.')
        else:
            analysis.status = AnalysisRequest.Status.PUBLISHED
            analysis.reviewed_by = request.user
            analysis.published_at = timezone.now()
            analysis.save(update_fields=['status', 'reviewed_by', 'published_at', 'updated_at'])
            messages.success(request, 'تحلیل منتشر شد.')
    elif action == 'draft':
        analysis.status = AnalysisRequest.Status.DRAFT
        analysis.save(update_fields=['status', 'updated_at'])
        messages.info(request, 'تحلیل به پیش‌نویس برگشت.')
    elif action == 'save':
        messages.success(request, 'تغییرات تحلیل ذخیره شد و نسخه جدید ثبت شد.')
    else:
        messages.error(request, 'عملیات ناشناخته است.')
    return redirect('analysis_detail', pk=pk)
