# SEAF Production Deployment Guide

This guide walks you through deploying the SEAF application to your VPS with automated CI/CD via GitHub Actions.

## Overview

**Domain**: `seaf.cenariodigital.dev`
**Reverse Proxy**: Traefik (already configured)
**CI/CD**: GitHub Actions with automated push deployment
**Server**: Self-hosted VPS with Docker

---

## Prerequisites

✅ VPS with Docker and Docker Compose installed
✅ Traefik already running on the VPS
✅ Domain `seaf.cenariodigital.dev` pointing to your VPS
✅ SSH access to the VPS
✅ GitHub repository for this project

---

## Step 1: Prepare Your VPS

### 1.1 Create Application Directory

SSH into your VPS and create a directory for the application:

```bash
sudo mkdir -p /opt/seaf
sudo chown $USER:$USER /opt/seaf
cd /opt/seaf
```

### 1.2 Clone Repository

```bash
git clone <your-repo-url> .
git checkout deploy/0.1
```

### 1.3 Create Production Environment File

```bash
cp .env.production .env
```

Edit `.env` with your production values:

```bash
nano .env
```

**Required changes:**
- `SECRET_KEY`: Generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- `DB_PASSWORD`: Generate with `openssl rand -base64 32`
- `DJANGO_SUPERUSER_PASSWORD`: Set your admin password
- `DJANGO_SUPERUSER_EMAIL`: Set your admin email

### 1.4 Verify Traefik Network

Ensure the `traefik-public` network exists:

```bash
docker network ls | grep traefik-public
```

If it doesn't exist:

```bash
docker network create traefik-public
```

### 1.5 Update DNS

Ensure `seaf.cenariodigital.dev` points to your VPS IP:

```bash
# Check DNS propagation
nslookup seaf.cenariodigital.dev

# Or
dig seaf.cenariodigital.dev
```

---

## Step 2: First Manual Deployment

Before setting up automated deployments, verify everything works manually:

```bash
cd /opt/seaf
chmod +x deploy.sh
./deploy.sh
```

This will:
- Pull latest code
- Build Docker images
- Start containers
- Run migrations
- Collect static files
- Create superuser (if configured)

### Verify Deployment

Check the application is running:

```bash
# View status
./deploy.sh status

# View logs
./deploy.sh logs

# Test the URL
curl -I https://seaf.cenariodigital.dev
```

Visit `https://seaf.cenariodigital.dev` in your browser. You should see the application with a valid SSL certificate.

---

## Step 3: Setup GitHub Actions for Automated Deployment

### 3.1 Create Deploy User (Recommended)

For better security, create a dedicated deploy user:

```bash
# On your VPS
sudo adduser deploy
sudo usermod -aG docker deploy
sudo chown -R deploy:deploy /opt/seaf
```

### 3.2 Setup SSH Key for GitHub Actions

```bash
# On your VPS (as deploy user or your user)
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy
cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# Display private key (you'll need this for GitHub)
cat ~/.ssh/github_deploy
```

**⚠️ Important**: Copy the entire private key output (including `-----BEGIN` and `-----END` lines)

### 3.3 Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add these secrets:

| Secret Name | Value | Example |
|------------|-------|---------|
| `SSH_PRIVATE_KEY` | The private key from `~/.ssh/github_deploy` | Full SSH private key |
| `VPS_HOST` | Your VPS IP address or hostname | `123.45.67.89` |
| `VPS_USER` | SSH username | `deploy` or your username |
| `VPS_PATH` | Application directory on VPS | `/opt/seaf` |

### 3.4 Verify Traefik Configuration

Make sure your Traefik configuration includes a `cloudflare` certificate resolver. Check your Traefik configuration file (usually `traefik.yml` or in `traefik-compose.yaml` labels).

The `compose.prod.yaml` file expects a resolver named `cloudflare`. If your Traefik uses a different resolver name (like `letsencrypt`), update line 67 in `compose.prod.yaml`:

```yaml
# Change from:
- "traefik.http.routers.seaf-secure.tls.certresolver=cloudflare"
# To:
- "traefik.http.routers.seaf-secure.tls.certresolver=letsencrypt"
```

---

## Step 4: Test Automated Deployment

### 4.1 Trigger First Automated Deploy

Push a change to the `deploy/0.1` or `main` branch:

