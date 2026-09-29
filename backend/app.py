"""
FastAPI Backend for EvidenceFlow AI
Production-ready REST API for the RAG system with Authentication
"""
from __future__ import annotations

import asyncio
import threading
from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sys
import os
import sqlite3
import json
import shutil
from datetime import datetime, timedelta
import secrets
import hashlib
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request
from dotenv import load_dotenv
import sqlalchemy
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.load_and_chunk import process_all_pdfs, chunk_documnents
from src.embedding import EmbeddingManager
from src.vectorstore import VectorStore
from src.hybrid_retrieval import HybridRetriever
from src.agentic_retrieval import AgenticRetrieval
from src.cag_cache import CAGCache
from src.storage_paths import get_pdf_directory

app = FastAPI(title="EvidenceFlow AI", version="2.0.0")

# Security
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
SECRET_KEY = secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_OAUTH_ENABLED = GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")

if GOOGLE_OAUTH_ENABLED:
    oauth = OAuth()
    oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        },
        redirect_uri='http://localhost:8001/auth/google/callback'
    )

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Global instances (will be initialized on startup)
embedding_manager = None
vectorstore = None
hybrid_retriever = None
agentic_retrieval = None
cache = None
system_ready = False
rag_initialization_task = None
rag_rebuild_lock = asyncio.Lock()
background_indexing_task = None
indexing_status_lock = threading.Lock()
indexing_status = {
    "active": False,
    "operation": None,
    "stage": "idle",
    "progress": 0,
    "logs": [],
    "started_at": None,
    "updated_at": None,
    "error": None,
}


def start_indexing_operation(operation):
    global indexing_status
    timestamp = datetime.now().strftime("%H:%M:%S")
    with indexing_status_lock:
        if indexing_status["active"]:
            return False
        indexing_status = {
            "active": True,
            "operation": operation,
            "stage": "starting",
            "progress": 0,
            "logs": [{"time": timestamp, "message": f"{operation} started"}],
            "started_at": timestamp,
            "updated_at": timestamp,
            "error": None,
        }
    return True


def report_indexing_progress(stage, message, progress):
    timestamp = datetime.now().strftime("%H:%M:%S")
    with indexing_status_lock:
        indexing_status["stage"] = stage
        indexing_status["progress"] = progress
        indexing_status["updated_at"] = timestamp
        indexing_status["logs"] = (indexing_status["logs"] + [
            {"time": timestamp, "message": message}
        ])[-80:]


def finish_indexing_operation(result=None, error=None):
    timestamp = datetime.now().strftime("%H:%M:%S")
    with indexing_status_lock:
        succeeded = error is None
        if not succeeded:
            message = f"Failed: {error}"
        elif "cleared_vector_count" in result:
            message = f"Cleared {result['cleared_vector_count']} vectors; source PDFs and accounts preserved"
        else:
            message = f"Completed: {result['document_count']} documents, {result['chunk_count']} chunks"
        indexing_status["active"] = False
        indexing_status["stage"] = "complete" if succeeded else "failed"
        indexing_status["progress"] = 100 if succeeded else indexing_status["progress"]
        indexing_status["updated_at"] = timestamp
        indexing_status["error"] = str(error) if error is not None else None
        indexing_status["logs"] = (indexing_status["logs"] + [
            {"time": timestamp, "message": message}
        ])[-80:]


def get_indexing_status_snapshot():
    with indexing_status_lock:
        return {**indexing_status, "logs": list(indexing_status["logs"])}

# PostgreSQL support
postgres_engine = None
User_model = None

# Database setup - supports both SQLite (local) and PostgreSQL (Render)
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]

def init_db():
    """Initialize database for users - supports SQLite and PostgreSQL"""
    if DATABASE_URL and DATABASE_URL.startswith("postgres"):
        # PostgreSQL for production
        import sqlalchemy
        from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, text
        from sqlalchemy.ext.declarative import declarative_base
        from sqlalchemy.orm import sessionmaker
        
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        Base = declarative_base()
        
        class User(Base):
            __tablename__ = "users"
            id = Column(Integer, primary_key=True, index=True)
            email = Column(String, unique=True, index=True, nullable=False)
            name = Column(String, nullable=False)
            password_hash = Column(String, nullable=False)
            role = Column(String, default="user", nullable=False)
            is_verified = Column(Boolean, default=False)
            verification_token = Column(String, nullable=True)
            created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
        
        Base.metadata.create_all(bind=engine)
        
        # Create default admin user
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            admin = session.query(User).filter(User.role == "admin").first()
            if not admin:
                admin_password = hashlib.sha256("admin123".encode()).hexdigest()
                admin_user = User(
                    email="admin@evidenceflow.ai",
                    name="Admin User",
                    password_hash=admin_password,
                    role="admin",
                    is_verified=True
                )
                session.add(admin_user)
                session.commit()
                print("Default admin user created: admin@evidenceflow.ai / admin123")
            else:
                admin.is_verified = True
                session.commit()
                print("Ensured admin user is verified")
        finally:
            session.close()
            
        # Store engine globally for later use
        global postgres_engine
        postgres_engine = engine
        global User_model
        User_model = User
        
    else:
        # SQLite for local development
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                is_verified BOOLEAN DEFAULT 0,
                verification_token TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'is_verified' not in columns:
            cursor.execute('ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 0')
            print("Added is_verified column to existing users table")
        
        cursor.execute('SELECT * FROM users WHERE role = "admin"')
        if not cursor.fetchone():
            admin_password = hashlib.sha256("admin123".encode()).hexdigest()
            cursor.execute(
                'INSERT INTO users (email, name, password_hash, role, is_verified) VALUES (?, ?, ?, ?, ?)',
                ('admin@evidenceflow.ai', 'Admin User', admin_password, 'admin', 1)
            )
            print("Default admin user created: admin@evidenceflow.ai / admin123")
        else:
            cursor.execute('UPDATE users SET is_verified = 1 WHERE role = "admin"')
            print("Ensured admin user is verified")
        
        conn.commit()
        conn.close()

