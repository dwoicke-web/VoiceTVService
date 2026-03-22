import React, { useState, useRef, useCallback, useEffect } from 'react';
import axios from 'axios';
import '../styles/VoiceControl.css';

const VoiceControl = ({ onCommandExecuted }) => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [lastResult, setLastResult] = useState(null);
  const [error, setError] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const recognitionRef = useRef(null);
  const timeoutRef = useRef(null);
  const finalTranscriptRef = useRef('');

  // Check for Web Speech API support
  const isSupported = !!(window.SpeechRecognition || window.webkitSpeechRecognition);

  useEffect(() => {
    return () => {
      // Cleanup on unmount
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  const sendCommand = useCallback(async (text) => {
    if (!text || !text.trim()) return;

    setIsProcessing(true);
    setError(null);

    try {
      const response = await axios.post('/api/voice/command', {
        transcript: text.trim(),
        speak_feedback: true
      });

      setLastResult(response.data);

      if (onCommandExecuted) {
        onCommandExecuted(response.data);
      }
    } catch (err) {
      console.error('Voice command error:', err);
      const errorData = err.response?.data;
      setError(errorData?.error || errorData?.message || 'Failed to process voice command');
      setLastResult(errorData || null);
    } finally {
      setIsProcessing(false);
    }
  }, [onCommandExecuted]);

  const startListening = useCallback(() => {
    if (!isSupported) {
      setError('Speech recognition not supported in this browser. Use Chrome or Edge.');
      return;
    }

    setError(null);
    setTranscript('');
    setInterimTranscript('');
    setLastResult(null);
    finalTranscriptRef.current = '';

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();

    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onresult = (event) => {
      let finalTranscript = '';
      let interim = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalTranscript += result[0].transcript;
        } else {
          interim += result[0].transcript;
        }
      }

      if (finalTranscript) {
        setTranscript(finalTranscript);
        setInterimTranscript('');
        finalTranscriptRef.current = finalTranscript;
      } else {
        setInterimTranscript(interim);
      }
    };

    recognition.onend = () => {
      setIsListening(false);
      if (finalTranscriptRef.current) {
        sendCommand(finalTranscriptRef.current);
        finalTranscriptRef.current = '';
      }
    };

    recognition.onerror = (event) => {
      setIsListening(false);
      if (event.error === 'no-speech') {
        setError('No speech detected. Try again.');
      } else if (event.error === 'not-allowed') {
        setError('Microphone access denied. Please allow microphone access.');
      } else if (event.error === 'aborted') {
        // User cancelled
      } else {
        setError(`Speech error: ${event.error}`);
      }
    };

    recognitionRef.current = recognition;
    recognition.start();

    // Auto-stop after 10 seconds
    timeoutRef.current = setTimeout(() => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    }, 10000);
  }, [isSupported, sendCommand]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
  }, []);

  const handleMicClick = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  const getStatusText = () => {
    if (isProcessing) return 'Processing command...';
    if (isListening) return 'Listening... speak now';
    return 'Push to talk';
  };

  const getStatusClass = () => {
    if (isProcessing) return 'processing';
    if (isListening) return 'listening';
    return '';
  };

  return (
    <div className="voice-control">
      <div className="voice-control-header">
        <h3>Voice Control</h3>
      </div>

      <div className="voice-control-body">
        {/* Microphone Button */}
        <button
          className={`mic-button ${isListening ? 'active' : ''} ${isProcessing ? 'processing' : ''}`}
          onClick={handleMicClick}
          disabled={isProcessing || !isSupported}
          title={isListening ? 'Stop listening' : 'Start listening'}
        >
          <div className="mic-icon">
            {isProcessing ? (
              <span className="spinner"></span>
            ) : (
              <svg viewBox="0 0 24 24" fill="currentColor" width="32" height="32">
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
              </svg>
            )}
          </div>
          {isListening && <div className="pulse-ring"></div>}
          {isListening && <div className="pulse-ring delay"></div>}
        </button>

        {/* Status */}
        <div className={`voice-status ${getStatusClass()}`}>
          {getStatusText()}
        </div>

        {/* Live Transcript */}
        {(transcript || interimTranscript) && (
          <div className="voice-transcript">
            {transcript && (
              <span className="voice-transcript-final">{transcript}</span>
            )}
            {interimTranscript && (
              <span className="voice-transcript-interim">{interimTranscript}</span>
            )}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="voice-error">{error}</div>
        )}

        {/* Result */}
        {lastResult && (
          <div className={`voice-result ${lastResult.status === 'success' ? 'success' : 'error'}`}>
            <div className="voice-result-intent">
              {lastResult.parsed_intent && (
                <span className="intent-badge">{lastResult.parsed_intent.replace('_', ' ')}</span>
              )}
            </div>
            {lastResult.voice_response && (
              <div className="voice-result-response">{lastResult.voice_response}</div>
            )}
            {lastResult.message && lastResult.status !== 'success' && (
              <div className="voice-result-message">{lastResult.message}</div>
            )}
          </div>
        )}

        {/* Quick Examples */}
        {!isListening && !transcript && !lastResult && (
          <div className="voice-examples">
            <p className="examples-label">Try saying:</p>
            <ul>
              <li>"Tune to ESPN on upper left"</li>
              <li>"Tune Fox News on lower right"</li>
              <li>"Watch the Penguins game on upper right"</li>
              <li>"Launch Netflix on upper left"</li>
              <li>"Turn on all TVs"</li>
              <li>"Reset antenna"</li>
            </ul>
          </div>
        )}

        {!isSupported && (
          <div className="voice-unsupported">
            Your browser doesn't support speech recognition.
            Please use Chrome or Edge.
          </div>
        )}
      </div>
    </div>
  );
};

export default VoiceControl;
