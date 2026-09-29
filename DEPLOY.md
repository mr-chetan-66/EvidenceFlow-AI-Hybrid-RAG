# Deploy EvidenceFlow AI on AWS Without a Domain

This guide deploys the complete application on AWS using only an EC2 instance and Amazon RDS PostgreSQL.

The application will be accessed through the EC2 public IP address. A domain name is not required.

```text
Browser
  |
  | http://EC2_PUBLIC_IP
  v
Nginx on EC2
  |-- React frontend on port 80
  `-- /api/* -> FastAPI backend on 127.0.0.1:8001
                         |
                         `-> Amazon RDS PostgreSQL
```

## Important resource requirement

The backend loads PyTorch, Sentence Transformers, ChromaDB, and FAISS. A 1 GB free-tier EC2 instance is usually too small and can run out of memory.

Use at least:

- EC2 `t3.medium` with 4 GB RAM for testing
- EC2 `t3.large` with 8 GB RAM for a more reliable deployment
- Ubuntu 22.04 or Ubuntu 24.04, x86_64
- At least 30 GB EBS storage

AWS charges depend on the account, region, free-tier eligibility, storage, public IPv4 usage, and database usage. Create an AWS Budget alert before starting.

## 1. Create the RDS PostgreSQL database

In AWS Console:

1. Open **RDS -> Databases -> Create database**.
2. Choose **PostgreSQL**.
3. Select the free-tier option if it is available for your account.
4. Choose the same AWS region that will contain the EC2 instance.
5. Set a database name such as `evidenceflow`.
6. Create a master username and a strong password.
7. For this deployment, keep **Public access** disabled when possible.
8. Create the database.

### RDS security group

Create or use an RDS security group. Add this inbound rule:

```text
Type: PostgreSQL
Port: 5432
Source: EC2 security group
```

Do not allow PostgreSQL port `5432` from `0.0.0.0/0`.

After the database is available, copy its endpoint. It looks similar to:

```text
evidenceflow.xxxxx.us-east-1.rds.amazonaws.com
```

The database URL used by this project should use the installed `psycopg2` driver:

```env
DATABASE_URL=postgresql+psycopg2://DB_USER:DB_PASSWORD@RDS_ENDPOINT:5432/evidenceflow
```

If the database password contains characters such as `@`, `:`, `/`, `?`, or `#`, URL-encode the password first.

## 2. Create the EC2 instance

In AWS Console:

1. Open **EC2 -> Instances -> Launch instance**.
2. Select Ubuntu 22.04 or Ubuntu 24.04.
3. Select `t3.medium` or larger.
4. Allocate at least 30 GB of gp3 EBS storage.
5. Create or select an SSH key pair.
6. Launch the instance.
7. Allocate and attach an Elastic IP address if possible. This keeps the public IP stable after a stop/start.

### EC2 security group

Add these inbound rules:

```text
SSH 22       Source: My IP only
HTTP 80      Source: 0.0.0.0/0
HTTPS 443    Source: 0.0.0.0/0 (optional; not used without a domain)
```

Do not expose port `8001` publicly. Nginx will proxy requests to the backend locally.

## 3. Connect to EC2

From a local terminal or AWS Instance Connect, connect as `ubuntu`:

```bash
ssh -i "your-key.pem" ubuntu@EC2_PUBLIC_IP
```

Update the system and install required packages:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip python3-dev build-essential nginx git nodejs npm
```

Check the installed versions:

```bash
python3 --version
node --version
npm --version
```

## 4. Download the project

```bash
cd ~
git clone https://github.com/mr-chetan-66/EvidenceFlow-AI-Hybrid-RAG.git
cd ~/EvidenceFlow-AI-Hybrid-RAG
```

For future updates:

```bash
cd ~/EvidenceFlow-AI-Hybrid-RAG
git pull origin main
```

## 5. Install backend dependencies

```bash
cd ~/EvidenceFlow-AI-Hybrid-RAG
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install --no-cache-dir -r requirements_render.txt
```

The backend uses CPU inference on EC2. Do not use multiple Uvicorn workers because each worker can load another copy of the embedding model.

## 6. Configure backend environment variables

Create the environment file:

```bash
cd ~/EvidenceFlow-AI-Hybrid-RAG
nano .env
```

Add the following values. Replace every placeholder with a real value:

```env
DATABASE_URL=postgresql+psycopg2://DB_USER:DB_PASSWORD@RDS_ENDPOINT:5432/evidenceflow
GROQ_API_KEY=your_new_groq_key
COHERE_API_KEY=your_new_cohere_key
FRONTEND_URL=http://EC2_PUBLIC_IP
```

Do not add `RENDER_DISK_PATH`. This deployment stores application files on the EC2 EBS disk.

Do not commit `.env` to GitHub.

The Google OAuth variables are omitted because the current backend contains a localhost OAuth callback. Use normal email/password login unless OAuth callback handling is updated separately.

## 7. Test PostgreSQL before starting the API

Run this from the project root:

```bash
cd ~/EvidenceFlow-AI-Hybrid-RAG
source .venv/bin/activate

python -c "from dotenv import load_dotenv; import os; from sqlalchemy import create_engine; load_dotenv(); engine=create_engine(os.environ['DATABASE_URL']); print(engine.dialect.name, engine.dialect.driver); engine.connect().close(); print('database connection OK')"
```

Expected output includes:

```text
postgresql psycopg2
database connection OK
```

If this fails, check the RDS endpoint, username, password, database name, and RDS security group before continuing.

## 8. Test the backend locally on EC2

Start the backend in the foreground:

```bash
cd ~/EvidenceFlow-AI-Hybrid-RAG
source .venv/bin/activate
uvicorn backend.app:app --host 127.0.0.1 --port 8001 --workers 1
```

Open a second Instance Connect session if available. Otherwise stop the foreground process and use `nohup` as shown below.

Test from EC2:

```bash
curl -i --max-time 30 http://127.0.0.1:8001/
```

A successful response starts with:

```text
HTTP/1.1 200 OK
```

Stop the foreground process with `Ctrl+C` after the test.

## 9. Run the backend as a systemd service

Create the service:

```bash
sudo nano /etc/systemd/system/evidenceflow.service
```

Use this content:

```ini
[Unit]
Description=EvidenceFlow AI FastAPI backend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/EvidenceFlow-AI-Hybrid-RAG
EnvironmentFile=/home/ubuntu/EvidenceFlow-AI-Hybrid-RAG/.env
ExecStart=/home/ubuntu/EvidenceFlow-AI-Hybrid-RAG/.venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port 8001 --workers 1
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable evidenceflow
sudo systemctl start evidenceflow
sudo systemctl status evidenceflow
```

View backend logs:

```bash
sudo journalctl -u evidenceflow -f
```

Check the local API:

```bash
curl -i http://127.0.0.1:8001/
```

## 10. Build the React frontend

The frontend should call Nginx at `/api`, so the backend port does not need to be public.

```bash
cd ~/EvidenceFlow-AI-Hybrid-RAG/frontend
npm install
VITE_API_URL=/api npm run build
```

Copy the compiled frontend to Nginx:

```bash
sudo mkdir -p /var/www/evidenceflow
sudo cp -r dist/* /var/www/evidenceflow/
```

## 11. Configure Nginx

Create an Nginx site:

```bash
sudo nano /etc/nginx/sites-available/evidenceflow
```

Add:

```nginx
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    server_name _;
    root /var/www/evidenceflow;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8001/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

Enable the site:

```bash
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/evidenceflow /etc/nginx/sites-enabled/evidenceflow
sudo nginx -t
sudo systemctl restart nginx
```

## 12. Open the application

Visit this URL in a browser:

```text
http://EC2_PUBLIC_IP
```

Test from EC2:

```bash
curl -i http://127.0.0.1/
curl -i http://127.0.0.1/api/
```

Test from another computer or AWS CloudShell:

```bash
curl -i http://EC2_PUBLIC_IP/
```

The frontend should load on port `80`, and Nginx should forward frontend API requests to FastAPI on port `8001`.

## 13. Initialize the application

1. Open `http://EC2_PUBLIC_IP`.
2. Log in with the initial admin account:

```text
Email: admin@evidenceflow.ai
Password: admin123
```

3. Upload PDF files through the admin interface.
4. Wait for the embedding model to load.
5. Initialize the system.

The files are stored on the EC2 disk:

```text
~/EvidenceFlow-AI-Hybrid-RAG/data/pdf/
~/EvidenceFlow-AI-Hybrid-RAG/data/vector_store/
~/EvidenceFlow-AI-Hybrid-RAG/data/cag_cache/
```

PostgreSQL stores the user records. The EC2 EBS disk stores PDFs, vectors, and cache data.

## 14. Updating the application

```bash
cd ~/EvidenceFlow-AI-Hybrid-RAG
git pull origin main
source .venv/bin/activate
sudo systemctl restart evidenceflow
```

If frontend files changed, rebuild and copy them again:

```bash
cd ~/EvidenceFlow-AI-Hybrid-RAG/frontend
npm install
VITE_API_URL=/api npm run build
sudo rm -rf /var/www/evidenceflow/*
sudo cp -r dist/* /var/www/evidenceflow/
sudo systemctl restart nginx
```

## Troubleshooting

### Port or connection refused

```bash
sudo systemctl status evidenceflow
sudo journalctl -u evidenceflow -n 100 --no-pager
sudo ss -ltnp | grep -E ':80|:8001'
sudo nginx -t
```

The backend should listen on `127.0.0.1:8001`, and Nginx should listen on `0.0.0.0:80`.

### Out of memory

Check memory:

```bash
free -h
```

Check whether the kernel killed Python:

```bash
dmesg -T | grep -i -E 'out of memory|killed process'
```

Use a larger EC2 instance and keep only one Uvicorn worker.

### Database connection failure

Verify:

- RDS and EC2 are in the same AWS region and VPC.
- RDS security group allows port `5432` from the EC2 security group.
- `DATABASE_URL` uses `postgresql+psycopg2://`.
- The RDS endpoint and password are correct.

### Frontend cannot call the backend

Verify:

```bash
grep VITE_API_URL ~/EvidenceFlow-AI-Hybrid-RAG/frontend/dist/assets/*.js
curl -i http://127.0.0.1/api/
curl -i http://EC2_PUBLIC_IP/api/
```

The frontend must be built with:

```bash
VITE_API_URL=/api npm run build
```

## Security notes

- Do not commit `.env`.
- Do not paste API keys into GitHub issues, chat, or logs.
- Restrict SSH to your IP address.
- Do not expose port `8001` publicly when using Nginx.
- Change the default admin password after the first login.
- An IP-only HTTP deployment is suitable for testing, not for production. Use HTTPS and a domain before handling real users or sensitive documents.