def get_db_connection():
    """Get database connection - supports both SQLite and PostgreSQL"""
    if DATABASE_URL and DATABASE_URL.startswith("postgres"):
        Session = sessionmaker(bind=postgres_engine)
        return Session()
    else:
        conn = sqlite3.connect('users.db')
        conn.row_factory = sqlite3.Row
        return conn

# Simple token storage with persistence (in production, use Redis or proper JWT)
token_store = {}

def save_token_store():
    """Save token store to disk for persistence"""
    try:
        import json
        with open('token_store.json', 'w') as f:
            json.dump(token_store, f)
    except Exception as e:
        print(f"Failed to save token store: {e}")

def cleanup_old_tokens():
    """Remove tokens older than 24 hours (simple cleanup)"""
    import time
    current_time = time.time()
    tokens_to_remove = []
    
    for token, user_data in token_store.items():
        # Remove tokens older than 24 hours (86400 seconds)
        if current_time - user_data.get('created_at_timestamp', current_time) > 86400:
            tokens_to_remove.append(token)
    
    for token in tokens_to_remove:
        del token_store[token]
    
    if tokens_to_remove:
        print(f"Cleaned up {len(tokens_to_remove)} old tokens")
        save_token_store()

def load_token_store():
    """Load token store from disk"""
    global token_store
    try:
        import json
        with open('token_store.json', 'r') as f:
            token_store = json.load(f)
        print(f"Loaded {len(token_store)} tokens from storage")
    except FileNotFoundError:
        print("No existing token store found, starting fresh")
        token_store = {}
    except Exception as e:
        print(f"Failed to load token store: {e}")
        token_store = {}

def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current user from token"""
    if token not in token_store:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_data = token_store[token]
    # Add is_verified if not present
    if 'is_verified' not in user_data:
        user_data['is_verified'] = True
    return User(**user_data)

def require_admin(current_user: User = Depends(get_current_user)):
    """Require admin role"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

def create_access_token(user: User):
    """Create access token"""
    import time
    token = secrets.token_urlsafe(32)
    user_dict = user.dict()
    # Ensure is_verified is included
    if 'is_verified' not in user_dict:
        user_dict['is_verified'] = user.is_verified if hasattr(user, 'is_verified') else True
    # Add timestamp for cleanup
    user_dict['created_at_timestamp'] = time.time()
    token_store[token] = user_dict
    save_token_store()  # Persist token store
    return token


# Pydantic models for API
class QueryRequest(BaseModel):
    query: str
    k: int = 10
    alpha: float = 0.5


class User(BaseModel):
    id: int
    email: str
    name: str
    role: str  # "admin" or "user"
    is_verified: bool = False
    created_at: str


class UserCreate(BaseModel):
    email: str
    name: str
    password: str
    role: str = "user"  # Default to user


class UserLogin(BaseModel):
    email: str
    password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: User


class DocumentUpload(BaseModel):
    filename: str
    content: str  # Base64 encoded file content


class QueryResponse(BaseModel):
    answer: str
    confidence: float
    cache_hit: str
    iterations: int
    evidence_count: int
    evidence_grade: Dict[str, Any]
    citations: List[Dict[str, Any]]


class SystemStatus(BaseModel):
    ready: bool
    document_count: int
    chunk_count: int
    cache_stats: Dict[str, Any]


@app.on_event("startup")
async def startup_event():
    """Fast startup — bind the port immediately, load heavy stuff in the background"""
    global system_ready, rag_initialization_task

    print("Starting EvidenceFlow AI backend...")

    # Load existing tokens for persistence
    load_token_store()

    # Clean up old tokens
    cleanup_old_tokens()

    # Initialize database
    init_db()

    system_ready = False

    # Don't block startup on model/vectorstore loading (this is what was
    # stalling Uvicorn long enough for Render's port scan to time out).
    # Kick it off in the background instead so the port opens right away.
    rag_initialization_task = asyncio.create_task(initialize_rag_system())


