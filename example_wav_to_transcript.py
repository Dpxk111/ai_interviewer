#!/usr/bin/env python
"""
Example usage of the process_wav_to_transcript utility function.
This script shows different ways to use the function for converting WAV files to transcripts.
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_screener.settings')
django.setup()

from interviews.utils import process_wav_to_transcript

def example_basic_usage():
    """Basic usage example"""
    print("=== Basic Usage Example ===")
    
    # Example WAV file path
    wav_file = "path/to/your/audio.wav"
    
    # Basic usage - converts WAV to MP3 and generates transcript
    result = process_wav_to_transcript(wav_file)
    
    if result['success']:
        print(f"✅ Success! Transcript: {result['transcript']}")
    else:
        print(f"❌ Failed: {result['error']}")

def example_with_custom_mp3_path():
    """Example with custom MP3 output path"""
    print("=== Custom MP3 Path Example ===")
    
    wav_file = "path/to/your/audio.wav"
    custom_mp3_path = "path/to/output/converted_audio.mp3"
    
    # Specify custom MP3 output path
    result = process_wav_to_transcript(wav_file, output_mp3_path=custom_mp3_path)
    
    if result['success']:
        print(f"✅ Success! Transcript: {result['transcript']}")
        print(f"MP3 saved to: {result['mp3_path']}")
    else:
        print(f"❌ Failed: {result['error']}")

def example_batch_processing():
    """Example of processing multiple WAV files"""
    print("=== Batch Processing Example ===")
    
    # Directory containing WAV files
    wav_directory = "media/uploads"
    results = []
    
    if os.path.exists(wav_directory):
        for filename in os.listdir(wav_directory):
            if filename.lower().endswith('.wav'):
                wav_path = os.path.join(wav_directory, filename)
                print(f"Processing: {filename}")
                
                result = process_wav_to_transcript(wav_path)
                results.append({
                    'filename': filename,
                    'result': result
                })
                
                if result['success']:
                    print(f"✅ {filename}: {result['transcript'][:50]}...")
                else:
                    print(f"❌ {filename}: {result['error']}")
    
    # Summary
    successful = sum(1 for r in results if r['result']['success'])
    total = len(results)
    print(f"\nBatch processing complete: {successful}/{total} files processed successfully")

def example_error_handling():
    """Example with comprehensive error handling"""
    print("=== Error Handling Example ===")
    
    wav_file = "path/to/your/audio.wav"
    
    try:
        result = process_wav_to_transcript(wav_file)
        
        if result['success']:
            print(f"✅ Processing successful!")
            print(f"Transcript: {result['transcript']}")
            print(f"Processing time: {result['processing_time']:.2f} seconds")
        else:
            print(f"❌ Processing failed!")
            print(f"Error: {result['error']}")
            print(f"Processing time: {result['processing_time']:.2f} seconds")
            
            # Handle specific error types
            if "not found" in result['error'].lower():
                print("→ File not found error - check the file path")
            elif "api key" in result['error'].lower():
                print("→ API key error - check your AssemblyAI configuration")
            elif "upload failed" in result['error'].lower():
                print("→ Upload error - check your internet connection")
            elif "timed out" in result['error'].lower():
                print("→ Timeout error - the audio file might be too long")
                
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def example_integration_with_django():
    """Example of integrating with Django models"""
    print("=== Django Integration Example ===")
    
    from interviews.models import Answer
    
    # Get an answer that needs transcription
    answer = Answer.objects.filter(transcript__isnull=True).first()
    
    if answer and answer.audio_file:
        print(f"Processing answer ID: {answer.id}")
        
        # Process the audio file
        result = process_wav_to_transcript(answer.audio_file.path)
        
        if result['success']:
            # Update the answer with the transcript
            answer.transcript = result['transcript']
            answer.save()
            print(f"✅ Answer updated with transcript: {result['transcript'][:50]}...")
        else:
            print(f"❌ Failed to process answer: {result['error']}")
    else:
        print("No answers found that need transcription")

if __name__ == "__main__":
    print("WAV to Transcript Utility Examples")
    print("=" * 40)
    
    # Run examples (uncomment the ones you want to test)
    
    # example_basic_usage()
    # example_with_custom_mp3_path()
    # example_batch_processing()
    # example_error_handling()
    # example_integration_with_django()
    
    print("\nTo run specific examples, uncomment them in the script.")
    print("Make sure to update file paths to match your actual files.")
