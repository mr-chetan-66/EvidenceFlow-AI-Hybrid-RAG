import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { Send, Database, Zap, Clock, FileText, Sparkles, RefreshCw, Trash2, LogOut, Shield, MessageSquare, Settings as SettingsIcon, Moon, Sun } from 'lucide-react';
import api, { API_BASE } from './api';
import './App.css';
import Login from './Login';
import AdminDashboard from './AdminDashboard';
import VerifyEmail from './VerifyEmail';
import OAuthCallback from './OAuthCallback';
import SettingsPage from './Settings';
import { applyThemePreference, autoSaveChatsEnabled, loadPreferences, savePreferences } from './preferences';

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
  const [chatHistory, setChatHistory] = useState([]);
  const [currentChatId, setCurrentChatId] = useState(null);
  const [showSidebar, setShowSidebar] = useState(true);
  const [theme, setTheme] = useState(() => loadPreferences().theme);
  const messagesEndRef = React.useRef(null);
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem('user') || '{}');

  // Apply theme on mount and when theme changes
  useEffect(() => {
    applyThemePreference(theme);
    savePreferences({ theme });
  }, [theme]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Load chat history from localStorage on mount
  useEffect(() => {
    const savedHistory = localStorage.getItem('chatHistory');
    if (savedHistory) {
      setChatHistory(JSON.parse(savedHistory));
    }
    
    const savedCurrentChatId = localStorage.getItem('currentChatId');
    if (savedCurrentChatId) {
      setCurrentChatId(savedCurrentChatId);
      const savedMessages = localStorage.getItem(`chat_${savedCurrentChatId}`);
      if (savedMessages) {
        setMessages(JSON.parse(savedMessages));
      }
    }
  }, []);

  // Save chat history to localStorage whenever it changes
  useEffect(() => {
    if (!autoSaveChatsEnabled()) return;
    localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
  }, [chatHistory]);

  // Save current chat messages to localStorage
  useEffect(() => {
    if (!currentChatId || !autoSaveChatsEnabled()) return;

    localStorage.setItem(`chat_${currentChatId}`, JSON.stringify(messages));
    localStorage.setItem('currentChatId', currentChatId);
  }, [messages, currentChatId]);

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

    // Create new chat if no current chat
    if (!currentChatId) {
      const newChatId = Date.now().toString();
      setCurrentChatId(newChatId);
      const newChat = {
        id: newChatId,
        title: input.substring(0, 30) + (input.length > 30 ? '...' : ''),
        timestamp: new Date().toISOString(),
        messages: []
      };
      setChatHistory(prev => [newChat, ...prev]);
    }

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
      
      // Update chat title if this is the first message
      if (messages.length === 0) {
        setChatHistory(prev => prev.map(chat => 
          chat.id === currentChatId 
            ? { ...chat, title: input.substring(0, 30) + (input.length > 30 ? '...' : '') }
            : chat
        ));
      }
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

  const createNewChat = () => {
    setCurrentChatId(null);
    setMessages([]);
  };

  const switchChat = (chatId) => {
    setCurrentChatId(chatId);
    const savedMessages = localStorage.getItem(`chat_${chatId}`);
    if (savedMessages) {
      setMessages(JSON.parse(savedMessages));
    } else {
      setMessages([]);
    }
  };

  const deleteChat = (chatId, e) => {
    e.stopPropagation();
    setChatHistory(prev => prev.filter(chat => chat.id !== chatId));
    localStorage.removeItem(`chat_${chatId}`);
    
    if (currentChatId === chatId) {
      createNewChat();
    }
  };

  const clearAllChats = () => {
    if (window.confirm('Are you sure you want to delete all chat history?')) {
      setChatHistory([]);
      setMessages([]);
      setCurrentChatId(null);
      // Clear all chat data from localStorage
      Object.keys(localStorage).forEach(key => {
        if (key.startsWith('chat_')) {
          localStorage.removeItem(key);
        }
      });
      localStorage.removeItem('chatHistory');
      localStorage.removeItem('currentChatId');
    }
  };

  const toggleDetails = (index) => {
    setShowDetails(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.7) return 'text-green-600';
    if (confidence >= 0.4) return 'text-orange-500';
    return 'text-red-600';
  };

  const getConfidenceIcon = (confidence) => {
    if (confidence >= 0.7) return '🟢';
    if (confidence >= 0.4) return '🟡';
    return '🔴';
  };

  return (
    <div className="chat-shell min-h-screen relative overflow-hidden bg-orange-50 bg-beige-paper flex">
      {/* Sidebar */}
      <div className={`chat-sidebar transition-all duration-300 ${showSidebar ? 'w-64' : 'w-0'} border-r border-orange-200 bg-beige-100/95 backdrop-blur-xl flex flex-col h-screen fixed left-0 top-0 z-20`}>
        <div className="p-4 border-b border-orange-200">
          <button
            onClick={createNewChat}
            className="w-full px-4 py-3 bg-orange-600 text-white rounded-xl transition hover:bg-orange-700 flex items-center justify-center gap-2 shadow-lg shadow-orange-500/30"
            style={{background: '#f74b03'}}
            onMouseEnter={(e) => e.target.style.background = '#cc3c02'}
            onMouseLeave={(e) => e.target.style.background = '#f74b03'}
          >
            <Sparkles className="w-5 h-5" />
            New Chat
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {chatHistory.map(chat => (
            <div
              key={chat.id}
              onClick={() => switchChat(chat.id)}
              className={`p-3 rounded-lg cursor-pointer transition group relative ${
                currentChatId === chat.id 
                  ? 'bg-orange-200 border border-orange-300' 
                  : 'hover:bg-orange-100 border border-transparent'
              }`}
            >
              <div className="flex items-start gap-2">
                <MessageSquare className="w-4 h-4 text-orange-600 mt-0.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-orange-900 truncate">{chat.title}</div>
                  <div className="text-xs text-orange-600 mt-1">
                    {new Date(chat.timestamp).toLocaleDateString()}
                  </div>
                </div>
              </div>
              <button
                onClick={(e) => deleteChat(chat.id, e)}
                className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition p-1 hover:bg-orange-300 rounded"
              >
                <Trash2 className="w-4 h-4 text-orange-600" />
              </button>
            </div>
          ))}
          
          {chatHistory.length === 0 && (
            <div className="text-center text-orange-600 text-sm py-8">
              No chat history yet
            </div>
          )}
        </div>
        
        <div className="p-4 border-t border-orange-200">
          <button
            onClick={clearAllChats}
            className="w-full px-4 py-2 bg-orange-200 text-orange-800 rounded-lg hover:bg-orange-300 transition flex items-center justify-center gap-2 text-sm"
          >
            <Trash2 className="w-4 h-4" />
            Clear All Chats
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className={`flex-1 flex flex-col transition-all duration-300 ${showSidebar ? 'ml-64' : 'ml-0'}`}>
        {/* Header */}
        <header className="chat-header border-b border-orange-200 backdrop-blur-xl bg-beige-100/90 relative z-10 shadow-md shadow-orange-500/10">
          <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowSidebar(!showSidebar)}
                className="p-2 hover:bg-orange-200 rounded-lg transition"
              >
                <div className="w-6 h-6 flex flex-col justify-center gap-1">
                  <div className="w-6 h-0.5 bg-orange-600"></div>
                  <div className="w-6 h-0.5 bg-orange-600"></div>
                  <div className="w-6 h-0.5 bg-orange-600"></div>
                </div>
              </button>
              <div className="w-10 h-10 bg-orange-600 rounded-xl flex items-center justify-center shadow-lg shadow-orange-500/30 border border-orange-400" style={{background: '#f74b03', borderColor: '#f74b03'}}>
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-orange-900">EvidenceFlow AI</h1>
                <p className="text-xs text-orange-700">Enterprise Knowledge System</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 px-4 py-2 bg-orange-100 border border-orange-300 rounded-lg backdrop-blur-sm shadow-sm">
                <div className={`w-2 h-2 rounded-full ${systemStatus.ready ? 'bg-green-500 shadow-lg shadow-green-500/50' : 'bg-orange-400 shadow-lg shadow-orange-400/50'}`} />
                <span className="text-sm text-orange-800">
                  {systemStatus.ready ? 'Ready' : 'Not Ready'}
                </span>
              </div>
              
              <button
                onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
                className="p-2 bg-orange-200 border border-orange-300 rounded-lg hover:bg-orange-300 transition shadow-sm hover:shadow-md"
                title={theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode'}
              >
                {theme === 'light' ? <Moon className="w-5 h-5 text-orange-800" /> : <Sun className="w-5 h-5 text-orange-800" />}
              </button>
              
              <button
                onClick={() => navigate('/settings')}
                className="p-2 bg-orange-200 border border-orange-300 rounded-lg hover:bg-orange-300 transition shadow-sm hover:shadow-md"
                title="Settings"
              >
                <SettingsIcon className="w-5 h-5 text-orange-800" />
              </button>
              
              <div className="flex items-center gap-2 px-4 py-2 bg-orange-100 border border-orange-300 rounded-lg backdrop-blur-sm shadow-sm">
                <Shield className="w-4 h-4 text-orange-600" />
                <span className="text-sm text-orange-800">{user.name || 'User'}</span>
              </div>
              
              {user.role === 'admin' && (
                <button
                  onClick={() => navigate('/admin')}
                  className="px-4 py-2 bg-orange-200 text-orange-800 border border-orange-300 rounded-lg hover:bg-orange-300 transition flex items-center gap-2 shadow-sm hover:shadow-md"
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
                className="px-4 py-2 bg-orange-200 text-orange-800 border border-orange-300 rounded-lg hover:bg-orange-300 transition flex items-center gap-2 shadow-sm hover:shadow-md"
              >
                <LogOut className="w-4 h-4" />
                Logout
              </button>
              
              {user.role === 'admin' && !systemStatus.ready && (
                <button
                  onClick={initializeSystem}
                  disabled={isInitializing}
                  className="px-4 py-2 text-white rounded-lg transition disabled:opacity-50 flex items-center gap-2 shadow-lg"
                  style={{background: '#f74b03', borderColor: '#f74b03'}}
                  onMouseEnter={(e) => e.target.style.background = '#cc3c02'}
                  onMouseLeave={(e) => e.target.style.background = '#f74b03'}
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
        <main className="chat-main flex-1 overflow-y-auto px-4 py-8 relative z-10">
        {!systemStatus.ready ? (
          <div className="text-center py-20">
            <div className="w-24 h-24 bg-orange-100 border border-orange-300 rounded-full flex items-center justify-center mx-auto mb-6 backdrop-blur-sm animate-float shadow-lg shadow-orange-500/20">
              <Database className="w-12 h-12 text-orange-600" />
            </div>
            <h2 className="text-2xl font-bold text-orange-900 mb-2">System Not Ready</h2>
            {user.role === 'admin' ? (
              <>
                <p className="text-orange-700 mb-6">Initialize the knowledge base to start asking questions</p>
                <button
                  onClick={initializeSystem}
                  disabled={isInitializing}
                  className="px-6 py-3 text-white rounded-xl transition disabled:opacity-50 flex items-center gap-2 mx-auto shadow-lg hover:shadow-xl"
                  style={{background: '#f74b03', borderColor: '#f74b03'}}
                  onMouseEnter={(e) => e.target.style.background = '#cc3c02'}
                  onMouseLeave={(e) => e.target.style.background = '#f74b03'}
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
              <p className="text-orange-700 mb-6">Please contact an administrator to initialize the system</p>
            )}
          </div>
        ) : (
          <>
            {/* Chat Messages */}
            <div className="space-y-4 mb-24">
              {messages.length === 0 && (
                <div className="text-center py-12">
                  <FileText className="w-16 h-16 text-orange-300 mx-auto mb-4 animate-float-slow" />
                  <h3 className="text-lg font-medium text-orange-700">Ask about your documents</h3>
                  <p className="text-sm text-orange-600">EvidenceFlow AI is ready to help</p>
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
                        ? 'text-white shadow-lg border'
                        : 'bg-beige-100 text-orange-900 border border-orange-200 shadow-md'
                    }`}
                    style={message.role === 'user' ? {background: '#f74b03', borderColor: '#f74b03'} : {}}
                  >
                    <p className="text-sm leading-relaxed">{message.content}</p>
                    
                    {message.role === 'assistant' && message.metadata && (
                      <button
                        onClick={() => toggleDetails(index)}
                        className="mt-3 text-xs text-orange-600 hover:text-orange-800 flex items-center gap-1"
                      >
                        <Clock className="w-3 h-3" />
                        {showDetails[index] ? 'Hide Details' : 'Show Details'}
                      </button>
                    )}
                    
                    {message.role === 'assistant' && showDetails[index] && message.metadata && (
                      <div className="mt-4 pt-4 border-t border-orange-200 space-y-3">
                        <div className="grid grid-cols-3 gap-3">
                          <div className="bg-orange-100 border border-orange-300 rounded-lg p-3 backdrop-blur-sm">
                            <div className="text-xs text-orange-700 mb-1">Confidence</div>
                            <div className={`font-bold ${getConfidenceColor(message.metadata.confidence)}`}>
                              {getConfidenceIcon(message.metadata.confidence)} {message.metadata.confidence.toFixed(2)}
                            </div>
                          </div>
                          <div className="bg-orange-100 border border-orange-300 rounded-lg p-3 backdrop-blur-sm">
                            <div className="text-xs text-orange-700 mb-1">Cache</div>
                            <div className="font-bold">
                              {message.metadata.cache_hit === 'miss' ? '❌ Miss' : '✅ Hit'}
                            </div>
                          </div>
                          <div className="bg-orange-100 border border-orange-300 rounded-lg p-3 backdrop-blur-sm">
                            <div className="text-xs text-orange-700 mb-1">Iterations</div>
                            <div className="font-bold">{message.metadata.iterations}</div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-orange-100 border border-orange-300 rounded-2xl p-4 backdrop-blur-sm">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-orange-400 rounded-full animate-bounce" />
                      <div className="w-2 h-2 bg-orange-400 rounded-full animate-bounce delay-100" />
                      <div className="w-2 h-2 bg-orange-400 rounded-full animate-bounce delay-200" />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className={`chat-composer fixed bottom-0 bg-gradient-to-t from-orange-50 via-orange-50/90 to-transparent pt-6 pb-6 backdrop-blur-sm transition-all duration-300 ${showSidebar ? 'left-64 right-0' : 'left-0 right-0'}`}>
              <div className="max-w-3xl mx-auto px-4">
                <div className="chat-composer-card flex items-center gap-3 bg-beige-100 backdrop-blur-xl rounded-2xl p-2 border border-orange-300 shadow-lg shadow-orange-500/10">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                    placeholder="Ask about your documents..."
                    className="chat-input flex-1 bg-transparent px-4 py-2 outline-none"
                    disabled={isLoading}
                  />
                  <button
                    onClick={sendMessage}
                    disabled={isLoading || !input.trim()}
                    className="w-10 h-10 rounded-xl flex items-center justify-center transition disabled:opacity-50 shadow-lg"
                    style={{background: '#f74b03', borderColor: '#f74b03'}}
                    onMouseEnter={(e) => e.target.style.background = '#cc3c02'}
                    onMouseLeave={(e) => e.target.style.background = '#f74b03'}
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
        <Route 
          path="/settings" 
          element={
            <ProtectedRoute>
              <SettingsPage />
            </ProtectedRoute>
          } 
        />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
