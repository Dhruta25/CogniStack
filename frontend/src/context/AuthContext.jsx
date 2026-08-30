import React, { createContext, useContext, useState, useEffect } from 'react';
import { loginApi, signupApi, getCurrentUserApi } from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem('token');
      if (storedToken) {
        try {
          const userData = await getCurrentUserApi();
          setUser(userData);
          setToken(storedToken);
        } catch (error) {
          console.error("Failed to load user with token", error);
          logout();
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const login = async (email, password) => {
    const data = await loginApi(email, password);
    localStorage.setItem('token', data.access_token);
    setToken(data.access_token);
    setUser(data.user);
    return data;
  };

  const signup = async (email, username, password) => {
    const userData = await signupApi(email, username, password);
    // Automatically log in after signup
    return await login(email, password);
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
