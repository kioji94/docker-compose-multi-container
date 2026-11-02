# Multi-Container App with Docker Compose

![CI](../../actions/workflows/ci.yaml/badge.svg)

A two-service application orchestrated with Docker Compose: a **Flask web app** that stores data in a **PostgreSQL** database. Built as a DevOps practice project covering Docker Compose, container orchestration and container networking.

## Architecture

```
            host (your machine)
                  |
          port 5000 (published)
                  |
        +---------v---------+  app-net (private bridge network)  +----------------+
        |   web (Flask)     | ---------------------------------> |  db (Postgres) |
        |   container       |   resolves "db" via Docker DNS     |  container     |
        +-------------------+          port 5432 (internal)      +--------+-------+
                                                                          |
                                                                  volume: db-data
```

| Service | Image                | Role                    | Exposed to host |
|---------|----------------------|-------------------------|-----------------|
| `web`   | built from `./app`   | REST API (Flask)        | `5000`          |
| `db`    | `postgres:16-alpine` | Persistent data storage | none (internal) |

## Key concepts demonstrated

- **Service discovery**: `web` connects to the host `db`. Compose's built-in DNS resolves the service name to the container IP on `app-net`.
- **Network isolation**: `db` has no `ports:` mapping, so it is unreachable from the host. Only `web` can talk to it.
- **Startup ordering**: `depends_on` with `condition: service_healthy` waits for the Postgres `healthcheck` (`pg_isready`) before starting `web`.
- **Persistence**: the named volume `db-data` keeps data across `docker compose down` / `up`.
- **Configuration via environment**: credentials come from `.env` (git-ignored), with a committed `.env.example`.
- **Least privilege**: the web container runs as a non-root user.

## Project structure

```
.
├── app/
│   ├── Dockerfile
│   ├── app.py
│   └── requirements.txt
├── scripts/
│   └── smoke-test.sh
├── .github/workflows/ci.yaml
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

## Run it

```bash
cp .env.example .env            # then edit the password
docker compose up -d --build
docker compose ps
```

Test the API:

```bash
curl http://localhost:5000/
curl http://localhost:5000/health
curl -X POST http://localhost:5000/notes \
     -H 'Content-Type: application/json' \
     -d '{"content": "hello from compose"}'
curl http://localhost:5000/notes
```

Or run the full automated check:

```bash
./scripts/smoke-test.sh
```

## Explore the networking

```bash
docker network ls
docker network inspect docker-compose-multi-container_app-net

# DNS resolution from inside the web container
docker compose exec web python -c "import socket; print(socket.gethostbyname('db'))"

# Query the database from inside its container
docker compose exec db psql -U appuser -d appdb -c "SELECT * FROM notes;"

# Prove the DB is NOT exposed to the host (should fail)
nc -zv localhost 5432
```

## Test persistence

```bash
docker compose down            # removes containers, keeps the volume
docker compose up -d
curl http://localhost:5000/notes   # data is still there

docker compose down -v         # also deletes the volume (data is gone)
```

## Useful commands

```bash
docker compose logs -f web     # follow web logs
docker compose logs db
docker compose restart web
docker compose build --no-cache
docker compose config          # render the final resolved config
docker compose top
```

## CI (GitHub Actions)

`.github/workflows/ci.yaml` runs on every push and pull request to `main`, and can be started manually (**Actions** tab, **Run workflow**).

| Job           | What it does |
|---------------|--------------|
| `lint`        | `docker compose config`, hadolint (Dockerfile), shellcheck, flake8 |
| `integration` | builds images, starts the stack, runs `scripts/smoke-test.sh`, checks the DB port is not exposed on the host, dumps logs on failure, tears everything down |

## Publish to GitHub

```bash
git init -b main
git add .
git commit -m "feat: multi-container Flask + PostgreSQL app with Docker Compose and CI"
git remote add origin git@github.com:<your-username>/docker-compose-multi-container.git
git push -u origin main
```

Then open the **Actions** tab to watch the first CI run. Replace the badge URL at the top of this README with `https://github.com/<your-username>/docker-compose-multi-container/actions/workflows/ci.yaml/badge.svg`.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `port is already allocated` | Change `WEB_PORT` in `.env` |
| `web` restarts repeatedly | `docker compose logs web`; usually wrong DB credentials after changing `.env`. Run `docker compose down -v` and start again |
| Changed `POSTGRES_PASSWORD` but login fails | Postgres only reads it on first init; remove the volume with `down -v` |

## What I learned

- How Compose creates a project network and DNS entries per service
- Why healthchecks are better than `sleep` for startup ordering
- How to keep a database private while exposing only the app
- How to validate a multi-container stack automatically in CI
