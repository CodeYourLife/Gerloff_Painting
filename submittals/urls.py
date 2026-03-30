from django.urls import path

from . import views


urlpatterns = [
path("submittals_home", views.submittals_home, name='submittals_home'),
path("submittals_new/<job_number>", views.submittals_new, name='submittals_new'),
path("submittals_page/<id>", views.submittals_page, name='submittals_page'),
path("submittals_item_close/<id>", views.submittals_item_close, name='submittals_item_close'),
path("submittals_new_selectjob", views.submittals_new_selectjob, name='submittals_new_selectjob'),
path('submittal_send/<submittal_id>', views.submittal_send, name='submittal_send'),
path('submittal_item_detail/<item_id>',views.submittal_item_detail,name='submittal_item_detail'
),
]