from django.urls import path
from . import views

urlpatterns = [
    # Job Description endpoints
    path('job-descriptions/', views.list_job_descriptions, name='list_job_descriptions'),
    path('job-descriptions/create/', views.create_job_description, name='create_job_description'),
    
    # Candidate endpoints
    path('candidates/', views.list_candidates, name='list_candidates'),
    path('candidates/create/', views.create_candidate, name='create_candidate'),
    
    # Interview endpoints
    path('interviews/', views.list_interviews, name='list_interviews'),
    path('interviews/create/', views.create_interview, name='create_interview'),
    path('interviews/<uuid:interview_id>/trigger/', views.trigger_interview, name='trigger_interview'),
    path('interviews/<uuid:interview_id>/results/', views.get_interview_results, name='get_interview_results'),
    
    # Twilio webhooks
    path('webhook/interview/<uuid:interview_id>/twiml/', views.twilio_webhook_twiml, name='twilio_webhook_twiml'),
    path('webhook/interview/<uuid:interview_id>/answer/<uuid:question_id>/', views.twilio_webhook_answer, name='twilio_webhook_answer'),
    path('webhook/interview/<uuid:interview_id>/status/', views.twilio_webhook_status, name='twilio_webhook_status'),
    
    # Test endpoint
    path('test/twiml/', views.test_twiml, name='test_twiml'),
]