async def initialize_rag_system():
    """Loads the embedding model + vector store without blocking Uvicorn's startup"""
    global embedding_manager, vectorstore, hybrid_retriever, agentic_retrieval, cache, system_ready

    try:
        loop = asyncio.get_event_loop()

        def _load():
            em = EmbeddingManager()
            vs = VectorStore()
            return em, vs

        # Run the actual heavy/blocking initialization in a thread so it
        # doesn't freeze the event loop
        embedding_manager, vectorstore = await loop.run_in_executor(None, _load)

        # Check if we have existing data - if yes, load without reinitializing
        if vectorstore.collection.count() > 0:
            print("Loading from existing vector store (skipping reinitialization)...")
            hybrid_retriever = HybridRetriever(embedding_manager, vectorstore)

            # Try to rebuild BM25 index from existing data
            try:
                existing_data = vectorstore.collection.get(limit=100)
                if existing_data and 'documents' in existing_data:
                    texts = existing_data['documents']
                    hybrid_retriever.index_documents(texts)
            except:
                pass

            agentic_retrieval = AgenticRetrieval(
                hybrid_retriever,
                max_iterations=2,
                enable_reranking=True,
                enable_citation_check=False
            )
            cache = CAGCache(embedding_manager=embedding_manager)
            system_ready = True
            print("System ready from cache! No reinitialization needed.")
        else:
            print("No existing data found. System needs initialization.")
            system_ready = False

    except Exception as e:
        print(f"Background initialization failed: {e}")
        import traceback
        traceback.print_exc()
        system_ready = False


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "EvidenceFlow AI API",
        "version": "1.0.0",
        "status": "ready" if system_ready else "needs_initialization",
        "google_oauth_enabled": bool(GOOGLE_OAUTH_ENABLED)
    }


@app.get("/status", response_model=SystemStatus)
async def get_status(current_user: User = Depends(get_current_user)):
    """Get system status (requires authentication)"""
    if not system_ready:
        return SystemStatus(
            ready=False,
            document_count=0,
            chunk_count=0,
            cache_stats={"enabled": False}
        )
    
    try:
        doc_count = vectorstore.collection.count()
        cache_stats = cache.get_stats() if cache else {"enabled": False}
        
        return SystemStatus(
            ready=True,
            document_count=doc_count,
            chunk_count=doc_count,  # Approximate
            cache_stats=cache_stats
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/initialize")
async def initialize_system(current_user: User = Depends(require_admin)):
    """Initialize or recover the embedding and retrieval system from stored PDFs."""
    return schedule_indexing_operation("reinitialize")


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest, current_user: User = Depends(get_current_user)):
    """Query the system (requires authentication)"""
    if not system_ready:
        raise HTTPException(status_code=400, detail="System not initialized")
    
    try:
        print(f"Processing query from {current_user.email}: {request.query}")
        result = agentic_retrieval.retrieve_and_answer(
            request.query,
            k=request.k,
            alpha=request.alpha
        )
        print(f"Query result: {result.keys()}")
        
        return QueryResponse(
            answer=result['answer'],
            confidence=result['confidence'],
            cache_hit=result['cache_hit'],
            iterations=result['iterations'],
            evidence_count=len(result['evidence']),
            evidence_grade=result['evidence_grade'],
            citations=result['citation_verification'].get('citations', [])
        )
        
    except Exception as e:
        print(f"Query error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/clear-cache")
async def clear_cache():
    """Clear the cache"""
    if cache:
        cache.invalidate()
        return {"message": "Cache cleared"}
    return {"message": "No cache to clear"}


# ============================================================
# AUTHENTICATION ENDPOINTS
# ============================================================

