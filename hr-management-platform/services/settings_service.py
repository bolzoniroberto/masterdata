"""
Settings Service - User preferences persistence and management.

Handles:
- Theme configuration
- Notification preferences
- Locale settings (language, timezone)
- Settings persistence to JSON
"""

import json
import streamlit as st
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any


class SettingsService:
    """Manages user preferences and settings"""

    def __init__(self, config_dir: Path = None):
        """
        Args:
            config_dir: Directory for config files (default: ./config)
        """
        if config_dir is None:
            config_dir = Path(__file__).parent.parent / 'config'

        self.config_dir = config_dir
        self.config_dir.mkdir(exist_ok=True)
        self.settings_file = self.config_dir / 'user_preferences.json'

        # Default settings
        self.defaults = {
            'theme': 'dark',
            'notifications': {
                'enabled': True,
                'frequency': 'weekly',
                'email': None
            },
            'locale': {
                'language': 'IT',
                'timezone': 'Europe/Rome'
            },
            'wizard_completed': False,
            'completed_at': None,
            'last_updated': None
        }

    def load_settings(self) -> Dict[str, Any]:
        """Load settings from JSON file"""
        if not self.settings_file.exists():
            return self.defaults.copy()

        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                # Merge with defaults to handle new keys
                merged = self.defaults.copy()
                merged.update(settings)
                return merged
        except Exception as e:
            print(f"Error loading settings: {e}")
            return self.defaults.copy()

    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Save settings to JSON file

        Args:
            settings: Settings dictionary to save

        Returns:
            True if successful, False otherwise
        """
        try:
            # Add timestamp
            settings['last_updated'] = datetime.now().isoformat()

            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False

    def get_theme(self) -> str:
        """Get current theme setting"""
        settings = self.load_settings()
        return settings.get('theme', 'dark')

    def set_theme(self, theme: str) -> bool:
        """
        Set theme preference

        Args:
            theme: 'dark', 'light', or 'auto'

        Returns:
            True if successful
        """
        if theme not in ['dark', 'light', 'auto']:
            return False

        settings = self.load_settings()
        settings['theme'] = theme
        return self.save_settings(settings)

    def apply_theme(self, theme: str = None):
        """
        Apply theme to Streamlit session

        Args:
            theme: Theme to apply (if None, loads from settings)
        """
        if theme is None:
            theme = self.get_theme()

        # Store in session state for runtime access
        st.session_state.current_theme = theme

        # Apply CSS based on theme
        if theme == 'dark':
            self._apply_dark_theme()
        elif theme == 'light':
            self._apply_light_theme()
        # 'auto' would need system detection (not implemented)

    def _apply_dark_theme(self):
        """Apply dark theme CSS"""
        st.markdown("""
        <style>
            :root {
                --c-bg: #0f172a;
                --c-surface: #1e293b;
                --c-raised: #334155;
                --c-text: #e2e8f0;
                --c-text-muted: #94a3b8;
                --c-border: #334155;
                --c-hover: #475569;
            }
        </style>
        """, unsafe_allow_html=True)

    def _apply_light_theme(self):
        """Apply light theme CSS"""
        st.markdown("""
        <style>
            :root {
                --c-bg: #ffffff;
                --c-surface: #f8fafc;
                --c-raised: #f1f5f9;
                --c-text: #1e293b;
                --c-text-muted: #64748b;
                --c-border: #e2e8f0;
                --c-hover: #e2e8f0;
            }
        </style>
        """, unsafe_allow_html=True)

    def get_notifications_config(self) -> Dict[str, Any]:
        """Get notification preferences"""
        settings = self.load_settings()
        return settings.get('notifications', self.defaults['notifications'])

    def set_notifications(self, enabled: bool, frequency: str = 'weekly', email: str = None) -> bool:
        """
        Set notification preferences

        Args:
            enabled: Enable/disable notifications
            frequency: 'daily', 'weekly', 'monthly'
            email: Email address for notifications

        Returns:
            True if successful
        """
        if frequency not in ['daily', 'weekly', 'monthly']:
            return False

        settings = self.load_settings()
        settings['notifications'] = {
            'enabled': enabled,
            'frequency': frequency,
            'email': email
        }
        return self.save_settings(settings)

    def get_locale_config(self) -> Dict[str, str]:
        """Get locale configuration"""
        settings = self.load_settings()
        return settings.get('locale', self.defaults['locale'])

    def set_locale(self, language: str = 'IT', timezone: str = 'Europe/Rome') -> bool:
        """
        Set locale preferences

        Args:
            language: Language code ('IT', 'EN')
            timezone: Timezone string

        Returns:
            True if successful
        """
        settings = self.load_settings()
        settings['locale'] = {
            'language': language,
            'timezone': timezone
        }
        return self.save_settings(settings)

    def mark_wizard_completed(self) -> bool:
        """Mark settings wizard as completed"""
        settings = self.load_settings()
        settings['wizard_completed'] = True
        settings['completed_at'] = datetime.now().isoformat()
        return self.save_settings(settings)

    def is_wizard_completed(self) -> bool:
        """Check if settings wizard was completed"""
        settings = self.load_settings()
        return settings.get('wizard_completed', False)

    def reset_settings(self) -> bool:
        """Reset all settings to defaults"""
        return self.save_settings(self.defaults.copy())


# Singleton instance
_settings_service = None


def get_settings_service() -> SettingsService:
    """Get settings service instance (singleton)"""
    global _settings_service
    if _settings_service is None:
        _settings_service = SettingsService()
    return _settings_service
