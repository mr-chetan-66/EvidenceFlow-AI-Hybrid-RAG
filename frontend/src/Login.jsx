import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogIn, Mail, Lock, User, Shield, Moon, Sun } from 'lucide-react';
import api, { API_BASE } from './api';
import './Login.css';
import { applyThemePreference, loadPreferences, savePreferences } from './preferences';

function Login() {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [googleOAuthEnabled, setGoogleOAuthEnabled] = useState(false);
  const [theme, setTheme] = useState(() => loadPreferences().theme);
  const navigate = useNavigate();

  useEffect(() => {
    // Check if Google OAuth is enabled
    checkGoogleOAuthStatus();
    
    applyThemePreference(theme);
    savePreferences({ theme });
  }, [theme]);

  const checkGoogleOAuthStatus = async () => {
    try {
      const response = await api.get('/');
      // Check if Google OAuth is configured on backend
      // The backend should provide this information in the root endpoint
      if (response.data.google_oauth_enabled === true) {
        setGoogleOAuthEnabled(true);
      } else {
        setGoogleOAuthEnabled(false);
      }
    } catch (error) {
      console.error('Failed to check OAuth status:', error);
      setGoogleOAuthEnabled(false);
    }
  };

  const handleGoogleLogin = () => {
    window.location.href = `${API_BASE}/auth/google`;
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isLogin) {
        // Login
        const response = await api.post('/auth/login', {
          email: formData.email,
          password: formData.password
        });

        // Clear any existing tokens and store new ones
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        localStorage.setItem('token', response.data.access_token);
        localStorage.setItem('user', JSON.stringify(response.data.user));

        // Redirect based on role
        if (response.data.user.role === 'admin') {
          navigate('/admin');
        } else {
          navigate('/');
        }
      } else {
        // Register - always as user by default
        const response = await api.post('/auth/register', {
          email: formData.email,
          password: formData.password,
          name: formData.name,
          role: 'user' // Default to user role for self-registration
        });

        // Auto-login after registration
        const loginResponse = await api.post('/auth/login', {
          email: formData.email,
          password: formData.password
        });

        // Clear any existing tokens and store new ones
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        localStorage.setItem('token', loginResponse.data.access_token);
        localStorage.setItem('user', JSON.stringify(loginResponse.data.user));

        // Always redirect to chat for self-registered users
        navigate('/');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-orange-50 bg-beige-paper p-4 relative">
      {/* Theme Toggle */}
      <button
        onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
        className="absolute top-4 right-4 p-2 bg-orange-200 border border-orange-300 rounded-lg hover:bg-orange-300 transition shadow-sm hover:shadow-md"
        title={theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode'}
      >
        {theme === 'light' ? <Moon className="w-5 h-5 text-orange-800" /> : <Sun className="w-5 h-5 text-orange-800" />}
      </button>
      
      <div className="max-w-md w-full">
        <div className="bg-beige-100 rounded-xl shadow-lg p-8 border-2 border-orange-200 login-card">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="w-12 h-12 rounded-lg flex items-center justify-center mx-auto mb-4 shadow-lg"
              style={{background: '#f74b03', borderColor: '#FFA500'}}>
              <Shield className="w-6 h-6 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-orange-900 mb-2">
              {isLogin ? 'Welcome back' : 'Create your account'}
            </h1>
            <p className="text-orange-700 text-sm">
              {isLogin ? 'Sign in to EvidenceFlow AI' : 'Get started with EvidenceFlow AI'}
            </p>
          </div>

          {/* Toggle */}
          <div className="flex bg-orange-100 rounded-lg p-1 mb-6 shadow-sm">
            <button
              onClick={() => setIsLogin(true)}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition ${
                isLogin
                  ? 'text-white shadow-sm'
                  : 'text-orange-700 hover:text-orange-900'
              }`}
              style={isLogin ? {background: '#f74b03'} : {}}
              onMouseEnter={(e) => { if(isLogin) e.target.style.background = '#cc3c02'; }}
              onMouseLeave={(e) => { if(isLogin) e.target.style.background = '#f74b03'; }}
            >
              Sign in
            </button>
            <button
              onClick={() => setIsLogin(false)}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition ${
                !isLogin
                  ? 'text-white shadow-sm'
                  : 'text-orange-700 hover:text-orange-900'
              }`}
              style={!isLogin ? {background: '#f74b03'} : {}}
              onMouseEnter={(e) => { if(!isLogin) e.target.style.background = '#cc3c02'; }}
              onMouseLeave={(e) => { if(!isLogin) e.target.style.background = '#f74b03'; }}
            >
              Sign up
            </button>
          </div>

          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-orange-200"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-beige-100 text-orange-600">Or continue with email</span>
            </div>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <div>
                <label className="block text-sm font-medium text-orange-900 mb-2">
                  Full name
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-orange-400" />
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    required={!isLogin}
                    className="w-full bg-white border border-orange-300 rounded-lg py-3 pl-10 pr-4 text-orange-900 placeholder-orange-400 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent transition shadow-sm"
                    placeholder="John Doe"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-orange-900 mb-2">
                Email address
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-orange-400" />
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  required
                  className="w-full bg-white border border-orange-300 rounded-lg py-3 pl-10 pr-4 text-orange-900 placeholder-orange-400 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent transition shadow-sm"
                  placeholder="you@example.com"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-orange-900 mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-orange-400" />
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  required
                  className="w-full bg-white border border-orange-300 rounded-lg py-3 pl-10 pr-4 text-orange-900 placeholder-orange-400 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent transition shadow-sm"
                  placeholder="••••••••"
                />
              </div>
            </div>

            {error && (
              <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 text-orange-600 text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full text-white py-3 rounded-lg font-medium transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-lg hover:shadow-xl btn-orange"
              style={{background: '#f74b03', borderColor: '#FFA500'}}
              onMouseEnter={(e) => e.target.style.background = '#cc3c02'}
              onMouseLeave={(e) => e.target.style.background = '#f74b03'}
            >
              {loading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <LogIn className="w-5 h-5" />
                  {isLogin ? 'Sign in' : 'Create account'}
                </>
              )}
            </button>
          </form>

          {/* Google OAuth Button */}
          {googleOAuthEnabled ? (
            <button
              type="button"
              onClick={handleGoogleLogin}
              className="w-full bg-white text-orange-900 py-3 rounded-lg font-medium hover:bg-orange-50 transition flex items-center justify-center gap-3 border border-orange-300 mt-4 shadow-sm hover:shadow-md"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Continue with Google
            </button>
          ) : (
            <div className="mt-4 p-3 bg-orange-50 rounded-lg border border-orange-200 text-center">
              <p className="text-xs text-orange-700">
                <span className="font-medium">Google OAuth not configured</span>
              </p>
              <p className="text-xs text-orange-600 mt-1">
                Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env file to enable Google login
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Login;