@app.post("/auth/register", response_model=User)
async def register(user_data: UserCreate):
    """Register a new user"""
    conn = get_db_connection()
    
    try:
        if DATABASE_URL and DATABASE_URL.startswith("postgres"):
            # PostgreSQL query
            from sqlalchemy import text
            existing_user = conn.execute(text("SELECT * FROM users WHERE email = :email"), {"email": user_data.email}).fetchone()
            if existing_user:
                conn.close()
                raise HTTPException(status_code=400, detail="Email already registered")
            
            password_hash = hashlib.sha256(user_data.password.encode()).hexdigest()
            
            new_user = User_model(
                email=user_data.email,
                name=user_data.name,
                password_hash=password_hash,
                role=user_data.role,
                is_verified=True
            )
            conn.add(new_user)
            conn.commit()
            
            user = conn.execute(text("SELECT * FROM users WHERE email = :email"), {"email": user_data.email}).fetchone()
            conn.close()
            
            return User(id=user.id, email=user.email, name=user.name, role=user.role, is_verified=True, created_at=str(user.created_at))
        else:
            # SQLite query
            existing_user = conn.execute('SELECT * FROM users WHERE email = ?', (user_data.email,)).fetchone()
            if existing_user:
                conn.close()
                raise HTTPException(status_code=400, detail="Email already registered")
            
            password_hash = hashlib.sha256(user_data.password.encode()).hexdigest()
            
            cursor = conn.execute(
                'INSERT INTO users (email, name, password_hash, role, is_verified) VALUES (?, ?, ?, ?, ?)',
                (user_data.email, user_data.name, password_hash, user_data.role, 1)
            )
            conn.commit()
            
            user = conn.execute('SELECT * FROM users WHERE id = ?', (cursor.lastrowid,)).fetchone()
            conn.close()
            
            user_dict = dict(user)
            return User(id=user_dict['id'], email=user_dict['email'], name=user_dict['name'], role=user_dict['role'], is_verified=True, created_at=user_dict['created_at'])
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth/login", response_model=Token)
async def login(login_data: UserLogin):
    """Login user and return token"""
    conn = get_db_connection()
    
    try:
        if DATABASE_URL and DATABASE_URL.startswith("postgres"):
            # PostgreSQL query
            from sqlalchemy import text
            user = conn.execute(text("SELECT * FROM users WHERE email = :email"), {"email": login_data.email}).fetchone()
            conn.close()
            
            if not user:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            password_hash = hashlib.sha256(login_data.password.encode()).hexdigest()
            if user.password_hash != password_hash:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            is_verified = user.is_verified if hasattr(user, 'is_verified') else True
            if user.role == 'admin' and user.email != 'admin@evidenceflow.ai' and not is_verified:
                raise HTTPException(status_code=403, detail="Admin account requires email verification")
            
            user_obj = User(
                id=user.id,
                email=user.email,
                name=user.name,
                role=user.role,
                is_verified=is_verified,
                created_at=str(user.created_at)
            )
            token = create_access_token(user_obj)
            
            return Token(access_token=token, token_type="bearer", user=user_obj)
        else:
            # SQLite query
            user = conn.execute('SELECT * FROM users WHERE email = ?', (login_data.email,)).fetchone()
            conn.close()
            
            if not user:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            password_hash = hashlib.sha256(login_data.password.encode()).hexdigest()
            if user['password_hash'] != password_hash:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            user_dict = dict(user)
            is_verified = user_dict.get('is_verified', True)
            if user_dict['role'] == 'admin' and user_dict['email'] != 'admin@evidenceflow.ai' and not is_verified:
                raise HTTPException(status_code=403, detail="Admin account requires email verification")
            
            user_obj = User(
                id=user_dict['id'],
                email=user_dict['email'],
                name=user_dict['name'],
                role=user_dict['role'],
                is_verified=is_verified,
                created_at=user_dict['created_at']
            )
            token = create_access_token(user_obj)
            
            return Token(access_token=token, token_type="bearer", user=user_obj)
    except HTTPException:
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return current_user


