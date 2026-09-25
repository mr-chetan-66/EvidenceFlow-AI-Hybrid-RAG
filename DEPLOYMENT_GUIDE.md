# EvidenceFlow AI - Render Deployment Guide

This guide will help you deploy your EvidenceFlow AI application to Render for free.

## 📋 Prerequisites

- GitHub account with your EvidenceFlow AI repository
- Render account (free tier)
- Groq API key (required)
- Cohere API key (optional, for reranking)
- Google OAuth credentials (optional)

## 🚀 Deployment Steps

### 1. Prepare Your Repository

1. **Ensure all files are committed to GitHub:**
   ```bash
   git add .
   git commit -m "Prepare for Render deployment"
   git push
   ```

2. **Verify your `.gitignore` includes:**
   - `.env` files
   - `users.db` (SQLite database)
   - `token_store.json`
   - `data/vector_store/` (ChromaDB)
   - `data/cag_cache/` (cache files)
   - `frontend/node_modules/`

### 2. Set Up Render Account

1. Go to [render.com](https://render.com) and sign up
2. Connect your GitHub account
3. Verify your email address

### 3. Deploy PostgreSQL Database

1. In Render dashboard, click **"New +"** → **"PostgreSQL"**
2. Configure:
   - **Name**: `evidenceflow-db`
   - **Database**: `evidenceflow`
   - **User**: `evidenceflow_user`
   - **Region**: Choose nearest region
   - **Plan**: Free
3. Click **"Create Database"**
4. Wait for database to be ready (~2-3 minutes)
5. Copy the **Internal Database URL** from the database dashboard

### 4. Deploy Backend Service

1. In Render dashboard, click **"New +"** → **"Web Service"**
2. Connect your GitHub repository
3. Configure:
   - **Name**: `evidenceflow-backend`
   - **Region**: Same as database
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements_render.txt`
   - **Start Command**: `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free

4. **Add Environment Variables:**
   - `DATABASE_URL`: (paste your PostgreSQL Internal Database URL)
   - `GROQ_API_KEY`: (your Groq API key)
   - `COHERE_API_KEY`: (your Cohere API key, optional)
   - `GOOGLE_CLIENT_ID`: (optional, for Google OAuth)
   - `GOOGLE_CLIENT_SECRET`: (optional, for Google OAuth)
   - `FRONTEND_URL`: `https://evidenceflow-frontend.onrender.com` (will update after frontend deployment)
   - `PORT`: `8001`

5. **Add Disk Storage (Important for ChromaDB):**
   - Scroll to **"Advanced"** → **"Disk"**
   - **Name**: `data`
   - **Mount Path**: `/opt/render/project/data`
   - **Size**: `1 GB`
   - Click **"Add"**

6. Click **"Create Web Service"**
7. Wait for deployment (~5-10 minutes)
8. Copy the backend URL: `https://evidenceflow-backend.onrender.com`

### 5. Deploy Frontend Service

1. In Render dashboard, click **"New +"** → **"Web Service"**
2. Connect your GitHub repository
3. Configure:
   - **Name**: `evidenceflow-frontend`
   - **Region**: Same as backend
   - **Branch**: `main`
   - **Runtime**: `Node`
   - **Build Command**: `cd frontend && npm install && npm run build`
   - **Start Command**: `cd frontend && npm run preview`
   - **Plan**: Free

4. **Add Environment Variables:**
   - `VITE_API_URL`: `https://evidenceflow-backend.onrender.com`

5. Click **"Create Web Service"**
6. Wait for deployment (~3-5 minutes)
7. Copy the frontend URL: `https://evidenceflow-frontend.onrender.com`

### 6. Update Backend CORS Settings

1. Go back to your backend service in Render
2. Click **"Environment"** tab
3. Update `FRONTEND_URL` to your actual frontend URL
4. Click **"Save Changes"**
5. Wait for redeployment

### 7. Initialize the System

1. Once both services are running, open your frontend URL
2. Login with default admin credentials:
   - Email: `admin@evidenceflow.ai`
   - Password: `admin123`
3. Go to **Settings** or **Admin Dashboard**
4. Click **"Initialize System"** to process your PDF documents
5. Wait for initialization to complete

## 🔧 Troubleshooting

### Backend Won't Start
- Check Render logs for errors
- Verify environment variables are set correctly
- Ensure PostgreSQL database is running
- Check that disk storage is properly mounted

### Frontend Can't Connect to Backend
- Verify `VITE_API_URL` is correct
- Check backend CORS settings
- Ensure both services are in the same region
- Check backend logs for connection errors

### Database Issues
- Verify `DATABASE_URL` is correct
- Check PostgreSQL database status
- Ensure database connection isn't timing out

### ChromaDB Issues
- Verify disk storage is mounted at `/opt/render/project/data`
- Check disk space (1GB should be sufficient for most use cases)
- Review vector store initialization logs

## 📊 Monitoring

### View Logs
- **Backend**: Render Dashboard → evidenceflow-backend → Logs
- **Frontend**: Render Dashboard → evidenceflow-frontend → Logs
- **Database**: Render Dashboard → evidenceflow-db → Metrics

### Performance
- Free tier limitations:
  - Backend: 512MB RAM, shared CPU
  - Frontend: 512MB RAM, shared CPU
  - Database: 1GB storage, 90 days of inactivity limit

### Scaling
If you need more resources:
- Upgrade to paid tiers ($7/month for basic, $25/month for standard)
- Consider using Redis for token storage instead of file-based
- Use external vector database (Pinecone, Weaviate) for larger datasets

## 🔒 Security

### Environment Variables
- Never commit `.env` files to GitHub
- Use Render's environment variable management
- Rotate API keys regularly
- Use strong passwords for database

### Authentication
- Default admin password should be changed immediately
- Enable HTTPS (automatic on Render)
- Consider implementing rate limiting
- Use secure token storage (upgrade to Redis for production)

## 🔄 Updates

### To Update Your Application
1. Commit and push changes to GitHub
2. Render will automatically detect and redeploy
3. Monitor logs for any issues
4. Test changes thoroughly

### Database Migrations
- For schema changes, use SQLAlchemy migrations
- Test migrations locally first
- Backup database before major changes
- Use Render's database backup features

## 📝 Notes

- Render free tier services spin down after 15 minutes of inactivity
- First request after spin-down may take longer (~30 seconds)
- Database remains active but connection may need re-establishment
- For production use, consider upgrading to paid tiers

## 🆘 Support

If you encounter issues:
1. Check Render status page: [status.render.com](https://status.render.com)
2. Review Render documentation: [docs.render.com](https://docs.render.com)
3. Check application logs for detailed error messages
4. Verify all environment variables are correctly set

## 🎉 Success!

Your EvidenceFlow AI application is now deployed and accessible via:
- **Frontend**: `https://evidenceflow-frontend.onrender.com`
- **Backend API**: `https://evidenceflow-backend.onrender.com`
- **API Documentation**: `https://evidenceflow-backend.onrender.com/docs`