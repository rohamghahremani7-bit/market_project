from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from accounts import views as account_views
from marketdata import views as market_views
from publishing import views as publishing_views
from analyses import views as analysis_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', account_views.home, name='home'),
    path('accounts/register/', account_views.register, name='register'),
    path('accounts/login/', account_views.login_view, name='login'),
    path('accounts/logout/', account_views.logout_view, name='logout'),
    path('accounts/profile/', account_views.profile, name='profile'),
    path('accounts/saved/', account_views.saved_items, name='saved_items'),
    path('dashboard/', account_views.dashboard, name='dashboard'),
    path('operator/', account_views.operator_dashboard, name='operator_dashboard'),
    path('operator/users/', account_views.manage_users, name='manage_users'),
    path('operator/articles/', publishing_views.operator_articles, name='operator_articles'),
    path('operator/articles/new/', publishing_views.article_create, name='article_create'),
    path('operator/articles/<int:pk>/edit/', publishing_views.article_edit, name='article_edit'),
    path('operator/articles/<int:pk>/delete/', publishing_views.article_delete, name='article_delete'),
    path('operator/import-csv/', market_views.import_csv, name='import_csv'),
    path('market/charts/', market_views.chart_home, name='chart_home'),
    path('market/charts/<str:symbol_code>/', market_views.chart_detail, name='chart_detail'),
    path('api/candles/', market_views.candles_api, name='candles_api'),
    path('articles/', publishing_views.article_list, name='article_list'),
    path('articles/<str:slug>/', publishing_views.article_detail, name='article_detail'),
    path('articles/<int:pk>/bookmark/', publishing_views.article_bookmark, name='article_bookmark'),
    path('analyses/', analysis_views.analysis_list, name='analysis_list'),
    path('analyses/new/', analysis_views.analysis_create, name='analysis_create'),
    path('analyses/<int:pk>/', analysis_views.analysis_detail, name='analysis_detail'),
    path('analyses/<int:pk>/bookmark/', analysis_views.analysis_bookmark, name='analysis_bookmark'),
    path('analyses/<int:pk>/action/', analysis_views.analysis_action, name='analysis_action'),
    path('api/symbols/', market_views.symbols_api, name='symbols_api'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
