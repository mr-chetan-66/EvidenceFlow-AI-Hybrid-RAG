import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Loader } from 'lucide-react';

function OAuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const token = searchParams.get('token');
    const user = searchParams.get('user');

    if (token && user) {
      try {
        localStorage.setItem('token', token);
        // Parse the URL-encoded user JSON
        const decodedUser = decodeURIComponent(user);
        const userObj = JSON.parse(decodedUser);
        localStorage.setItem('user', JSON.stringify(userObj));
        navigate('/');
      } catch (e) {
        console.error('Error storing OAuth data:', e);
        navigate('/login?error=oauth_failed');
      }
    } else {
      navigate('/login?error=no_token');
    }
  }, [searchParams, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <Loader className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
        <p className="text-gray-900 text-lg">Completing sign in...</p>
      </div>
    </div>
  );
}

export default OAuthCallback;