@app.post("/auth/change-password")
async def change_password(password_data: PasswordChange, current_user: User = Depends(get_current_user)):
    """Change the authenticated user's password"""
    if len(password_data.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

    conn = get_db_connection()
    try:
        if DATABASE_URL and DATABASE_URL.startswith("postgres"):
            from sqlalchemy import text

            result = conn.execute(
                text("SELECT password_hash FROM users WHERE id = :user_id"),
                {"user_id": current_user.id},
            ).fetchone()
            password_hash = result.password_hash if result else None
        else:
            result = conn.execute(
                "SELECT password_hash FROM users WHERE id = ?",
                (current_user.id,),
            ).fetchone()
            password_hash = result["password_hash"] if result else None

        if password_hash != hashlib.sha256(password_data.current_password.encode()).hexdigest():
            raise HTTPException(status_code=400, detail="Current password is incorrect")

        new_password_hash = hashlib.sha256(password_data.new_password.encode()).hexdigest()
        if DATABASE_URL and DATABASE_URL.startswith("postgres"):
            conn.execute(
                text("UPDATE users SET password_hash = :password_hash WHERE id = :user_id"),
                {"password_hash": new_password_hash, "user_id": current_user.id},
            )
        else:
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (new_password_hash, current_user.id),
            )
        conn.commit()
        return {"message": "Password changed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/auth/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout user and invalidate token"""
    # Get the token from the Authorization header
    # This is a simple implementation - in production you'd want to extract the token properly
    # For now, we'll clear all tokens for this user
    tokens_to_remove = []
    for token, user_data in token_store.items():
        if user_data.get('email') == current_user.email:
            tokens_to_remove.append(token)
    
    for token in tokens_to_remove:
        del token_store[token]
    
    save_token_store()  # Persist changes
    return {"message": "Logged out successfully"}

# ============================================================
# GOOGLE OAUTH ENDPOINTS
# ============================================================

@app.get("/auth/google")
async def google_login(request: Request):
    """Initiate Google OAuth login"""
    if not GOOGLE_OAUTH_ENABLED:
        raise HTTPException(status_code=501, detail="Google OAuth is not configured")
    
    redirect_uri = request.url_for('google_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth/google/callback")
async def google_callback(request: Request):
    """Handle Google OAuth callback"""
    if not GOOGLE_OAUTH_ENABLED:
        raise HTTPException(status_code=501, detail="Google OAuth is not configured")
    
    try:
        token = await oauth.google.authorize_access_token(request)
        
        # Get user info from the token directly
        user_info = token.get('userinfo')
        if not user_info:
            # Fallback to id_token if userinfo is not available
            id_token = token.get('id_token')
            if id_token:
                # Parse id_token to get user info
                import jwt
                try:
                    # Decode the JWT token (without verification for simplicity in this case)
                    decoded = jwt.decode(id_token, options={"verify_signature": False})
                    user_info = decoded
                except:
                    pass
        
        if not user_info:
            raise HTTPException(status_code=400, detail="Could not get user information from Google")
        
        # Extract user information
        email = user_info.get('email')
        name = user_info.get('name', email.split('@')[0]) if email else 'User'
        
        if not email:
            raise HTTPException(status_code=400, detail="Could not get email from Google")
        
        # Check if user exists
        conn = get_db_connection()
        
        try:
            if DATABASE_URL and DATABASE_URL.startswith("postgres"):
                # PostgreSQL query
                from sqlalchemy import text
                existing_user = conn.execute(text("SELECT * FROM users WHERE email = :email"), {"email": email}).fetchone()
                
                if existing_user:
                    # User exists, log them in
                    user_obj = User(
                        id=existing_user.id,
                        email=existing_user.email,
                        name=existing_user.name,
                        role=existing_user.role,
                        is_verified=existing_user.is_verified if hasattr(existing_user, 'is_verified') else True,
                        created_at=str(existing_user.created_at)
                    )
                    conn.close()
                    access_token = create_access_token(user_obj)
                    
                    # Redirect to frontend with token in URL
                    from fastapi.responses import RedirectResponse
                    import urllib.parse
                    user_json = json.dumps(user_obj.model_dump())
                    encoded_user = urllib.parse.quote(user_json)
                    return RedirectResponse(
                        url=f"{FRONTEND_URL}/oauth-callback?token={access_token}&user={encoded_user}"
                    )
                else:
                    # Create new user as normal user (auto-verified)
                    password_hash = hashlib.sha256(secrets.token_urlsafe(32).encode()).hexdigest()
                    new_user = User_model(
                        email=email,
                        name=name,
                        password_hash=password_hash,
                        role='user',
                        is_verified=True
                    )
                    conn.add(new_user)
                    conn.commit()
                    
                    created_user = conn.execute(text("SELECT * FROM users WHERE email = :email"), {"email": email}).fetchone()
                    conn.close()
                    
                    user_obj = User(
                        id=created_user.id,
                        email=created_user.email,
                        name=created_user.name,
                        role=created_user.role,
                        is_verified=True,
                        created_at=str(created_user.created_at)
                    )
                    access_token = create_access_token(user_obj)
                    
                    # Redirect to frontend with token in URL
                    from fastapi.responses import RedirectResponse
                    import urllib.parse
                    user_json = json.dumps(user_obj.model_dump())
                    encoded_user = urllib.parse.quote(user_json)
                    return RedirectResponse(
                        url=f"{FRONTEND_URL}/oauth-callback?token={access_token}&user={encoded_user}"
                    )
            else:
                # SQLite query
                existing_user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
                
                if existing_user:
                    # User exists, log them in
                    existing_user_dict = dict(existing_user)
                    user_obj = User(
                        id=existing_user_dict['id'],
                        email=existing_user_dict['email'],
                        name=existing_user_dict['name'],
                        role=existing_user_dict['role'],
                        is_verified=existing_user_dict.get('is_verified', True),
                        created_at=existing_user_dict['created_at']
                    )
                    conn.close()
                    access_token = create_access_token(user_obj)
                    
                    # Redirect to frontend with token in URL
                    from fastapi.responses import RedirectResponse
                    import urllib.parse
                    user_json = json.dumps(user_obj.model_dump())
                    encoded_user = urllib.parse.quote(user_json)
                    return RedirectResponse(
                        url=f"{FRONTEND_URL}/oauth-callback?token={access_token}&user={encoded_user}"
                    )
                else:
                    # Create new user as normal user (auto-verified)
                    password_hash = hashlib.sha256(secrets.token_urlsafe(32).encode()).hexdigest()
                    cursor = conn.execute(
                        'INSERT INTO users (email, name, password_hash, role, is_verified) VALUES (?, ?, ?, ?, ?)',
                        (email, name, password_hash, 'user', 1)
                    )
                    conn.commit()
                    
                    # Get created user
                    new_user = conn.execute('SELECT * FROM users WHERE id = ?', (cursor.lastrowid,)).fetchone()
                    conn.close()
                    
                    new_user_dict = dict(new_user)
                    user_obj = User(
                        id=new_user_dict['id'],
                        email=new_user_dict['email'],
                        name=new_user_dict['name'],
                        role=new_user_dict['role'],
                        is_verified=new_user_dict.get('is_verified', True),
                        created_at=new_user_dict['created_at']
                    )
                    access_token = create_access_token(user_obj)
                    
                    # Redirect to frontend with token in URL
                    from fastapi.responses import RedirectResponse
                    import urllib.parse
                    user_json = json.dumps(user_obj.model_dump())
                    encoded_user = urllib.parse.quote(user_json)
                    return RedirectResponse(
                        url=f"{FRONTEND_URL}/oauth-callback?token={access_token}&user={encoded_user}"
                    )
        except Exception as e:
            conn.close()
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ADMIN ENDPOINTS
# ============================================================

@app.get("/admin/documents")
async def list_documents(current_user: User = Depends(require_admin)):
    """List all documents in the system"""
    try:
        from pathlib import Path
        
        pdf_dir = get_pdf_directory()
        
        documents = []
        if pdf_dir.exists():
            for pdf_file in pdf_dir.iterdir():
                if not pdf_file.is_file() or pdf_file.suffix.lower() != ".pdf":
                    continue
                stat = pdf_file.stat()
                documents.append({
                    "filename": pdf_file.name,
                    "size": stat.st_size,
                    "created": stat.st_ctime
                })
        
        return {"documents": documents, "total": len(documents)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/documents/{filename}")
async def delete_document(filename: str, current_user: User = Depends(require_admin)):
    """Delete a document"""
    try:
        from pathlib import Path

        pdf_dir = get_pdf_directory()
        safe_filename = Path(filename).name
        if safe_filename != filename or Path(filename).suffix.lower() != ".pdf":
            raise HTTPException(status_code=400, detail="Invalid PDF filename")

        file_path = pdf_dir / safe_filename
        if file_path.exists():
            file_path.unlink()
            return {"message": f"Document {filename} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def rebuild_document_index(operation="reindex"):
    """Rebuild retrieval state from PDFs in the project's persistent data directory."""
    global embedding_manager, vectorstore, hybrid_retriever, agentic_retrieval, cache, system_ready
    from pathlib import Path

    pdf_dir = get_pdf_directory()

    report_indexing_progress("loading_pdfs", "Loading uploaded PDF documents", 12)
    all_documents = process_all_pdfs(str(pdf_dir))
    report_indexing_progress(
        "chunking_documents",
        f"Loaded {len(all_documents)} pages; splitting into text chunks",
        25,
    )
    all_chunks = chunk_documnents(all_documents)
    texts = [doc.page_content for doc in all_chunks]

    if operation == "reinitialize" or embedding_manager is None:
        report_indexing_progress("loading_model", "Loading the embedding model", 35)
        embedding_manager = EmbeddingManager()
    if vectorstore is None:
        report_indexing_progress("opening_vector_store", "Opening the vector store", 42)
        vectorstore = VectorStore()

    report_indexing_progress(
        "generating_embeddings",
        f"Generating embeddings for {len(texts)} chunks",
        55,
    )
    last_embedding_progress = 55

    def report_embedding_batch(completed_batches, total_batches):
        nonlocal last_embedding_progress
        progress = 55 + int(20 * completed_batches / total_batches)
        if progress >= last_embedding_progress + 2 or completed_batches == total_batches:
            report_indexing_progress(
                "generating_embeddings",
                f"Embedded batch {completed_batches} of {total_batches}",
                progress,
            )
            last_embedding_progress = progress

    embeddings = (
        embedding_manager.genetate_embedding(texts, progress_callback=report_embedding_batch)
        if texts else []
    )
    system_ready = False
    report_indexing_progress("rebuilding_vector_store", "Replacing the vector index", 76)
    vectorstore.client.delete_collection(name=vectorstore.collection_name)
    vectorstore.collection = vectorstore.client.get_or_create_collection(
        name=vectorstore.collection_name,
        metadata={"description": "PDF documents RAG vector"},
    )

    if texts:
        vectorstore.add_documents(all_chunks, embeddings)

    report_indexing_progress("building_retriever", "Building keyword and vector retrievers", 90)
    hybrid_retriever = HybridRetriever(embedding_manager, vectorstore)
    if texts:
        hybrid_retriever.index_documents(texts)
    agentic_retrieval = AgenticRetrieval(
        hybrid_retriever,
        max_iterations=2,
        enable_reranking=True,
        enable_citation_check=False,
    )
    if cache:
        cache.invalidate()
    cache = CAGCache(embedding_manager=embedding_manager)
    system_ready = bool(texts)
    if system_ready:
        report_indexing_progress("ready", "Embedding system is ready", 98)
    else:
        report_indexing_progress("no_documents", "No text chunks found; system remains not ready", 98)
    return {"document_count": len(all_documents), "chunk_count": len(all_chunks)}


def clear_vector_index():
    global vectorstore, hybrid_retriever, agentic_retrieval, cache, system_ready
    system_ready = False
    report_indexing_progress("opening_vector_store", "Opening persistent vector storage", 25)
    if vectorstore is None:
        vectorstore = VectorStore()

    existing_vectors = vectorstore.collection.count()
    report_indexing_progress("clearing_vectors", f"Removing {existing_vectors} stored vectors", 60)
    vectorstore.client.delete_collection(name=vectorstore.collection_name)
    vectorstore.collection = vectorstore.client.get_or_create_collection(
        name=vectorstore.collection_name,
        metadata={"description": "PDF documents RAG vector"},
    )
    hybrid_retriever = None
    agentic_retrieval = None
    if cache:
        cache.invalidate()
    report_indexing_progress(
        "vectors_cleared",
        "Vector embeddings and retrieval cache cleared; source PDFs and accounts preserved",
        95,
    )
    return {"document_count": 0, "chunk_count": 0, "cleared_vector_count": existing_vectors}


async def wait_for_rag_initialization():
    if rag_initialization_task is not None:
        await rag_initialization_task


async def run_tracked_rebuild(operation):
    async with rag_rebuild_lock:
        try:
            if rag_initialization_task is not None and not rag_initialization_task.done():
                report_indexing_progress("waiting_for_startup", "Waiting for startup model initialization", 3)
            await wait_for_rag_initialization()
            if operation == "clear_vectors":
                result = await asyncio.to_thread(clear_vector_index)
            else:
                result = await asyncio.to_thread(rebuild_document_index, operation)
        except Exception as error:
            finish_indexing_operation(error=error)
            return
        finish_indexing_operation(result=result)


def schedule_indexing_operation(operation):
    global background_indexing_task
    if not start_indexing_operation(operation):
        raise HTTPException(status_code=409, detail="An indexing operation is already running")
    background_indexing_task = asyncio.create_task(run_tracked_rebuild(operation))
    return {"accepted": True, "message": f"{operation} started", "operation": operation}


@app.get("/admin/indexing-status")
async def get_admin_indexing_status(current_user: User = Depends(require_admin)):
    """Return the current indexing operation and its recent progress messages."""
    return get_indexing_status_snapshot()


@app.post("/admin/upload")
async def upload_document(
    files: Optional[List[UploadFile]] = File(None),
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(require_admin),
):
    """Save selected PDFs and rebuild embeddings once for the complete collection."""
    from pathlib import Path

    selected_files = list(files or [])
    if file is not None:
        selected_files.append(file)
    if not selected_files:
        raise HTTPException(status_code=400, detail="Select at least one PDF to upload")

    pdf_dir = get_pdf_directory()
    saved_filenames = []
    try:
        for uploaded_file in selected_files:
            filename = Path(uploaded_file.filename or "").name
            if not filename or Path(filename).suffix.lower() != ".pdf":
                raise HTTPException(status_code=400, detail="Only PDF files can be uploaded")
            saved_filenames.append(filename)

        if not start_indexing_operation("upload"):
            raise HTTPException(status_code=409, detail="An indexing operation is already running")
        try:
            for index, (uploaded_file, filename) in enumerate(zip(selected_files, saved_filenames)):
                report_indexing_progress(
                    "saving_uploads",
                    f"Saving {filename}",
                    5 + int(8 * (index + 1) / len(selected_files)),
                )
                with (pdf_dir / filename).open("wb") as buffer:
                    shutil.copyfileobj(uploaded_file.file, buffer)
        except Exception as error:
            finish_indexing_operation(error=error)
            raise
        global background_indexing_task
        background_indexing_task = asyncio.create_task(run_tracked_rebuild("upload"))
        return {
            "accepted": True,
            "message": "Documents saved; embedding job started",
            "uploaded_files": saved_filenames,
            "operation": "upload",
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/users")
async def list_users(current_user: User = Depends(require_admin)):
    """List all users (admin only)"""
    try:
        conn = get_db_connection()
        if DATABASE_URL and DATABASE_URL.startswith("postgres"):
            from sqlalchemy import text
            users = conn.execute(text(
                'SELECT id, email, name, role, is_verified, created_at FROM users ORDER BY id'
            )).mappings().all()
        else:
            users = conn.execute(
                'SELECT id, email, name, role, is_verified, created_at FROM users ORDER BY id'
            ).fetchall()
        conn.close()
        
        return {
            "users": [
                {
                    "id": user['id'],
                    "email": user['email'],
                    "name": user['name'],
                    "role": user['role'],
                    "is_verified": user['is_verified'],
                    "created_at": user['created_at']
                }
                for user in users
            ],
            "total": len(users)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/users")
async def create_user(user_data: UserCreate, current_user: User = Depends(require_admin)):
    """Create a new user (admin only)"""
    try:
        conn = get_db_connection()

        # Hash password
        password_hash = hashlib.sha256(user_data.password.encode()).hexdigest()

        # Generate verification token for admin users
        verification_token = None
        is_verified = True  # Auto-verify normal users

        if user_data.role == 'admin':
            verification_token = secrets.token_urlsafe(32)
            is_verified = False  # Admins need verification

        if DATABASE_URL and DATABASE_URL.startswith("postgres"):
            existing_user = conn.query(User_model).filter(User_model.email == user_data.email).first()
            if existing_user:
                conn.close()
                raise HTTPException(status_code=400, detail="Email already registered")

            user = User_model(
                email=user_data.email,
                name=user_data.name,
                password_hash=password_hash,
                role=user_data.role,
                is_verified=is_verified,
                verification_token=verification_token,
            )
            conn.add(user)
            conn.commit()
            conn.refresh(user)
            response_data = {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "is_verified": user.is_verified,
                "created_at": user.created_at,
            }
            conn.close()
        else:
            existing_user = conn.execute('SELECT * FROM users WHERE email = ?', (user_data.email,)).fetchone()
            if existing_user:
                conn.close()
                raise HTTPException(status_code=400, detail="Email already registered")

            cursor = conn.execute(
                'INSERT INTO users (email, name, password_hash, role, is_verified, verification_token) VALUES (?, ?, ?, ?, ?, ?)',
                (user_data.email, user_data.name, password_hash, user_data.role, is_verified, verification_token)
            )
            conn.commit()
            user = conn.execute('SELECT * FROM users WHERE id = ?', (cursor.lastrowid,)).fetchone()
            conn.close()
            response_data = {
                "id": user['id'],
                "email": user['email'],
                "name": user['name'],
                "role": user['role'],
                "is_verified": user['is_verified'],
                "created_at": user['created_at'],
            }
        
        # Include verification token for admin users (for demo purposes)
        if user_data.role == 'admin' and verification_token:
            response_data["verification_token"] = verification_token
            response_data["verification_url"] = f"http://localhost:3001/verify?token={verification_token}"
        
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/users/{user_id}")
async def delete_user(user_id: int, current_user: User = Depends(require_admin)):
    """Delete a user (admin only)"""
    try:
        conn = get_db_connection()
        
        if DATABASE_URL and DATABASE_URL.startswith("postgres"):
            from sqlalchemy import text
            user = conn.execute(
                text('SELECT * FROM users WHERE id = :user_id'), {'user_id': user_id}
            ).mappings().first()
        else:
            user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user:
            conn.close()
            raise HTTPException(status_code=404, detail="User not found")
        
        # Prevent deleting the last admin
        if user['role'] == 'admin':
            if DATABASE_URL and DATABASE_URL.startswith("postgres"):
                admin_count = conn.execute(
                    text('SELECT COUNT(*) FROM users WHERE role = :role'), {'role': 'admin'}
                ).scalar_one()
            else:
                admin_count = conn.execute('SELECT COUNT(*) as count FROM users WHERE role = "admin"').fetchone()['count']
            if admin_count <= 1:
                conn.close()
                raise HTTPException(status_code=400, detail="Cannot delete the last admin user")
        
        # Delete user
        if DATABASE_URL and DATABASE_URL.startswith("postgres"):
            from sqlalchemy import text
            conn.execute(text('DELETE FROM users WHERE id = :user_id'), {'user_id': user_id})
        else:
            conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
        
        return {"message": f"User {user_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/auth/verify")
async def verify_email(token: str):
    """Verify email with token"""
    try:
        conn = get_db_connection()
        
        if DATABASE_URL and DATABASE_URL.startswith("postgres"):
            from sqlalchemy import text
            user = conn.execute(
                text('SELECT * FROM users WHERE verification_token = :token'),
                {'token': token},
            ).mappings().first()
        else:
            user = conn.execute(
                'SELECT * FROM users WHERE verification_token = ?', (token,)
            ).fetchone()
        
        if not user:
            conn.close()
            raise HTTPException(status_code=404, detail="Invalid or expired verification token")
        
        if DATABASE_URL and DATABASE_URL.startswith("postgres"):
            conn.execute(
                text('UPDATE users SET is_verified = TRUE, verification_token = NULL WHERE id = :user_id'),
                {'user_id': user['id']},
            )
        else:
            conn.execute(
                'UPDATE users SET is_verified = 1, verification_token = NULL WHERE id = ?',
                (user['id'],)
            )
        conn.commit()
        conn.close()
        
        return {
            "message": "Email verified successfully",
            "email": user['email'],
            "name": user['name']
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/reindex")
async def reindex_documents(current_user: User = Depends(require_admin)):
    """Reindex all documents (clear and rebuild vector store)"""
    return schedule_indexing_operation("reindex")


@app.post("/admin/clear-vector-data")
async def clear_vector_data(current_user: User = Depends(require_admin)):
    """Clear embeddings and vector index while preserving PDFs and user accounts."""
    return schedule_indexing_operation("clear_vectors")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)