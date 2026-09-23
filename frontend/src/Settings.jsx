import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Moon, Sun, Monitor, Save, LogOut, Trash2, Bell, Lock, User, Database } from 'lucide-react';
import api from './api';
import { applyThemePreference, loadPreferences, savePreferences } from './preferences';

function Settings() {
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const savedPreferences = loadPreferences();
  const [theme, setTheme] = useState(savedPreferences.theme);
  const [notifications, setNotifications] = useState(savedPreferences.notifications);
  const [autoSave, setAutoSave] = useState(savedPreferences.autoSaveChats);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    applyThemePreference(theme);
    savePreferences({ theme });
  }, [theme]);

  const handleThemeChange = (newTheme) => {
    setTheme(newTheme);
  };

  const handleSave = async () => {
    setSaving(true);

    savePreferences({
      theme,
      notifications,
      autoSaveChats: autoSave
    });

    setTimeout(() => {
      setSaving(false);
      alert('Settings saved successfully!');
    }, 1000);
  };

  const handleLogout = async () => {
    try {
      await api.post('/auth/logout');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      navigate('/login');
    }
  };

  const clearChatHistory = () => {
    if (window.confirm('Are you sure you want to delete all chat history?')) {
      Object.keys(localStorage).forEach(key => {
        if (key.startsWith('chat_')) {
          localStorage.removeItem(key);
        }
      });
      localStorage.removeItem('chatHistory');
      localStorage.removeItem('currentChatId');
      alert('Chat history cleared successfully!');
    }
  };

  return (
    <div className="min-h-screen bg-orange-50 bg-beige-paper p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate(-1)}
            className="text-orange-600 hover:text-orange-800 mb-4 flex items-center gap-2"
          >
            ← Back
          </button>
          <h1 className="text-3xl font-bold text-orange-900 mb-2">Settings</h1>
          <p className="text-orange-700">Manage your account preferences and application settings</p>
        </div>

        {/* User Info Card */}
        <div className="bg-beige-100 rounded-xl p-6 mb-6 border border-orange-200 shadow-lg">
          <div className="flex items-center gap-4 mb-4">
            <div className="w-16 h-16 bg-orange-600 rounded-full flex items-center justify-center" style={{background: '#f74b03'}}>
              <User className="w-8 h-8 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-orange-900">{user.name || 'User'}</h2>
              <p className="text-orange-700">{user.email}</p>
              <div className="flex items-center gap-2 mt-1">
                <Shield className="w-4 h-4 text-orange-600" />
                <span className="text-sm text-orange-600 capitalize">{user.role}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Appearance Settings */}
        <div className="bg-beige-100 rounded-xl p-6 mb-6 border border-orange-200 shadow-lg">
          <h3 className="text-lg font-bold text-orange-900 mb-4 flex items-center gap-2">
            <Monitor className="w-5 h-5" />
            Appearance
          </h3>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-orange-900 mb-3">Theme</label>
              <div className="flex gap-3">
                <button
                  onClick={() => handleThemeChange('light')}
                  className={`flex-1 p-4 rounded-lg border-2 transition flex flex-col items-center gap-2 ${
                    theme === 'light' 
                      ? 'border-orange-500 bg-orange-100' 
                      : 'border-orange-300 hover:border-orange-400'
                  }`}
                >
                  <Sun className="w-6 h-6 text-orange-600" />
                  <span className="text-sm text-orange-900">Light</span>
                </button>
                <button
                  onClick={() => handleThemeChange('dark')}
                  className={`flex-1 p-4 rounded-lg border-2 transition flex flex-col items-center gap-2 ${
                    theme === 'dark' 
                      ? 'border-orange-500 bg-orange-100' 
                      : 'border-orange-300 hover:border-orange-400'
                  }`}
                >
                  <Moon className="w-6 h-6 text-orange-600" />
                  <span className="text-sm text-orange-900">Dark</span>
                </button>
                <button
                  onClick={() => handleThemeChange('system')}
                  className={`flex-1 p-4 rounded-lg border-2 transition flex flex-col items-center gap-2 ${
                    theme === 'system' 
                      ? 'border-orange-500 bg-orange-100' 
                      : 'border-orange-300 hover:border-orange-400'
                  }`}
                >
                  <Monitor className="w-6 h-6 text-orange-600" />
                  <span className="text-sm text-orange-900">System</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Notification Settings */}
        <div className="bg-beige-100 rounded-xl p-6 mb-6 border border-orange-200 shadow-lg">
          <h3 className="text-lg font-bold text-orange-900 mb-4 flex items-center gap-2">
            <Bell className="w-5 h-5" />
            Notifications
          </h3>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-orange-900 font-medium">Email Notifications</p>
                <p className="text-sm text-orange-600">Receive updates about your account</p>
              </div>
              <button
                onClick={() => setNotifications(!notifications)}
                className={`w-12 h-6 rounded-full transition ${
                  notifications ? 'bg-orange-600' : 'bg-orange-300'
                }`}
                style={notifications ? {background: '#f74b03'} : {}}
              >
                <div className={`w-5 h-5 bg-white rounded-full transition transform ${
                  notifications ? 'translate-x-6' : 'translate-x-0.5'
                }`} />
              </button>
            </div>
            
            <div className="flex items-center justify-between">
              <div>
                <p className="text-orange-900 font-medium">Auto-save Chats</p>
                <p className="text-sm text-orange-600">Automatically save chat history</p>
              </div>
              <button
                onClick={() => setAutoSave(!autoSave)}
                className={`w-12 h-6 rounded-full transition ${
                  autoSave ? 'bg-orange-600' : 'bg-orange-300'
                }`}
                style={autoSave ? {background: '#f74b03'} : {}}
              >
                <div className={`w-5 h-5 bg-white rounded-full transition transform ${
                  autoSave ? 'translate-x-6' : 'translate-x-0.5'
                }`} />
              </button>
            </div>
          </div>
        </div>

        {/* Data Management */}
        <div className="bg-beige-100 rounded-xl p-6 mb-6 border border-orange-200 shadow-lg">
          <h3 className="text-lg font-bold text-orange-900 mb-4 flex items-center gap-2">
            <Database className="w-5 h-5" />
            Data Management
          </h3>
          
          <div className="space-y-4">
            <button
              onClick={clearChatHistory}
              className="w-full px-4 py-3 bg-orange-200 text-orange-800 border border-orange-300 rounded-lg hover:bg-orange-300 transition flex items-center justify-center gap-2"
            >
              <Trash2 className="w-5 h-5" />
              Clear Chat History
            </button>
          </div>
        </div>

        {/* Security Settings */}
        <div className="bg-beige-100 rounded-xl p-6 mb-6 border border-orange-200 shadow-lg">
          <h3 className="text-lg font-bold text-orange-900 mb-4 flex items-center gap-2">
            <Lock className="w-5 h-5" />
            Security
          </h3>
          
          <div className="space-y-4">
            <button
              onClick={handleLogout}
              className="w-full px-4 py-3 bg-orange-200 text-orange-800 border border-orange-300 rounded-lg hover:bg-orange-300 transition flex items-center justify-center gap-2"
            >
              <LogOut className="w-5 h-5" />
              Logout
            </button>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-6 py-3 text-white rounded-lg transition disabled:opacity-50 flex items-center gap-2 shadow-lg"
            style={{background: '#f74b03'}}
            onMouseEnter={(e) => e.target.style.background = '#cc3c02'}
            onMouseLeave={(e) => e.target.style.background = '#f74b03'}
          >
            <Save className="w-5 h-5" />
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default Settings;