```bash
git add .
git commit -m "Test automated deployment"
git push origin deploy/0.1
```

### 4.2 Monitor Deployment

1. Go to your GitHub repository
2. Click on "Actions" tab
3. Watch the deployment workflow run
4. Check for any errors

### 4.3 Verify Deployment Succeeded

After the workflow completes:

```bash
# SSH into your VPS
ssh deploy@your-vps-ip

# Check application status
cd /opt/seaf
./deploy.sh status
./deploy.sh logs
```

Visit `https://seaf.cenariodigital.dev` to verify the application is running.

---

## Deployment Workflow

Once set up, deployments are automatic:

1. Push code to `deploy/0.1` or `main` branch
2. GitHub Actions automatically:
   - Connects to your VPS via SSH
   - Pulls latest code
   - Rebuilds Docker containers
   - Runs migrations
   - Restarts services
   - Verifies health check
3. Application updates with zero manual intervention

You can also trigger manual deployments:
- Go to Actions → Deploy to Production → Run workflow

---

## Useful Commands

### On Your VPS

```bash
# Deploy/Update application
./deploy.sh

# View logs
./deploy.sh logs

# Check status
./deploy.sh status

# Restart containers
./deploy.sh restart

# Stop application
./deploy.sh stop

# View real-time logs
docker compose -f compose.prod.yaml logs -f

# Access Django shell
docker compose -f compose.prod.yaml exec app python manage.py shell

# Create superuser manually
docker compose -f compose.prod.yaml exec app python manage.py createsuperuser

# Run migrations manually
docker compose -f compose.prod.yaml exec app python manage.py migrate
```

---

## Troubleshooting

### Application Not Starting

```bash
# Check container status
docker compose -f compose.prod.yaml ps

# View detailed logs
docker compose -f compose.prod.yaml logs

# Check database connectivity
docker compose -f compose.prod.yaml exec app python manage.py check --database default
```

### SSL Certificate Issues

```bash
# Check Traefik logs
docker logs traefik

# Verify DNS is correct
dig seaf.cenariodigital.dev

# Manually trigger certificate
docker restart traefik
```

### GitHub Actions Deployment Fails

1. Check GitHub Actions logs for specific error
2. Verify SSH secrets are correct
3. Test SSH connection manually:
   ```bash
   ssh -i /path/to/private/key user@vps-ip
   ```
4. Check VPS disk space:
   ```bash
   df -h
   ```

### Database Connection Errors

```bash
# Check database container
docker compose -f compose.prod.yaml ps db

# Check database logs
docker compose -f compose.prod.yaml logs db

# Verify environment variables
cat .env | grep DB_
```

### Static Files Not Loading

```bash
# Recollect static files
docker compose -f compose.prod.yaml exec app python manage.py collectstatic --noinput

# Verify volume mounts
docker volume ls
docker volume inspect short-skirt-long-jacket_static_volume
```

---

## Security Checklist

- [ ] `DEBUG=False` in production `.env`
- [ ] Strong `SECRET_KEY` generated
- [ ] Strong database passwords
- [ ] SSH key authentication (no password login)
- [ ] Firewall configured (only ports 80, 443, 22 open)
- [ ] Regular backups of database volume
- [ ] `.env` file never committed to git
- [ ] GitHub secrets properly configured
- [ ] SSL certificates auto-renewing via Let's Encrypt

---

## Backup Strategy

### Database Backup

```bash
# Create backup
docker compose -f compose.prod.yaml exec db pg_dump -U seaf_user seaf_production > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
cat backup_file.sql | docker compose -f compose.prod.yaml exec -T db psql -U seaf_user -d seaf_production
```

### Volume Backup

```bash
# Backup volumes
docker run --rm -v short-skirt-long-jacket_postgres_data:/data -v $(pwd):/backup ubuntu tar czf /backup/postgres_backup.tar.gz /data
```

---

## Monitoring

Consider setting up:

- **Uptime monitoring**: UptimeRobot, Pingdom
- **Log aggregation**: Papertrail, Loggly
- **Error tracking**: Sentry
- **Server monitoring**: Netdata, Prometheus

---

## Support

- Technical documentation: `README.technical.md`
- Command reference: `README.commands.md`
- Application health: `https://seaf.cenariodigital.dev/health/`

For issues, check logs first:
```bash
./deploy.sh logs
```
