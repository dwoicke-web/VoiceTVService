import React, { useState, useEffect } from 'react';
import axios from 'axios';
import DebugStep from './DebugStep';
import '../styles/DebugDashboard.css';

const DebugDashboard = () => {
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [selectedRun, setSelectedRun] = useState(null);
  const [selectedStepNum, setSelectedStepNum] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filterStatus, setFilterStatus] = useState('all');

  const API_BASE = process.env.REACT_APP_API_URL || '';

  // Poll for runs list every 500ms
  useEffect(() => {
    const fetchRuns = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`${API_BASE}/api/logs/runs?limit=50`);
        setRuns(response.data.runs || []);
        setError(null);
      } catch (err) {
        console.error('Error fetching runs:', err);
        setError('Failed to fetch runs');
      } finally {
        setLoading(false);
      }
    };

    const interval = setInterval(fetchRuns, 500);
    fetchRuns(); // Fetch immediately

    return () => clearInterval(interval);
  }, [API_BASE]);

  // Fetch selected run details
  useEffect(() => {
    if (!selectedRunId) return;

    const fetchRun = async () => {
      try {
        const response = await axios.get(`${API_BASE}/api/logs/runs/${selectedRunId}`);
        setSelectedRun(response.data);
        if (response.data.steps && response.data.steps.length > 0) {
          setSelectedStepNum(response.data.steps[0].step_num);
        }
        setError(null);
      } catch (err) {
        console.error('Error fetching run:', err);
        setError('Failed to fetch run details');
      }
    };

    const interval = setInterval(fetchRun, 500);
    fetchRun(); // Fetch immediately

    return () => clearInterval(interval);
  }, [selectedRunId, API_BASE]);

  const handleRunClick = (runId) => {
    setSelectedRunId(runId);
  };

  const handleDeleteRun = async (runId, e) => {
    e.stopPropagation();
    try {
      await axios.delete(`${API_BASE}/api/logs/runs/${runId}`);
      setRuns(runs.filter(r => r.run_id !== runId));
      if (selectedRunId === runId) {
        setSelectedRunId(null);
        setSelectedRun(null);
      }
    } catch (err) {
      console.error('Error deleting run:', err);
      setError('Failed to delete run');
    }
  };

  const filteredSteps = selectedRun
    ? selectedRun.steps.filter((step) => {
        if (filterStatus === 'all') return true;
        return step.status === filterStatus;
      })
    : [];

  const selectedStep = selectedRun
    ? selectedRun.steps.find(s => s.step_num === selectedStepNum)
    : null;

  return (
    <div className="debug-dashboard">
      <div className="debug-header">
        <h1>🔍 Debug Dashboard</h1>
        <p className="subtitle">Real-time logging of TV launcher execution</p>
      </div>

      <div className="debug-container">
        {/* Left Panel: Run History */}
        <div className="debug-sidebar">
          <h2>Recent Runs</h2>
          {loading && !runs.length && <p className="loading">Loading runs...</p>}
          {error && <p className="error">{error}</p>}
          {runs.length === 0 && !loading && <p className="empty">No runs yet</p>}

          <div className="runs-list">
            {runs.map((run) => (
              <div
                key={run.run_id}
                className={`run-item ${selectedRunId === run.run_id ? 'active' : ''}`}
                onClick={() => handleRunClick(run.run_id)}
              >
                <div className="run-header">
                  <div className={`status-badge ${run.status || 'unknown'}`}>
                    {run.status === 'success' && '✓'}
                    {run.status === 'failure' && '✗'}
                    {!run.status && '?'}
                  </div>
                  <span className="run-title">
                    {run.team_target || run.metadata?.team_target || 'Game'}
                  </span>
                  <button
                    className="delete-btn"
                    onClick={(e) => handleDeleteRun(run.run_id, e)}
                    title="Delete run"
                  >
                    ×
                  </button>
                </div>
                <div className="run-meta">
                  <small>Steps: {run.step_count}</small>
                  {run.start_time && (
                    <small>
                      {new Date(run.start_time).toLocaleTimeString()}
                    </small>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Middle Panel: Steps Timeline */}
        <div className="debug-timeline">
          {selectedRun ? (
            <>
              <h2>Steps ({filteredSteps.length})</h2>
              <div className="filter-controls">
                <label>
                  Status:
                  <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
                    <option value="all">All</option>
                    <option value="success">Success</option>
                    <option value="failure">Failure</option>
                    <option value="pending">Pending</option>
                  </select>
                </label>
              </div>
              <div className="steps-list">
                {filteredSteps.map((step) => (
                  <div
                    key={step.step_num}
                    className={`step-item ${selectedStepNum === step.step_num ? 'active' : ''} ${step.status}`}
                    onClick={() => setSelectedStepNum(step.step_num)}
                  >
                    <div className="step-num">{step.step_num}</div>
                    <div className="step-func">{step.func_name}</div>
                    <div className={`step-status ${step.status}`}>
                      {step.status === 'success' && '✓'}
                      {step.status === 'failure' && '✗'}
                      {step.status === 'pending' && '○'}
                    </div>
                    <div className="step-duration">{step.duration_ms}ms</div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="empty">Select a run to view steps</div>
          )}
        </div>

        {/* Right Panel: Step Details */}
        <div className="debug-detail">
          {selectedStep ? (
            <DebugStep step={selectedStep} runId={selectedRunId} apiBase={API_BASE} />
          ) : selectedRun ? (
            <div className="empty">Select a step to view details</div>
          ) : (
            <div className="empty">Select a run to get started</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DebugDashboard;
