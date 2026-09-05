import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export const checkHealth = async () => {
  const response = await api.get('/health');
  return response.data;
};

// Auth API
export const signupApi = async (email, username, password) => {
  const response = await api.post('/api/auth/signup', { email, username, password });
  return response.data;
};

export const loginApi = async (email, password) => {
  const response = await api.post('/api/auth/login', { email, password });
  return response.data;
};

export const getCurrentUserApi = async () => {
  const response = await api.get('/api/auth/me');
  return response.data;
};

// Chat API
export const createChatApi = async (title = 'New Chat') => {
  const response = await api.post('/api/chats', { title });
  return response.data;
};

export const getChatsApi = async () => {
  const response = await api.get('/api/chats');
  return response.data;
};

export const getChatMessagesApi = async (chatId) => {
  const response = await api.get(`/api/chats/${chatId}/messages`);
  return response.data;
};

export const sendMessageApi = async (chatId, content) => {
  const response = await api.post(`/api/chats/${chatId}/messages`, { content });
  return response.data;
};

export const streamMessageApi = async (chatId, content, onChunk, onComplete, onError) => {
  const token = localStorage.getItem('token');
  try {
    const response = await fetch(`${API_BASE_URL}/api/chats/${chatId}/messages/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ content })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.chunk) {
              onChunk(data.chunk);
            }
            if (data.done) {
              onComplete(data);
            }
          } catch (e) {
            console.error('Failed to parse SSE data:', e);
          }
        }
      }
    }
  } catch (err) {
    if (onError) onError(err);
  }
};

export const renameChatApi = async (chatId, title) => {
  const response = await api.patch(`/api/chats/${chatId}`, { title });
  return response.data;
};

export const deleteChatApi = async (chatId) => {
  const response = await api.delete(`/api/chats/${chatId}`);
  return response.data;
};

// RAG Applications API
export const createRAGAppApi = async (name) => {
  const response = await api.post('/api/rag-apps', { name });
  return response.data;
};

export const getRAGAppsApi = async () => {
  const response = await api.get('/api/rag-apps');
  return response.data;
};

export const deleteRAGAppApi = async (appId) => {
  const response = await api.delete(`/api/rag-apps/${appId}`);
  return response.data;
};

export const uploadRAGDocApi = async (appId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post(`/api/rag-apps/${appId}/documents/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

export const listRAGDocsApi = async (appId) => {
  const response = await api.get(`/api/rag-apps/${appId}/documents`);
  return response.data;
};

export const deleteRAGDocApi = async (docId) => {
  const response = await api.delete(`/api/documents/${docId}`);
  return response.data;
};

export const reindexRAGAppApi = async (appId) => {
  const response = await api.post(`/api/rag-apps/${appId}/reindex`);
  return response.data;
};

export const chatRAGAppApi = async (appId, question) => {
  const response = await api.post(`/api/rag-apps/${appId}/chat`, { question });
  return response.data;
};

export default api;
