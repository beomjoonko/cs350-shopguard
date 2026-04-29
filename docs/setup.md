# ShopGuard — Local Setup

## Prerequisites

- Docker Desktop (or Docker Engine + Compose plugin)
- Make (optional, for the Makefile shortcuts)
- ≥ 8 GB free RAM (the four services together fit easily, but MySQL likes room)

## First run

```bash
git clone <repo-url> shopguard
cd shopguard
cp .env.example .env

# Build images and start everything in the background
make up

# Apply DB migrations (Alembic)
make migrate
```

You should now have:

| Service | URL |
|---|---|
| Frontend (Next.js) | http://localhost:3000 |
| Backend Swagger UI | http://localhost:8000/docs |
| Backend ReDoc      | http://localhost:8000/redoc |
| MySQL              | `mysql://shopguard:changeme@localhost:3306/shopguard` |
| Redis              | `redis://localhost:6379` |

## Creating the first admin user

The auth router only creates `USER` accounts. To promote a user to admin,
log in to MySQL once and update the row manually:

```sql
USE shopguard;
UPDATE users SET role = 'ADMIN' WHERE email = 'you@example.com';
```

## Common tasks

```bash
make logs                   # tail logs from all services
make down                   # stop everything
make revision m="add column"  # new Alembic migration
make migrate                # apply pending migrations
make test-backend
make test-frontend
make clean                  # nuke volumes + node_modules
```

## Running services without Docker (advanced)

Each subdirectory has its own `requirements.txt` / `package.json`. The only
external infrastructure you need running is **MySQL 8** and **Redis 7** —
adjust `DATABASE_URL` and `REDIS_HOST` in your `.env` accordingly.

## Resetting the database

```bash
make down
docker volume rm shopguard_mysql_data shopguard_redis_data
make up
make migrate
```
