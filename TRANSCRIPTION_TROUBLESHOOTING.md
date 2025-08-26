# Transcription Troubleshooting Guide

This guide helps you troubleshoot issues with audio transcription using AssemblyAI.

## Common Issues

### 1. "Transcoding failed. File does not appear to contain audio. File type is application/octet-stream (data)"

This error occurs when AssemblyAI cannot recognize the audio file format. Here are the steps to resolve it:

#### Check AssemblyAI API Key
1. Ensure your `ASSEMBLYAI_API_KEY` is set in your environment variables
2. Verify the API key is valid by running the test script:
   ```bash
   python test_transcription.py
   ```

#### Check Audio File Format
1. The audio files from Twilio might not be in the expected format
2. Use the debug endpoint to analyze the file:
   ```bash
   POST /api/debug/transcription/{answer_id}/
   ```

#### Manual Testing
1. Run the test script to check all audio files:
   ```bash
   python test_transcription.py
   ```

### 2. Audio File Validation Issues

If audio files are failing validation:

1. **File too small**: Audio files should be at least 1KB
2. **File empty**: Check if the file was properly saved
3. **Invalid format**: The file might not be a valid audio format

### 3. AssemblyAI API Issues

Common API issues:

1. **Invalid API key**: Check your AssemblyAI API key
2. **Rate limiting**: AssemblyAI has rate limits
3. **File size limits**: Audio files should be under 1GB

## Debug Tools

### 1. Test Script
Run the test script to check all audio files:
```bash
python test_transcription.py
```

### 2. Debug Endpoint
Use the debug endpoint to test specific answers:
```bash
POST /api/debug/transcription/{answer_id}/
```

### 3. Manual File Check
Check audio files manually:
```python
from interviews.utils import validate_audio_file, debug_audio_file
from interviews.models import Answer

# Get an answer
answer = Answer.objects.get(id='your-answer-id')

# Debug the audio file
debug_audio_file(answer)

# Validate the audio file
is_valid, message = validate_audio_file(answer.audio_file.path)
print(f"Valid: {is_valid}, Message: {message}")
```

## Solutions

### 1. Fix Audio File Format
The system now includes:
- Automatic audio format detection
- Conversion to WAV format
- Fallback methods for problematic files

### 2. Improve Error Handling
The updated code includes:
- Better error messages
- Fallback transcription methods
- Detailed logging

### 3. File Validation
The system now validates:
- File existence
- File size
- Audio format
- Audio duration

## Environment Variables

Make sure these are set:
```bash
ASSEMBLYAI_API_KEY=your_assemblyai_api_key_here
```

## Dependencies

Ensure these packages are installed:
```bash
pip install pydub==0.25.1
```

## Logs

Check the Django logs for detailed error messages. The transcription process now includes extensive logging to help identify issues.

## Support

If you continue to have issues:
1. Run the test script and share the output
2. Check the Django logs for error messages
3. Verify your AssemblyAI API key is valid
4. Ensure audio files are being properly saved
