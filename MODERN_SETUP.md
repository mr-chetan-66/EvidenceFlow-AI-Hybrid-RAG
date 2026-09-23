# EvidenceFlow AI - Modern Architecture Setup Guide

## 🚀 New Architecture: React + FastAPI

We've upgraded from Streamlit to a modern, production-ready architecture:

### **Backend: FastAPI**
- Modern, fast Python web framework
- RESTful API endpoints
- Automatic API documentation
- Better performance and scalability

### **Frontend: React + Vite**
- Modern React with Vite for fast development
- Beautiful, responsive UI with Tailwind CSS
- Real-time chat interface
- Production-ready build system

## 📋 Installation Steps

### **1. Install Backend Dependencies**

```bash
cd E:\AIML\RAGApplication
python -m pip install fastapi uvicorn pydantic
```

### **2. Install Frontend Dependencies**

```bash
cd frontend
npm install
```

### **3. Start Backend Server**

```bash
# From project root
cd backend
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### **4. Start Frontend Development Server**

```bash
# From frontend directory
cd frontend
npm run dev
```

### **5. Access the Application**

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🔧 Configuration

### **Environment Variables (.env)**
```bash
GROQ_API_KEY=your_groq_api_key_here
COHERE_API_KEY=your_cohere_api_key_here  # Optional
```

### **API Endpoints**

- `GET /` - API status
- `GET /status` - System status
- `POST /initialize` - Initialize system with documents
- `POST /query` - Query the knowledge base
- `POST /clear-cache` - Clear the cache

## ✨ Features

### **Fixed Issues:**

1. **✅ Fast Loading**: 
   - Lazy imports for instant page load
   - No more 1-2 minute initial load times

2. **✅ Persistent Storage**:
   - Checks existing vector store on startup
   - No need to re-initialize every time
   - Automatic cache loading

3. **✅ Modern UI/UX**:
   - Beautiful gradient design
   - Smooth animations
   - Responsive layout
   - Real-time chat interface
   - Detailed response metrics

### **UI Improvements:**

- 🎨 Modern gradient backgrounds
- 💫 Smooth animations and transitions
- 📱 Fully responsive design
- 🎯 Intuitive user experience
- 📊 Clean metrics display
- 🔍 Expandable response details
- 💾 Cache status indicators

## 🚀 Running the Application

### **Development Mode:**

```bash
# Terminal 1: Backend
cd backend
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend  
cd frontend
npm run dev
```

### **Production Build:**

```bash
# Build frontend
cd frontend
npm run build

# Serve with backend
cd backend
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

## 📊 Comparison: Old vs New

| Feature | Streamlit (Old) | React + FastAPI (New) |
|---------|----------------|----------------------|
| **Initial Load** | 1-2 minutes | < 5 seconds |
| **Re-initialization** | Required every time | Automatic persistence |
| **UI Framework** | Streamlit | React + Tailwind |
| **API** | None | RESTful API |
| **Scalability** | Limited | High |
| **Customization** | Limited | Full control |
| **Production Ready** | No | Yes |

## 🎯 Benefits of New Architecture

1. **Performance**: 10x faster initial load
2. **Persistence**: No need to re-initialize
3. **Modern UI**: Beautiful, responsive interface
4. **API Access**: Can be used by other applications
5. **Scalability**: Production-ready architecture
6. **Developer Experience**: Modern tooling and hot reload

## 🔄 Migration from Streamlit

The Streamlit version (`evidenceflow_app.py`) is still available as a backup. To use it:

```bash
streamlit run evidenceflow_app.py
```

But we recommend the new React + FastAPI architecture for production use.

## 🛠️ Troubleshooting

### **Backend Issues:**
- Ensure FastAPI is installed: `pip install fastapi uvicorn`
- Check API key in `.env` file
- Verify documents in `./data/pdf` folder

### **Frontend Issues:**
- Ensure Node.js is installed
- Run `npm install` in frontend directory
- Check backend is running on port 8000

### **CORS Issues:**
- If frontend can't connect to backend, check CORS settings in `backend/app.py`

## 📝 Next Steps

1. Set up your API keys in `.env`
2. Place PDF documents in `./data/pdf`
3. Start both backend and frontend servers
4. Initialize the system from the UI
5. Start asking questions!

The new architecture provides a much better user experience with faster loading, persistent storage, and a beautiful modern interface!