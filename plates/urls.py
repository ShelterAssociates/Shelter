from django.urls import path

from plates import views

app_name = "plates"

urlpatterns = [
    path("", views.home, name="home"),
    path("single/", views.single, name="single"),
    path("help/", views.help_page, name="help"),
    path("help/plates-guide.pdf", views.help_pdf, name="help_pdf"),
    path("bulk/new/", views.bulk_new, name="bulk_new"),
    path("excel-format/<str:plate_type>/", views.excel_format_download, name="excel_format_download"),
    path("batches/", views.batches_list, name="batches"),
    path("batches/<uuid:public_id>/", views.batch_detail, name="batch_detail"),
    path("batches/<uuid:public_id>/check/", views.bulk_check, name="bulk_check"),
    path("batches/<uuid:public_id>/demo/<int:row_number>/", views.bulk_demo_image, name="bulk_demo_image"),
    path("batches/<uuid:public_id>/rows-to-check/", views.bulk_skipped, name="bulk_skipped"),
    path("batches/<uuid:public_id>/confirm/", views.bulk_confirm, name="bulk_confirm"),
    path("batches/<uuid:public_id>/download/", views.batch_download, name="batch_download"),
    path("batches/<uuid:public_id>/cancel/", views.batch_cancel, name="batch_cancel"),
    path("batches/<uuid:public_id>/generate-again/", views.batch_regenerate, name="batch_regenerate"),
    path("templates/", views.templates, name="templates"),
    path("templates/new/", views.template_new, name="template_new"),
    path("templates/archived/", views.templates_archived, name="templates_archived"),
    path("templates/preview/", views.template_preview, name="template_preview"),
    path("templates/link-preview/", views.link_preview, name="link_preview"),
    path("templates/assets/", views.asset_upload, name="asset_upload"),
    path("templates/fonts/", views.font_upload, name="font_upload"),
    path("templates/<int:pk>/", views.template_edit, name="template_edit"),
    path("templates/<int:pk>/copy/", views.template_copy, name="template_copy"),
    path("templates/<int:pk>/archive/", views.template_archive, name="template_archive"),
    path("templates/<int:pk>/restore/", views.template_restore, name="template_restore"),
    path("templates/<int:pk>/delete/", views.template_delete, name="template_delete"),
    path("templates/<int:pk>/image/", views.template_image, name="template_image"),
]
