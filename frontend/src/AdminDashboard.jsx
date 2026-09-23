import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Shield, 
  FileText, 
  Trash2, 
  RefreshCw, 
  Upload, 
  LogOut, 
  Users, 
  Database,
  Activity,
  HardDrive,
  UserPlus,
  UserMinus,
  Edit,
  Moon,
  Sun,
  Settings
} from 'lucide-react';
import api, { API_BASE } from './api';
import './AdminDashboard.css';
import { applyThemePreference, loadPreferences, savePreferences } from './preferences';

function AdminDashboard() {
  const [documents, setDocuments] = useState([]);
  const [systemStatus, setSystemStatus] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [reindexing, setReindexing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [showUserModal, setShowUserModal] = useState(false);
  const [userFormData, setUserFormData] = useState({
    email: '',
    name: '',
    password: '',
    role: 'user'
  });
  const [createdUserInfo, setCreatedUserInfo] = useState(null);
  const [theme, setTheme] = useState(() => loadPreferences().theme);
  const navigate = useNavigate();

  const currentUser = JSON.parse(localStorage.getItem('user') || '{}');

  useEffect(() => {
    if (currentUser.role !== 'admin') {
      navigate('/');
      return;
    }
    fetchDocuments();
    fetchSystemStatus();
    fetchUsers();
    
    applyThemePreference(theme);
    savePreferences({ theme });
  }, [theme]);

  const fetchDocuments = async () => {
    try {
      const response = await api.get('/admin/documents');
      setDocuments(response.data.documents);
    } catch (error) {
      console.error('Failed to fetch documents:', error);
    }
  };

  const fetchSystemStatus = async () => {
    try {
      const response = await api.get('/status');
      setSystemStatus(response.data);
    } catch (error) {
      console.error('Failed to fetch system status:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchUsers = async () => {
    try {
      const response = await api.get('/admin/users');
      setUsers(response.data.users);
    } catch (error) {
      console.error('Failed to fetch users:', error);
    }
  };

  const handleDeleteDocument = async (filename) => {
    if (!confirm(`Are you sure you want to delete ${filename}?`)) return;

    try {
      await api.delete(`/admin/documents/${filename}`);
      fetchDocuments();
    } catch (error) {
      alert('Failed to delete document');
    }
  };

  const handleReindex = async () => {
    if (!confirm('This will clear all existing data and rebuild the index. Continue?')) return;

    setReindexing(true);
    try {
      const response = await api.post('/admin/reindex');
      alert(`Reindex completed: ${response.data.document_count} documents, ${response.data.chunk_count} chunks`);
      fetchSystemStatus();
    } catch (error) {
      alert('Reindex failed');
    } finally {
      setReindexing(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      await api.post('/admin/upload', formData, {
        headers: { 
          'Content-Type': 'multipart/form-data'
        }
      });
      alert('File uploaded successfully');
      fetchDocuments();
    } catch (error) {
      alert('File upload failed');
    } finally {
      setUploading(false);
    }
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

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      const response = await api.post('/admin/users', userFormData);
      setShowUserModal(false);
      setUserFormData({ email: '', name: '', password: '', role: 'user' });
      fetchUsers();
      
      // Show verification info for admin users
      if (userFormData.role === 'admin') {
        setCreatedUserInfo(response.data);
      } else {
        alert('User created successfully');
      }
    } catch (error) {
      alert('Failed to create user: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!confirm('Are you sure you want to delete this user?')) return;

    try {
      await api.delete(`/admin/users/${userId}`);
      fetchUsers();
      alert('User deleted successfully');
    } catch (error) {
      alert('Failed to delete user: ' + (error.response?.data?.detail || error.message));
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-orange-50 bg-beige-paper">
        <div className="text-orange-900 text-xl">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-orange-50 bg-beige-paper">
      {/* Header */}
      <header className="border-b border-orange-200 backdrop-blur-xl bg-beige-100/90 shadow-md shadow-orange-500/10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center shadow-lg"
              style={{background: '#f74b03', borderColor: '#f74b03'}}>
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-orange-900">Admin Dashboard</h1>
              <p className="text-xs text-orange-700">EvidenceFlow AI Management</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-4 py-2 bg-orange-100 border border-orange-300 rounded-lg backdrop-blur-sm">
              <Shield className="w-4 h-4 text-orange-600" />
              <span className="text-sm text-orange-800">{currentUser.name || 'Admin'}</span>
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
              <Settings className="w-5 h-5 text-orange-800" />
            </button>
            
            <button
              onClick={() => navigate('/')}
              className="px-4 py-2 bg-orange-200 text-orange-800 border border-orange-300 rounded-lg hover:bg-orange-300 transition flex items-center gap-2"
            >
              <Database className="w-4 h-4" />
              Back to Chat
            </button>
            <button
              onClick={handleLogout}
              className="px-4 py-2 bg-orange-200 text-orange-800 border border-orange-300 rounded-lg hover:bg-orange-300 transition flex items-center gap-2"
            >
              <LogOut className="w-4 h-4" />
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* System Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-beige-100 backdrop-blur-sm rounded-xl p-6 border border-orange-300">
            <div className="flex items-center justify-between mb-4">
              <Database className="w-8 h-8 text-orange-600" />
              <span className={`px-2 py-1 rounded-full text-xs ${systemStatus?.ready ? 'bg-green-500/20 text-green-600' : 'bg-orange-500/20 text-orange-600'}`}>
                {systemStatus?.ready ? 'Ready' : 'Not Ready'}
              </span>
            </div>
            <div className="text-2xl font-bold text-orange-900">{systemStatus?.document_count || 0}</div>
            <div className="text-sm text-orange-700">Documents</div>
          </div>

          <div className="bg-beige-100 backdrop-blur-sm rounded-xl p-6 border border-orange-300">
            <div className="flex items-center justify-between mb-4">
              <FileText className="w-8 h-8 text-orange-600" />
              <span className="px-2 py-1 rounded-full text-xs bg-orange-500/20 text-orange-600">
                Chunks
              </span>
            </div>
            <div className="text-2xl font-bold text-orange-900">{systemStatus?.chunk_count || 0}</div>
            <div className="text-sm text-orange-700">Text Chunks</div>
          </div>

          <div className="bg-beige-100 backdrop-blur-sm rounded-xl p-6 border border-orange-300">
            <div className="flex items-center justify-between mb-4">
              <Activity className="w-8 h-8 text-orange-600" />
              <span className="px-2 py-1 rounded-full text-xs bg-orange-500/20 text-orange-600">
                Cache
              </span>
            </div>
            <div className="text-2xl font-bold text-orange-900">{systemStatus?.cache_stats?.total_cached_queries || 0}</div>
            <div className="text-sm text-orange-700">Cached Queries</div>
          </div>

          <div className="bg-beige-100 backdrop-blur-sm rounded-xl p-6 border border-orange-300">
            <div className="flex items-center justify-between mb-4">
              <HardDrive className="w-8 h-8 text-orange-600" />
              <span className="px-2 py-1 rounded-full text-xs bg-orange-500/20 text-orange-600">
                Storage
              </span>
            </div>
            <div className="text-2xl font-bold text-orange-900">{formatFileSize(systemStatus?.cache_stats?.cache_file_size || 0)}</div>
            <div className="text-sm text-orange-700">Cache Size</div>
          </div>
        </div>

        {/* Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          <div className="bg-beige-100 backdrop-blur-sm rounded-xl p-6 border border-orange-300">
            <h3 className="text-lg font-semibold text-orange-900 mb-4 flex items-center gap-2">
              <Upload className="w-5 h-5 text-orange-600" />
              Upload Document
            </h3>
            <div className="flex items-center gap-4">
              <input
                type="file"
                accept=".pdf"
                onChange={handleFileUpload}
                disabled={uploading}
                className="flex-1 text-sm text-orange-700"
              />
              {uploading && (
                <div className="w-5 h-5 border-2 border-orange-400 border-t-transparent rounded-full animate-spin" />
              )}
            </div>
          </div>

          <div className="bg-beige-100 backdrop-blur-sm rounded-xl p-6 border border-orange-300">
            <h3 className="text-lg font-semibold text-orange-900 mb-4 flex items-center gap-2">
              <RefreshCw className="w-5 h-5 text-orange-600" />
              Reindex System
            </h3>
            <p className="text-sm text-orange-700 mb-4">
              Clear all data and rebuild the search index from uploaded documents
            </p>
            <button
              onClick={handleReindex}
              disabled={reindexing}
              className="px-4 py-2 text-white rounded-lg transition disabled:opacity-50 flex items-center gap-2"
              style={{background: '#f74b03'}}
              onMouseEnter={(e) => e.target.style.background = '#cc3c02'}
              onMouseLeave={(e) => e.target.style.background = '#f74b03'}
            >
              {reindexing ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Reindexing...
                </>
              ) : (
                <>
                  <RefreshCw className="w-4 h-4" />
                  Reindex All Documents
                </>
              )}
            </button>
          </div>
        </div>

        {/* Documents List */}
        <div className="bg-beige-100 backdrop-blur-sm rounded-xl border border-orange-300">
          <div className="p-6 border-b border-orange-300">
            <h3 className="text-lg font-semibold text-orange-900 flex items-center gap-2">
              <FileText className="w-5 h-5 text-orange-600" />
              Uploaded Documents ({documents.length})
            </h3>
          </div>
          
          {documents.length === 0 ? (
            <div className="p-12 text-center">
              <FileText className="w-16 h-16 text-orange-300 mx-auto mb-4" />
              <p className="text-orange-600">No documents uploaded yet</p>
            </div>
          ) : (
            <div className="divide-y divide-orange-200">
              {documents.map((doc, index) => (
                <div key={index} className="p-4 flex items-center justify-between hover:bg-orange-200 transition">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                      <FileText className="w-5 h-5 text-orange-600" />
                    </div>
                    <div>
                      <div className="text-orange-900 font-medium">{doc.filename}</div>
                      <div className="text-sm text-orange-600">{formatFileSize(doc.size)}</div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDeleteDocument(doc.filename)}
                    className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg transition"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* User Management */}
        <div className="bg-beige-100 backdrop-blur-sm rounded-xl border border-orange-300 dashboard-card-beige">
          <div className="p-6 border-b border-orange-300 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-orange-900 flex items-center gap-2">
              <Users className="w-5 h-5 text-orange-600" />
              User Management ({users.length})
            </h3>
            <button
              onClick={() => setShowUserModal(true)}
              className="px-4 py-2 text-white rounded-lg transition flex items-center gap-2 text-sm shadow-lg"
              style={{background: '#f74b03', borderColor: '#f74b03'}}
              onMouseEnter={(e) => e.target.style.background = '#cc3c02'}
              onMouseLeave={(e) => e.target.style.background = '#f74b03'}
            >
              <UserPlus className="w-4 h-4" />
              Add User
            </button>
          </div>
          
          {users.length === 0 ? (
            <div className="p-12 text-center">
              <Users className="w-16 h-16 text-orange-300 mx-auto mb-4" />
              <p className="text-orange-600">No users found</p>
            </div>
          ) : (
            <div className="divide-y divide-orange-200">
              {users.map((userItem) => (
                <div key={userItem.id} className="p-4 flex items-center justify-between hover:bg-orange-200 transition">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                      <Users className="w-5 h-5 text-orange-600" />
                    </div>
                    <div>
                      <div className="text-orange-900 font-medium">{userItem.name}</div>
                      <div className="text-sm text-orange-600">{userItem.email}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      userItem.role === 'admin' 
                        ? 'bg-orange-500/20 text-orange-600' 
                        : 'bg-blue-500/20 text-blue-600'
                    }`}>
                      {userItem.role}
                    </span>
                    {userItem.role === 'admin' && (
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        userItem.is_verified 
                          ? 'bg-green-500/20 text-green-600' 
                          : 'bg-yellow-500/20 text-yellow-600'
                      }`}>
                        {userItem.is_verified ? 'Verified' : 'Pending'}
                      </span>
                    )}
                    {userItem.id !== currentUser.id && (
                      <button
                        onClick={() => handleDeleteUser(userItem.id)}
                        className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg transition"
                      >
                        <UserMinus className="w-5 h-5" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* User Creation Modal */}
      {showUserModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-beige-100 backdrop-blur-xl rounded-2xl p-8 border border-orange-300 shadow-2xl max-w-md w-full mx-4 login-card">
            <h3 className="text-xl font-bold text-orange-900 mb-6 flex items-center gap-2">
              <UserPlus className="w-5 h-5 text-orange-600" />
              Create New User
            </h3>
            <form onSubmit={handleCreateUser} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-orange-900 mb-2">
                  Full Name
                </label>
                <input
                  type="text"
                  value={userFormData.name}
                  onChange={(e) => setUserFormData({...userFormData, name: e.target.value})}
                  required
                  className="w-full bg-white border border-orange-300 rounded-lg py-3 px-4 text-orange-900 placeholder-orange-400 focus:outline-none focus:border-orange-500 transition shadow-sm"
                  placeholder="John Doe"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-orange-900 mb-2">
                  Email Address
                </label>
                <input
                  type="email"
                  value={userFormData.email}
                  onChange={(e) => setUserFormData({...userFormData, email: e.target.value})}
                  required
                  className="w-full bg-white border border-orange-300 rounded-lg py-3 px-4 text-orange-900 placeholder-orange-400 focus:outline-none focus:border-orange-500 transition shadow-sm"
                  placeholder="you@example.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-orange-900 mb-2">
                  Password
                </label>
                <input
                  type="password"
                  value={userFormData.password}
                  onChange={(e) => setUserFormData({...userFormData, password: e.target.value})}
                  required
                  className="w-full bg-white border border-orange-300 rounded-lg py-3 px-4 text-orange-900 placeholder-orange-400 focus:outline-none focus:border-orange-500 transition shadow-sm"
                  placeholder="••••••••"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-orange-900 mb-2">
                  Role
                </label>
                <select
                  value={userFormData.role}
                  onChange={(e) => setUserFormData({...userFormData, role: e.target.value})}
                  className="w-full bg-white border border-orange-300 rounded-lg py-3 px-4 text-orange-900 focus:outline-none focus:border-orange-500 transition appearance-none cursor-pointer shadow-sm"
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowUserModal(false);
                    setUserFormData({ email: '', name: '', password: '', role: 'user' });
                  }}
                  className="flex-1 px-4 py-2 bg-orange-200 text-orange-800 border border-orange-300 rounded-lg hover:bg-orange-300 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 text-white rounded-lg transition flex items-center justify-center gap-2 shadow-lg"
                  style={{background: '#f74b03', borderColor: '#f74b03'}}
                  onMouseEnter={(e) => e.target.style.background = '#cc3c02'}
                  onMouseLeave={(e) => e.target.style.background = '#f74b03'}
                >
                  <UserPlus className="w-4 h-4" />
                  Create User
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Verification Info Modal */}
      {createdUserInfo && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-beige-100 backdrop-blur-xl rounded-2xl p-8 border border-orange-300 shadow-2xl max-w-md w-full mx-4 login-card">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-gradient-to-br from-yellow-500 to-orange-500 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg shadow-orange-500/30">
                <Shield className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-xl font-bold text-orange-900 mb-2">Admin User Created</h3>
              <p className="text-orange-600 text-sm">Email verification required</p>
            </div>
            
            <div className="bg-orange-100 border border-orange-300 rounded-lg p-4 mb-6">
              <p className="text-sm text-orange-900 mb-2">
                <strong>Email:</strong> {createdUserInfo.email}
              </p>
              <p className="text-sm text-orange-900 mb-2">
                <strong>Name:</strong> {createdUserInfo.name}
              </p>
              <p className="text-sm text-orange-900 mb-4">
                <strong>Status:</strong> <span className="text-orange-600">Pending Verification</span>
              </p>
              
              <div className="border-t border-orange-300 pt-4 mt-4">
                <p className="text-xs text-orange-700 mb-2">Verification Token (for demo):</p>
                <code className="text-xs bg-orange-200 px-2 py-1 rounded block break-all text-orange-900">
                  {createdUserInfo.verification_token}
                </code>
              </div>
              
              <div className="border-t border-orange-300 pt-4 mt-4">
                <p className="text-xs text-orange-700 mb-2">Verification URL:</p>
                <a 
                  href={createdUserInfo.verification_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs bg-orange-200 px-2 py-1 rounded block break-all text-orange-900 hover:text-orange-700"
                >
                  {createdUserInfo.verification_url}
                </a>
              </div>
            </div>
            
            <div className="text-xs text-orange-600 mb-4">
              <p>In production, this would be sent via email. For demo purposes, copy the URL to verify the account.</p>
            </div>
            
            <button
              onClick={() => setCreatedUserInfo(null)}
              className="w-full px-4 py-2 text-white rounded-lg transition shadow-lg"
              style={{background: '#f74b03', borderColor: '#f74b03'}}
              onMouseEnter={(e) => e.target.style.background = '#cc3c02'}
              onMouseLeave={(e) => e.target.style.background = '#f74b03'}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default AdminDashboard;
