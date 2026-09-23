import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Shield, CheckCircle, XCircle, Loader } from 'lucide-react';
import api, { API_BASE } from './api';
import './Login.css';

function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState('loading'); // loading, success, error
  const [message, setMessage] = useState('');
  const [userInfo, setUserInfo] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const token = searchParams.get('token');
    if (!token) {
      setStatus('error');
      setMessage('No verification token provided');
      return;
    }

    verifyEmail(token);
  }, [searchParams]);

  const verifyEmail = async (token) => {
    try {
      const response = await api.get(`/auth/verify?token=${token}`);
      setStatus('success');
      setUserInfo(response.data);
      setMessage('Email verified successfully!');
    } catch (error) {
      setStatus('error');
      setMessage(error.response?.data?.detail || 'Verification failed');
    }
  };

  const handleLogin = () => {
    navigate('/login');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <div className="max-w-md w-full">
        <div className="bg-white rounded-xl shadow-lg p-8">
          {/* Header */}
          <div className="text-center mb-8">
            {status === 'loading' && (
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Loader className="w-8 h-8 text-blue-600 animate-spin" />
              </div>
            )}
            {status === 'success' && (
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="w-8 h-8 text-green-600" />
              </div>
            )}
            {status === 'error' && (
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <XCircle className="w-8 h-8 text-red-600" />
              </div>
            )}
            
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              {status === 'loading' ? 'Verifying email...' : 
               status === 'success' ? 'Email verified!' : 
               'Verification failed'}
            </h1>
            <p className="text-gray-600 text-sm">
              {status === 'loading' ? 'Please wait while we verify your email address' : message}
            </p>
          </div>

          {/* User Info */}
          {status === 'success' && userInfo && (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6">
              <div className="text-sm text-gray-700 mb-2">
                <strong>Welcome,</strong> {userInfo.name}
              </div>
              <div className="text-sm text-gray-600">
                {userInfo.email}
              </div>
            </div>
          )}

          {/* Action Button */}
          {status !== 'loading' && (
            <button
              onClick={handleLogin}
              className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 transition flex items-center justify-center gap-2"
            >
              <Shield className="w-5 h-5" />
              Go to login
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default VerifyEmail;