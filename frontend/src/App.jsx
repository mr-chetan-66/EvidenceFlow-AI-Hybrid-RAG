import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { Send, Database, Zap, Clock, FileText, Sparkles, RefreshCw, Trash2, LogOut, Shield } from 'lucide-react';
import api, { API_BASE } from './api';
import './App.css';
import Login from './Login';
import AdminDashboard from './AdminDashboard';
import VerifyEmail from './VerifyEmail';
import OAuthCallback from './OAuthCallback';

// Protected Route Component
function ProtectedRoute({ children, adminOnly = false }) {
  const token = localStorage.getItem('token');
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const navigate = useNavigate();

  useEffect(() => {
    if (!token) {
      navigate('/login');
      return;
    }

    if (adminOnly && user.role !== 'admin') {
      navigate('/');
      return;
    }
  }, [token, user, navigate, adminOnly]);

  if (!token) {
    return null;
  }

  if (adminOnly && user.role !== 'admin') {
    return null;
  }

  return children;
}

function ChatApp() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [systemStatus, setSystemStatus] = useState({ ready: false, document_count: 0 });
  const [isInitializing, setIsInitializing] = useState(false);
  const [showDetails, setShowDetails] = useState({});
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem('user') || '{}');

  // Check system status on mount
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      checkStatus();
    }
  }, []);

  const checkStatus = async () => {
    try {
      const response = await api.get('/status');
      setSystemStatus(response.data);
    } catch (error) {
      console.error('Status check failed:', error);
    }
  };

  const initializeSystem = async () => {
    setIsInitializing(true);
    try {
      const response = await api.post('/initialize');
      setSystemStatus({
        ready: true,
        document_count: response.data.document_count
      });
      await checkStatus();
    } catch (error) {
      console.error('Initialization failed:', error);
      alert('Failed to initialize system');
    } finally {
      setIsInitializing(false);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await api.post('/query', {
        query: input,
        k: 10,
        alpha: 0.5
      });

      const assistantMessage = {
        role: 'assistant',
        content: response.data.answer,
        metadata: response.data
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Query error:', error);
      const errorMessage = {
        role: 'assistant',
        content: `Error: ${error.response?.data?.detail || error.message || 'Something went wrong. Please try again.'}`,
        error: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleDetails = (index) => {
    setShowDetails(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.7) return 'text-green-400';
    if (confidence >= 0.4) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getConfidenceIcon = (confidence) => {
    if (confidence >= 0.7) return '🟢';
    if (confidence >= 0.4) return '🟡';
    return '🔴';
  };

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* 3D Background Elements */}
      <div className="bg-3d-container">
        <div className="bg-3d-shape bg-3d-shape-1"></div>
        <div className="bg-3d-shape bg-3d-shape-2"></div>
        <div className="bg-3d-shape bg-3d-shape-3"></div>
        <div className="bg-3d-shape bg-3d-shape-4"></div>
        <div className="bg-3d-shape bg-3d-shape-5"></div>
      </div>
      {/* Header */}
      <header className="border-b border-purple-500/20 backdrop-blur-xl bg-black/30 relative z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl flex items-center justify-center shadow-lg shadow-purple-500/30">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">EvidenceFlow AI</h1>
              <p className="text-xs text-purple-200/60">Enterprise Knowledge System</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-4 py-2 bg-purple-900/30 border border-purple-500/20 rounded-lg backdrop-blur-sm">
              <div className={`w-2 h-2 rounded-full ${systemStatus.ready ? 'bg-green-400 shadow-lg shadow-green-400/50' : 'bg-yellow-400 shadow-lg shadow-yellow-400/50'}`} />
              <span className="text-sm text-purple-100">
                {systemStatus.ready ? 'Ready' : 'Not Ready'}
              </span>
            </div>
            
            <div className="flex items-center gap-2 px-4 py-2 bg-purple-900/30 border border-purple-500/20 rounded-lg backdrop-blur-sm">
              <Shield className="w-4 h-4 text-purple-300" />
              <span className="text-sm text-purple-100">{user.name || 'User'}</span>
            </div>
            
            {user.role === 'admin' && (
              <button
                onClick={() => navigate('/admin')}
                className="px-4 py-2 bg-purple-600/20 text-purple-300 border border-purple-500/20 rounded-lg hover:bg-purple-600/30 transition flex items-center gap-2"
              >
                <Shield className="w-4 h-4" />
                Admin Dashboard
              </button>
            )}
            
            <button
              onClick={async () => {
                try {
                  await api.post('/auth/logout');
                } catch (error) {
                  console.error('Logout error:', error);
                } finally {
                  localStorage.removeItem('token');
                  localStorage.removeItem('user');
                  navigate('/login');
                }
              }}
              className="px-4 py-2 bg-red-600/20 text-red-300 border border-red-500/20 rounded-lg hover:bg-red-600/30 transition flex items-center gap-2"
            >
              <LogOut className="w-4 h-4" />
              Logout
            </button>
            
            {user.role === 'admin' && !systemStatus.ready && (
              <button
                onClick={initializeSystem}
                disabled={isInitializing}
                className="px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg hover:opacity-90 transition disabled:opacity-50 flex items-center gap-2 shadow-lg shadow-purple-500/30 border border-purple-400/20"
              >
                {isInitializing ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Initializing...
                  </>
                ) : (
                  <>
                    <Database className="w-4 h-4" />
                    Initialize
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8 relative z-10">
        {!systemStatus.ready ? (
          <div className="text-center py-20">
            <div className="w-24 h-24 bg-purple-900/30 border border-purple-500/20 rounded-full flex items-center justify-center mx-auto mb-6 backdrop-blur-sm animate-float">
              <Database className="w-12 h-12 text-purple-300" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">System Not Ready</h2>
            {user.role === 'admin' ? (
              <>
                <p className="text-purple-200/60 mb-6">Initialize the knowledge base to start asking questions</p>
                <button
                  onClick={initializeSystem}
                  disabled={isInitializing}
                  className="px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-xl hover:opacity-90 transition disabled:opacity-50 flex items-center gap-2 mx-auto shadow-lg shadow-purple-500/30 border border-purple-400/20"
                >
                  {isInitializing ? (
                    <>
                      <RefreshCw className="w-5 h-5 animate-spin" />
                      Initializing...
                    </>
                  ) : (
                    <>
                      <Zap className="w-5 h-5" />
                      Initialize System
                    </>
                  )}
                </button>
              </>
            ) : (
              <p className="text-purple-200/60 mb-6">Please contact an administrator to initialize the system</p>
            )}
          </div>
        ) : (
          <>
            {/* Chat Messages */}
            <div className="space-y-4 mb-24">
              {messages.length === 0 && (
                <div className="text-center py-12">
                  <FileText className="w-16 h-16 text-purple-300/30 mx-auto mb-4 animate-float-slow" />
                  <h3 className="text-lg font-medium text-purple-200/60">Ask about your documents</h3>
                  <p className="text-sm text-purple-200/40">EvidenceFlow AI is ready to help</p>
                </div>
              )}
              
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-2xl rounded-2xl p-4 backdrop-blur-sm ${
                      message.role === 'user'
                        ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-lg shadow-purple-500/30 border border-purple-400/20'
                        : 'bg-black/40 text-white border border-purple-500/20'
                    }`}
                  >
                    <p className="text-sm leading-relaxed">{message.content}</p>
                    
                    {message.role === 'assistant' && message.metadata && (
                      <button
                        onClick={() => toggleDetails(index)}
                        className="mt-3 text-xs text-purple-200/60 hover:text-purple-200 flex items-center gap-1"
                      >
                        <Clock className="w-3 h-3" />
                        {showDetails[index] ? 'Hide Details' : 'Show Details'}
                      </button>
                    )}
                    
                    {message.role === 'assistant' && showDetails[index] && message.metadata && (
                      <div className="mt-4 pt-4 border-t border-purple-500/20 space-y-3">
                        <div className="grid grid-cols-3 gap-3">
                          <div className="bg-purple-900/30 border border-purple-500/20 rounded-lg p-3 backdrop-blur-sm">
                            <div className="text-xs text-purple-200/60 mb-1">Confidence</div>
                            <div className={`font-bold ${getConfidenceColor(message.metadata.confidence)}`}>
                              {getConfidenceIcon(message.metadata.confidence)} {message.metadata.confidence.toFixed(2)}
                            </div>
                          </div>
                          <div className="bg-purple-900/30 border border-purple-500/20 rounded-lg p-3 backdrop-blur-sm">
                            <div className="text-xs text-purple-200/60 mb-1">Cache</div>
                            <div className="font-bold">
                              {message.metadata.cache_hit === 'miss' ? '❌ Miss' : '✅ Hit'}
                            </div>
                          </div>
                          <div className="bg-purple-900/30 border border-purple-500/20 rounded-lg p-3 backdrop-blur-sm">
                            <div className="text-xs text-purple-200/60 mb-1">Iterations</div>
                            <div className="font-bold">{message.metadata.iterations}</div>
                          </div>
                        </div>
                        
                        {message.metadata.citations && message.metadata.citations.length > 0 && (
                          <div>
                            <div className="text-xs text-purple-200/60 mb-2">Top Sources</div>
                            <div className="space-y-2">
                              {message.metadata.citations.slice(0, 3).map((citation, i) => (
                                <div key={i} className="bg-purple-900/30 border border-purple-500/20 rounded-lg p-2 text-xs backdrop-blur-sm">
                                  <div className="font-medium">{citation.source || 'Unknown'}</div>
                                  <div className="text-purple-200/60">
                                    {citation.page !== 'N/A' && citation.page !== 0 ? `Page ${citation.page}` : 'Page information not available'}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-black/40 border border-purple-500/20 rounded-2xl p-4 backdrop-blur-sm">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-purple-300 rounded-full animate-bounce" />
                      <div className="w-2 h-2 bg-purple-300 rounded-full animate-bounce delay-100" />
                      <div className="w-2 h-2 bg-purple-300 rounded-full animate-bounce delay-200" />
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Input Area */}
            <div className="fixed bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 via-black/60 to-transparent pt-6 pb-6 backdrop-blur-sm">
              <div className="max-w-3xl mx-auto px-4">
                <div className="flex items-center gap-3 bg-black/40 backdrop-blur-xl rounded-2xl p-2 border border-purple-500/20 shadow-lg">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                    placeholder="Ask about your documents..."
                    className="flex-1 bg-transparent text-white placeholder-purple-200/40 px-4 py-2 outline-none"
                    disabled={isLoading}
                  />
                  <button
                    onClick={sendMessage}
                    disabled={isLoading || !input.trim()}
                    className="w-10 h-10 bg-gradient-to-r from-purple-600 to-pink-600 rounded-xl flex items-center justify-center hover:opacity-90 transition disabled:opacity-50 shadow-lg shadow-purple-500/30 border border-purple-400/20"
                  >
                    <Send className="w-5 h-5 text-white" />
                  </button>
                </div>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/verify" element={<VerifyEmail />} />
        <Route path="/oauth-callback" element={<OAuthCallback />} />
        <Route 
          path="/" 
          element={
            <ProtectedRoute>
              <ChatApp />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/admin" 
          element={
            <ProtectedRoute adminOnly={true}>
              <AdminDashboard />
            </ProtectedRoute>
          } 
        />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
