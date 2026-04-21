import React, { useState } from 'react';
import '../styles/DebugStep.css';

const DebugStep = ({ step, runId, apiBase }) => {
  const [expandedSections, setExpandedSections] = useState({
    inputs: true,
    outputs: true,
    error: false,
  });

  const toggleSection = (section) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const formatJson = (obj) => {
    try {
      return JSON.stringify(obj, null, 2);
    } catch {
      return String(obj);
    }
  };

  return (
    <div className="debug-step">
      <div className="step-header">
        <h3>Step {step.step_num}: {step.func_name}</h3>
        <div className={`step-status-badge ${step.status}`}>
          {step.status === 'success' && '✓ SUCCESS'}
          {step.status === 'failure' && '✗ FAILURE'}
          {step.status === 'pending' && '○ PENDING'}
        </div>
      </div>

      <div className="step-timing">
        <span className="timestamp">
          {new Date(step.timestamp).toLocaleTimeString()}
        </span>
        <span className="duration">
          {step.duration_ms}ms
        </span>
      </div>

      {/* Inputs Section */}
      <div className="step-section">
        <button
          className="section-toggle"
          onClick={() => toggleSection('inputs')}
        >
          {expandedSections.inputs ? '▼' : '▶'} Inputs
        </button>
        {expandedSections.inputs && (
          <div className="section-content">
            <pre className="json-display">
              {formatJson(step.inputs)}
            </pre>
          </div>
        )}
      </div>

      {/* Outputs Section */}
      <div className="step-section">
        <button
          className="section-toggle"
          onClick={() => toggleSection('outputs')}
        >
          {expandedSections.outputs ? '▼' : '▶'} Outputs
        </button>
        {expandedSections.outputs && (
          <div className="section-content">
            {step.outputs ? (
              <pre className="json-display">
                {formatJson(step.outputs)}
              </pre>
            ) : (
              <p className="empty-value">No output</p>
            )}
          </div>
        )}
      </div>

      {/* Metadata Section */}
      {step.metadata && Object.keys(step.metadata).length > 0 && (
        <div className="step-section">
          <button
            className="section-toggle"
            onClick={() => toggleSection('metadata')}
          >
            {expandedSections.metadata ? '▼' : '▶'} Metadata
          </button>
          {expandedSections.metadata && (
            <div className="section-content">
              <pre className="json-display">
                {formatJson(step.metadata)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Error Section */}
      {step.error && (
        <div className="step-section error">
          <button
            className="section-toggle"
            onClick={() => toggleSection('error')}
          >
            {expandedSections.error ? '▼' : '▶'} Error
          </button>
          {expandedSections.error && (
            <div className="section-content">
              <pre className="error-display">
                {step.error}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Screenshot Display */}
      {step.metadata?.screenshot_id && (
        <div className="step-section">
          <h4>📷 Screenshot</h4>
          <div className="screenshot-container">
            <img
              src={`${apiBase}/api/logs/runs/${runId}/screenshots/${step.metadata.screenshot_id}`}
              alt={`Screenshot from step ${step.step_num}`}
              className="screenshot-image"
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default DebugStep;
