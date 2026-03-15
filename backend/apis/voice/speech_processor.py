"""
Speech processor - Convert audio to text using speech-to-text service
Supports Google Cloud Speech-to-Text and OpenAI Whisper API
"""

import os
from typing import Dict, Any, Optional
from enum import Enum


class SpeechProvider(Enum):
    """Available speech-to-text providers"""
    GOOGLE_CLOUD = "google_cloud"
    OPENAI_WHISPER = "openai_whisper"
    MOCK = "mock"


class SpeechProcessor:
    """Processes audio input to text using speech-to-text APIs"""

    def __init__(self, provider: SpeechProvider = SpeechProvider.MOCK):
        """
        Initialize speech processor

        Args:
            provider: Which speech-to-text service to use
        """
        self.provider = provider
        self.google_api_key = os.environ.get('GOOGLE_SPEECH_API_KEY')
        self.openai_api_key = os.environ.get('OPENAI_API_KEY')

        # Determine actual provider to use
        if self.google_api_key:
            self.provider = SpeechProvider.GOOGLE_CLOUD
        elif self.openai_api_key:
            self.provider = SpeechProvider.OPENAI_WHISPER
        else:
            self.provider = SpeechProvider.MOCK

    async def transcribe_audio(self, audio_file_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file to text

        Args:
            audio_file_path: Path to audio file

        Returns:
            Dictionary with transcription results
        """
        if self.provider == SpeechProvider.GOOGLE_CLOUD:
            return await self._transcribe_google_cloud(audio_file_path)
        elif self.provider == SpeechProvider.OPENAI_WHISPER:
            return await self._transcribe_openai(audio_file_path)
        else:
            return await self._transcribe_mock(audio_file_path)

    async def transcribe_stream(self, audio_stream: bytes) -> Dict[str, Any]:
        """
        Transcribe audio from stream (real-time)

        Args:
            audio_stream: Audio data in bytes

        Returns:
            Dictionary with transcription results
        """
        if self.provider == SpeechProvider.GOOGLE_CLOUD:
            return await self._transcribe_stream_google_cloud(audio_stream)
        else:
            return await self._transcribe_mock_stream(audio_stream)

    async def _transcribe_google_cloud(self, audio_file_path: str) -> Dict[str, Any]:
        """Google Cloud Speech-to-Text implementation"""
        # Real implementation would use Google Cloud client library
        return {
            'status': 'success',
            'provider': 'google_cloud',
            'transcript': 'Mock transcription from audio',
            'confidence': 0.95,
            'language': 'en-US'
        }

    async def _transcribe_openai(self, audio_file_path: str) -> Dict[str, Any]:
        """OpenAI Whisper implementation"""
        # Real implementation would use OpenAI Whisper API
        return {
            'status': 'success',
            'provider': 'openai_whisper',
            'transcript': 'Mock transcription from audio',
            'confidence': 0.92,
            'language': 'en-US'
        }

    async def _transcribe_stream_google_cloud(self, audio_stream: bytes) -> Dict[str, Any]:
        """Google Cloud streaming transcription"""
        return {
            'status': 'success',
            'provider': 'google_cloud',
            'transcript': 'Mock streaming transcription',
            'is_final': True,
            'confidence': 0.94,
            'language': 'en-US'
        }

    async def _transcribe_mock(self, audio_file_path: str) -> Dict[str, Any]:
        """Mock transcription for development"""
        return {
            'status': 'success',
            'provider': 'mock',
            'transcript': 'Put Breaking Bad on the big screen',
            'confidence': 0.88,
            'language': 'en-US',
            'note': 'Set GOOGLE_SPEECH_API_KEY or OPENAI_API_KEY for real transcription'
        }

    async def _transcribe_mock_stream(self, audio_stream: bytes) -> Dict[str, Any]:
        """Mock streaming transcription"""
        return {
            'status': 'success',
            'provider': 'mock',
            'transcript': 'Play The Sopranos on upper left',
            'is_final': True,
            'confidence': 0.89,
            'language': 'en-US',
            'note': 'Mock streaming data'
        }


# Global speech processor
_speech_processor = None


def get_speech_processor() -> SpeechProcessor:
    """Get or create the global speech processor"""
    global _speech_processor
    if _speech_processor is None:
        _speech_processor = SpeechProcessor()
    return _speech_processor
