from django.db import models
import uuid
import os

def get_upload_path(instance, filename):
    """Generate upload path for files"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('uploads', filename)

class JobDescription(models.Model):
    """Model to store job descriptions and generated questions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    questions = models.JSONField(default=list)  # Store generated questions
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.created_at.strftime('%Y-%m-%d')}"

class Candidate(models.Model):
    """Model to store candidate information"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)  # E.164 format
    resume = models.FileField(upload_to=get_upload_path, null=True, blank=True)
    resume_text = models.TextField(blank=True)  # Parsed resume text
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.email}"

class Interview(models.Model):
    """Model to store interview sessions"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_description = models.ForeignKey(JobDescription, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    twilio_call_sid = models.CharField(max_length=100, null=True, blank=True)
    call_duration = models.IntegerField(null=True, blank=True)  # in seconds
    final_score = models.FloatField(null=True, blank=True)
    recommendation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Interview {self.id} - {self.candidate.name}"

class Question(models.Model):
    """Model to store interview questions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_number = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['question_number']

    def __str__(self):
        return f"Q{self.question_number}: {self.question_text[:50]}..."

class Answer(models.Model):
    """Model to store candidate answers"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    audio_file = models.FileField(upload_to=get_upload_path, null=True, blank=True)
    audio_duration = models.IntegerField(null=True, blank=True)  # Duration in seconds
    transcript = models.TextField(blank=True)
    score = models.FloatField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Answer to Q{self.question.question_number} - {self.transcript[:50]}..."
