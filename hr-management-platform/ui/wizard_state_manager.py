"""
Wizard State Manager - Centralized state machine for multi-step wizards.

Features:
- Step navigation with auto-skip logic
- Data persistence in session state
- Validation per step
- Progress tracking
"""

import streamlit as st
from typing import Any, Dict, Optional, Set


class WizardStateManager:
    """Manages state for a multi-step wizard flow"""

    def __init__(self, wizard_id: str, total_steps: int):
        """
        Args:
            wizard_id: Unique identifier (e.g., 'import', 'settings')
            total_steps: Total number of steps in wizard
        """
        self.wizard_id = wizard_id
        self.total_steps = total_steps
        self.state_key = f'wizard_{wizard_id}_state'

    def _ensure_initialized(self):
        """Ensure state is initialized in session state (lazy initialization)"""
        if self.state_key not in st.session_state:
            st.session_state[self.state_key] = {
                'active': False,
                'current_step': 1,
                'data': {},
                'validation_errors': [],
                'skip_map': {},  # {step: bool}
                'completed_steps': set()
            }

    @property
    def state(self) -> Dict:
        """Get current wizard state (ensures initialization)"""
        self._ensure_initialized()
        return st.session_state[self.state_key]

    @property
    def is_active(self) -> bool:
        """Check if wizard is active"""
        return self.state.get('active', False)

    @property
    def current_step(self) -> int:
        """Get current step number"""
        return self.state.get('current_step', 1)

    def activate(self):
        """Start wizard from step 1"""
        self.state['active'] = True
        self.state['current_step'] = 1
        self.state['data'] = {}
        self.state['validation_errors'] = []
        self.state['skip_map'] = {}
        self.state['completed_steps'] = set()
        st.session_state.modal_overlay_visible = True

    def deactivate(self):
        """Close wizard and clear state"""
        self.state['active'] = False
        st.session_state.modal_overlay_visible = False

    def next_step(self):
        """Navigate to next non-skipped step"""
        current = self.state['current_step']
        self.state['completed_steps'].add(current)

        next_step = current + 1
        while next_step <= self.total_steps:
            if not self.state['skip_map'].get(next_step, False):
                self.state['current_step'] = next_step
                return
            next_step += 1

        # All remaining steps skipped or reached end
        self.state['current_step'] = self.total_steps

    def prev_step(self):
        """Navigate to previous non-skipped step"""
        current = self.state['current_step']
        prev_step = current - 1

        while prev_step >= 1:
            if not self.state['skip_map'].get(prev_step, False):
                self.state['current_step'] = prev_step
                return
            prev_step -= 1

    def goto_step(self, step: int):
        """Jump to specific step"""
        if 1 <= step <= self.total_steps:
            self.state['current_step'] = step

    def set_skip(self, step: int, skip: bool):
        """Mark step as skipped/unskipped"""
        self.state['skip_map'][step] = skip

    def set_data(self, key: str, value: Any):
        """Save data for wizard"""
        self.state['data'][key] = value

    def get_data(self, key: str, default: Any = None) -> Any:
        """Get saved data"""
        return self.state['data'].get(key, default)

    def get_all_data(self) -> Dict:
        """Get all wizard data"""
        return self.state['data']

    def is_step_completed(self, step: int) -> bool:
        """Check if step was completed"""
        return step in self.state['completed_steps']

    def is_step_skipped(self, step: int) -> bool:
        """Check if step is marked as skipped"""
        return self.state['skip_map'].get(step, False)

    def add_error(self, error: str):
        """Add validation error"""
        self.state['validation_errors'].append(error)

    def clear_errors(self):
        """Clear validation errors"""
        self.state['validation_errors'] = []

    def has_errors(self) -> bool:
        """Check if validation errors exist"""
        return len(self.state['validation_errors']) > 0

    def get_errors(self) -> list:
        """Get all validation errors"""
        return self.state['validation_errors']

    def get_progress_percentage(self) -> float:
        """Calculate progress percentage (0-100)"""
        return (self.current_step / self.total_steps) * 100

    def reset(self):
        """Reset wizard to initial state"""
        self.state['current_step'] = 1
        self.state['data'] = {}
        self.state['validation_errors'] = []
        self.state['skip_map'] = {}
        self.state['completed_steps'] = set()


# Singleton instances
_import_wizard = None
_settings_wizard = None
_onboarding_wizard = None


def get_import_wizard() -> WizardStateManager:
    """Get import wizard instance (singleton)"""
    global _import_wizard
    if _import_wizard is None:
        _import_wizard = WizardStateManager('import', total_steps=5)
    return _import_wizard


def get_settings_wizard() -> WizardStateManager:
    """Get settings wizard instance (singleton)"""
    global _settings_wizard
    if _settings_wizard is None:
        _settings_wizard = WizardStateManager('settings', total_steps=3)
    return _settings_wizard


def get_onboarding_wizard() -> WizardStateManager:
    """Get onboarding wizard instance (singleton)"""
    global _onboarding_wizard
    if _onboarding_wizard is None:
        _onboarding_wizard = WizardStateManager('onboarding', total_steps=4)
    return _onboarding_wizard
