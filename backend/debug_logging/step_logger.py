"""
StepLogger: Decorator-based function wrapping for detailed execution logging.

Usage:
    @step_log
    def my_function(arg1, arg2):
        return result

    # Or with custom metadata:
    @step_log(metadata={'category': 'screenshot'})
    def capture_screenshot():
        return base64_image
"""

import functools
import time
import uuid
import json
import traceback
import threading
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from contextvars import ContextVar

# Context variable to track current run ID across async/thread contexts
_current_run_id: ContextVar[Optional[str]] = ContextVar('run_id', default=None)
_current_run_step: ContextVar[int] = ContextVar('step_num', default=0)

# Global dictionary to store in-progress runs
_runs_in_memory: Dict[str, List[Dict[str, Any]]] = {}
_runs_lock = threading.Lock()


class StepLogger:
    """Manages detailed logging of function execution steps."""

    def __init__(self):
        self.run_id = None
        self.steps: List[Dict[str, Any]] = []
        self.metadata = {}

    def start_run(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Start a new run and return the run ID."""
        self.run_id = str(uuid.uuid4())
        self.steps = []
        self.metadata = metadata or {}

        _current_run_id.set(self.run_id)
        _current_run_step.set(0)

        with _runs_lock:
            _runs_in_memory[self.run_id] = self.steps

        return self.run_id

    def log_step(
        self,
        func_name: str,
        inputs: Dict[str, Any],
        outputs: Any = None,
        status: str = 'pending',
        duration: float = 0.0,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Log a single step. Returns step number."""
        step_num = _current_run_step.get() + 1
        _current_run_step.set(step_num)

        step = {
            'step_num': step_num,
            'func_name': func_name,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'inputs': _serialize(inputs),
            'outputs': _serialize(outputs) if outputs is not None else None,
            'status': status,
            'duration_ms': int(duration * 1000),
            'error': error,
            'metadata': metadata or {},
        }

        run_id = _current_run_id.get()
        if run_id and run_id in _runs_in_memory:
            _runs_in_memory[run_id].append(step)

        return step_num

    def get_run(self, run_id: str) -> Dict[str, Any]:
        """Get a run by ID (for API retrieval)."""
        with _runs_lock:
            steps = _runs_in_memory.get(run_id, [])
            if not steps:
                return None

            return {
                'run_id': run_id,
                'metadata': self.metadata,
                'steps': steps,
                'step_count': len(steps),
                'start_time': steps[0]['timestamp'] if steps else None,
                'end_time': steps[-1]['timestamp'] if steps else None,
            }

    def get_run_steps(self, run_id: str) -> List[Dict[str, Any]]:
        """Get all steps for a run."""
        with _runs_lock:
            return _runs_in_memory.get(run_id, [])


# Global logger instance
_logger_instance = StepLogger()


def step_log(func: Optional[Callable] = None, *, metadata: Optional[Dict[str, Any]] = None):
    """
    Decorator that logs function execution.

    Usage:
        @step_log
        def my_func(): ...

        @step_log(metadata={'type': 'navigation'})
        def my_func(): ...
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs) -> Any:
            func_name = f.__name__
            inputs = _extract_inputs(args, kwargs, f)

            start_time = time.time()
            error = None
            result = None
            status = 'success'

            try:
                result = f(*args, **kwargs)
                return result
            except Exception as e:
                status = 'failure'
                error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
                raise
            finally:
                duration = time.time() - start_time
                _logger_instance.log_step(
                    func_name=func_name,
                    inputs=inputs,
                    outputs=result,
                    status=status,
                    duration=duration,
                    error=error,
                    metadata=metadata,
                )

        return wrapper

    # Handle both @step_log and @step_log(...) syntax
    if func is not None:
        return decorator(func)
    return decorator


def start_run(metadata: Optional[Dict[str, Any]] = None) -> str:
    """Start a new logging run. Call this before launching a game."""
    return _logger_instance.start_run(metadata)


def log_step(
    func_name: str,
    inputs: Dict[str, Any],
    outputs: Any = None,
    status: str = 'success',
    duration: float = 0.0,
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> int:
    """Log a step manually (for complex logic that decorator can't capture)."""
    return _logger_instance.log_step(func_name, inputs, outputs, status, duration, error, metadata)


def get_run(run_id: str) -> Dict[str, Any]:
    """Get a run by ID."""
    return _logger_instance.get_run(run_id)


def get_current_run_id() -> Optional[str]:
    """Get the current run ID (useful for attaching screenshots)."""
    return _current_run_id.get()


def _extract_inputs(args: tuple, kwargs: dict, func: Callable) -> Dict[str, Any]:
    """Extract function inputs in a serializable format."""
    try:
        import inspect
        sig = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        return dict(bound.arguments)
    except Exception:
        # Fallback if inspection fails
        return {'args': str(args), 'kwargs': str(kwargs)}


def _serialize(obj: Any) -> Any:
    """Safely serialize an object for JSON."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): _serialize(v) for k, v in obj.items()}
    if isinstance(obj, bytes):
        return f"<bytes: {len(obj)} bytes>"
    # For custom objects, use repr
    return repr(obj)
