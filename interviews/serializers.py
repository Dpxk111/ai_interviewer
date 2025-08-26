from rest_framework import serializers
from .models import JobDescription, Candidate, Interview, Question, Answer

class JobDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobDescription
        fields = ['id', 'title', 'description', 'questions', 'created_at', 'updated_at']
        read_only_fields = ['id', 'questions', 'created_at', 'updated_at']

class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = ['id', 'name', 'email', 'phone', 'resume', 'resume_text', 'created_at', 'updated_at']
        read_only_fields = ['id', 'resume_text', 'created_at', 'updated_at']

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'question_text', 'question_number', 'created_at']
        read_only_fields = ['id', 'created_at']

class AnswerSerializer(serializers.ModelSerializer):
    audio_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Answer
        fields = ['id', 'audio_file', 'transcript', 'score', 'feedback', 'audio_url', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_audio_url(self, obj):
        if obj.audio_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.audio_file.url)
            return obj.audio_file.url
        return None

class InterviewSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    candidate = CandidateSerializer(read_only=True)
    job_description = JobDescriptionSerializer(read_only=True)
    
    class Meta:
        model = Interview
        fields = [
            'id', 'job_description', 'candidate', 'status', 'twilio_call_sid',
            'call_duration', 'final_score', 'recommendation', 'questions',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'twilio_call_sid', 'call_duration', 'final_score',
            'recommendation', 'created_at', 'updated_at'
        ]

class InterviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interview
        fields = ['job_description', 'candidate']


from .utils import generate_transcript_from_audio
class InterviewResultSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source='candidate.name', read_only=True)
    questions = serializers.SerializerMethodField()

    class Meta:
        model = Interview
        fields = ["id", "candidate_name", "questions"]

    def get_questions(self, obj):
        print("00000000000000")
        questions_data = []
        request = self.context.get("request")

        for question in obj.questions.all():
            answer = question.answers.first()

            transcript = None
            print(answer.transcript, "123213213123123\n\n\n\n")
            print(answer.audio_file, "123213213123123\n\n\n\n")
            if answer:
                print("11111111111111")
                if not answer.transcript:
                    # transcript = generate_transcript_from_audio(answer)
                    pass
                else:
                    transcript = answer.transcript
                print("22222222222222")

            audio_url = None
            if answer and answer.audio_file:
                print("44444444444444")
                if request:
                    print("55555555555555")
                    audio_url = request.build_absolute_uri(answer.audio_file.url)
                else:
                    print("66666666666666")
                    audio_url = answer.audio_file.url

            questions_data.append({
                "question_number": question.question_number,
                "question_text": question.question_text,
                "answer": {
                    "transcript": transcript if transcript else "",
                    "score": answer.score if answer else None,
                    "feedback": answer.feedback if answer else "",
                    "audio_url": audio_url,
                    "audio_duration": getattr(answer, "audio_duration", None) if answer else None,
                } if answer else None
            })
        return questions_data


