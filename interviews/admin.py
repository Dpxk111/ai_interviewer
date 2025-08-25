from django.contrib import admin
from .models import JobDescription, Candidate, Interview, Question, Answer

@admin.register(JobDescription)
class JobDescriptionAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_at', 'updated_at']
    search_fields = ['title', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'created_at']
    search_fields = ['name', 'email', 'phone']
    readonly_fields = ['id', 'created_at', 'updated_at']

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'interview', 'question_number', 'created_at']
    search_fields = ['question_text']
    list_filter = ['interview']
    readonly_fields = ['id', 'created_at']

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['question', 'score', 'created_at']
    search_fields = ['transcript']
    list_filter = ['score']
    readonly_fields = ['id', 'created_at']

@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'candidate', 'job_description', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['candidate__name', 'job_description__title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('candidate', 'job_description')
