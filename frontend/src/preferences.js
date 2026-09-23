const PREFERENCES_KEY = 'appPreferences';

const DEFAULT_PREFERENCES = {
  theme: 'light',
  notifications: true,
  autoSaveChats: true
};

export function loadPreferences() {
  try {
    const savedPreferences = JSON.parse(localStorage.getItem(PREFERENCES_KEY) || '{}');
    const legacyTheme = localStorage.getItem('theme');

    return {
      ...DEFAULT_PREFERENCES,
      ...savedPreferences,
      theme: savedPreferences.theme || legacyTheme || DEFAULT_PREFERENCES.theme
    };
  } catch (error) {
    return { ...DEFAULT_PREFERENCES };
  }
}

export function savePreferences(updates) {
  const nextPreferences = {
    ...loadPreferences(),
    ...updates
  };

  localStorage.setItem(PREFERENCES_KEY, JSON.stringify(nextPreferences));
  localStorage.setItem('theme', nextPreferences.theme);

  return nextPreferences;
}

export function resolveTheme(themePreference) {
  if (themePreference === 'system') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  return themePreference === 'dark' ? 'dark' : 'light';
}

export function applyThemePreference(themePreference) {
  document.documentElement.setAttribute('data-theme', resolveTheme(themePreference));
  document.documentElement.setAttribute('data-theme-preference', themePreference);
}

export function autoSaveChatsEnabled() {
  return loadPreferences().autoSaveChats !== false;
}
