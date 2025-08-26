from django.urls import path
from . import views

urlpatterns = [
    # Job Description endpoints
    path('job-descriptions/', views.JobDescriptionListView.as_view(), name='list_job_descriptions'),
    path('job-descriptions/create/', views.JobDescriptionCreateView.as_view(), name='create_job_description'),
    
    # Candidate endpoints
    path('candidates/', views.CandidateListView.as_view(), name='list_candidates'),
    path('candidates/create/', views.CandidateCreateView.as_view(), name='create_candidate'),
    
    # Interview endpoints
    path('interviews/', views.InterviewListView.as_view(), name='list_interviews'),
    path('interviews/create/', views.InterviewCreateView.as_view(), name='create_interview'),
    path('interviews/<uuid:interview_id>/trigger/', views.InterviewTriggerView.as_view(), name='trigger_interview'),
    path('interviews/<uuid:interview_id>/results/', views.InterviewResultsView.as_view(), name='get_interview_results'),
    
    # Twilio webhooks
    path('webhook/interview/<uuid:interview_id>/twiml/', views.TwilioWebhookTwiMLView.as_view(), name='twilio_webhook_twiml'),
    path('webhook/interview/<uuid:interview_id>/answer/<uuid:question_id>/', views.TwilioWebhookAnswerView.as_view(), name='twilio_webhook_answer'),
    path('webhook/interview/<uuid:interview_id>/status/', views.TwilioWebhookStatusView.as_view(), name='twilio_webhook_status'),
    # path("webhook/interview/<uuid:interview_id>/answer/<uuid:question_id>/", views.TwilioAnswerWebhookView.as_view(), name="twilio-answer-webhook"),

    # Test endpoint
    path('test/twiml/', views.TestTwiMLView.as_view(), name='test_twiml'),
    
    # Audio file endpoints
    path('audio-files/', views.AudioFilesListView.as_view(), name='list_audio_files'),
    path('audio-files/interview/<uuid:interview_id>/', views.AudioFilesByInterviewView.as_view(), name='list_audio_files_by_interview'),
    
    # Debug endpoints
    path('debug/transcription/<uuid:answer_id>/', views.DebugTranscriptionView.as_view(), name='debug_transcription'),
]
