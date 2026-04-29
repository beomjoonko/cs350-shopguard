# ShopGuard — Frontend (Next.js)

App-router based Next.js 14 client implementing the screens described in SRS §3.1.

## Pages

| Route | SRS Reference | Purpose |
|---|---|---|
| `/` | §3.1 Main Search Interface | Landing + central search bar |
| `/search` | §3.1 Search Results & Warning | Show Risk Score / Level for a URL |
| `/report` | §3.1 Fraud Reporting Interface + §4.2 | Report-fraud form (with legal-consent gate) |
| `/login`, `/register` | §4.1 | Auth |
| `/my-page` | §3.1 My Account + §4.3 | User's report history |
| `/admin` | §3.1 Admin Dashboard + §4.4 | Admin moderation |

## Local development

Inside the monorepo, the frontend is started by `make up`. To run standalone:

```bash
npm install
cp .env.example .env.local
npm run dev
```

The API base URL comes from `NEXT_PUBLIC_API_BASE_URL`. All HTTP calls go
through `src/lib/api.ts`.
