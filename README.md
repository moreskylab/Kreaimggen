# KreaImgGen

Production-ready AI image generation platform – **FastAPI** backend, **Celery** workers, **Bootstrap 5** frontend served via **Nginx**, brokered through **RabbitMQ**, cached in **Redis**, orchestrated on Kubernetes with a full **Helm** chart and **Gateway API** routing.

---

## Architecture

```
Browser  ──►  Nginx (frontend)
                │  /api/* proxied to
                ▼
          FastAPI (backend)   ──►  RabbitMQ  ──►  Celery Worker  ──►  Krea AI
                │                                       │
                └──────────────  Redis (results)  ◄─────┘
```

| Component | Technology |
|-----------|------------|
| Frontend  | Nginx 1.27, Bootstrap 5, Vanilla JS |
| Backend   | FastAPI 0.111, SlowAPI rate-limiting, JWT (python-jose) |
| Worker    | Celery 5.3, RabbitMQ 3.13 (broker), Redis 7 (backend) |
| AI        | Krea AI REST API (async prediction polling) |
| Monitoring| Flower, Fluentd → Elasticsearch, Grafana dashboard |
| Infra     | Docker Compose (dev) · Helm chart (prod) · Kustomize overlay |

---

## Quick Start (Docker Compose)

```bash
cp .env.example .env                  # set KREA_API_KEY and SECRET_KEY
# Run migrations manually (during development)
cd backend
alembic upgrade head

# Generate a new migration after model changes
alembic revision --autogenerate -m "add images table"

# docker-compose spins up postgres automatically and migrations run on container start
docker compose up --build -d

open http://localhost                  # Frontend
open http://localhost:15672            # RabbitMQ Management (guest/guest)
open http://localhost:5555             # Flower
open http://localhost:8000/api/v1/docs # FastAPI Swagger UI
```

---

## Project Structure

```
kreaimggen/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app, CORS, rate-limiting
│   │   ├── auth.py           # JWT helpers (bcrypt + python-jose)
│   │   ├── celery_app.py     # Celery + queue configuration
│   │   ├── tasks.py          # generate_image task → Krea AI
│   │   ├── models.py         # Pydantic models
│   │   ├── config.py         # pydantic-settings + .env
│   │   └── routes/
│   │       ├── auth.py       # POST /register  POST /token
│   │       └── generate.py   # POST /generate  GET /generate/status/{id}
│   ├── Dockerfile            # Multi-stage, non-root
│   └── requirements.txt
├── worker/
│   └── Dockerfile            # Same source, celery worker CMD
├── frontend/
│   ├── Dockerfile            # Nginx Alpine
│   ├── nginx.conf            # Proxy /api → backend, SPA fallback
│   └── static/
│       ├── index.html        # Generate form (Bootstrap 5, dark)
│       ├── login.html        # JWT login
│       ├── register.html     # Registration
│       └── js/app.js         # authFetch, polling, JWT helpers
├── helm/kreaimggen/
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
│       ├── backend-deployment.yaml
│       ├── worker-deployment.yaml
│       ├── flower-deployment.yaml
│       ├── frontend-deployment.yaml
│       ├── redis-statefulset.yaml
│       ├── services.yaml
│       ├── hpa.yaml          # HPA for backend and worker
│       ├── secrets.yaml      # App/broker secrets + ServiceAccount
│       └── httproute.yaml    # Gateway API Gateway + 3 HTTPRoutes
├── kustomize/
│   ├── base/
│   └── overlays/production/  # Image overrides, replica/resource patches
├── observability/
│   ├── fluentd/fluentd.conf
│   └── grafana/celery-dashboard.json
├── docker-compose.yml
└── .env.example
```

---

## Kubernetes Deployment (Helm)

```bash
kubectl create namespace kreaimggen

helm upgrade --install kreaimggen ./helm/kreaimggen \
  --namespace kreaimggen \
  --set backend.secretEnv.SECRET_KEY="$(openssl rand -hex 32)" \
  --set backend.secretEnv.KREA_API_KEY="$KREA_API_KEY" \
  --set gateway.routes.frontend.hostnames[0]="kreaimggen.yourdomain.com"
```

**Kustomize production overlay:**

```bash
helm template kreaimggen ./helm/kreaimggen > kustomize/base/all.yaml
kubectl apply -k kustomize/overlays/production
```

---

## API Reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/auth/register` | — | Create user |
| `POST` | `/api/v1/auth/token` | — | Login → JWT |
| `POST` | `/api/v1/generate` | Bearer | Queue image generation |
| `GET`  | `/api/v1/generate/status/{id}` | Bearer | Poll task / get image URLs |
| `GET`  | `/healthz` | — | Liveness probe |

---

## Observability

**Fluentd** – set `ELASTICSEARCH_HOST`/`PORT` in `observability/fluentd/fluentd.conf`, deploy as DaemonSet.

**Grafana** – import `observability/grafana/celery-dashboard.json`. Metrics are exposed by [celery-exporter](https://github.com/danihodovic/celery-exporter) (Prometheus).

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | *(required)* | JWT signing key (`openssl rand -hex 32`) |
| `KREA_API_KEY` | *(required)* | Krea AI API key |
| `KREA_API_BASE_URL` | `https://api.krea.ai/v1` | Krea AI endpoint |
| `CELERY_BROKER_URL` | `amqp://guest:guest@rabbitmq:5672//` | RabbitMQ |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/0` | Redis results |
| `REDIS_URL` | `redis://redis:6379/1` | Redis rate-limit state |
| `RATE_LIMIT_PER_MINUTE` | `20` | Requests per IP per minute |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT lifetime |

---

## Production Checklist

- [ ] Replace `FAKE_USERS_DB` with PostgreSQL + SQLAlchemy
- [ ] Inject secrets via Vault / ExternalSecrets Operator
- [ ] Tighten CORS `allow_origins` to your frontend domain
- [ ] Restrict Flower + RabbitMQ UI to internal network / VPN
- [ ] Enable TLS on the Gateway listener (`protocol: HTTPS`)
- [ ] Configure `imagePullSecrets` for your private container registry