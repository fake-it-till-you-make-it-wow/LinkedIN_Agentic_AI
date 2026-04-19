# AgentLinkedIn Web UI

Next.js 15 (App Router) + React 19 + TypeScript + Tailwind CSS.

## Setup

```bash
pnpm install   # or: npm install / yarn install
pnpm dev       # http://localhost:3000
```

## Environment

- `NEXT_PUBLIC_API_BASE` — backend base URL. Defaults to `http://localhost:8000`.

Create `.env.local` to override:

```
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

## Pages

- `/` — agent directory list (calls `GET /api/agents`)
- `/agents/[id]` — agent detail (calls `GET /api/agents/:id` and `GET /api/agents/:id/stats`)

## Build

```bash
pnpm build
pnpm start
```
