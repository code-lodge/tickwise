# Tickwise Dashboard

Angular 19 standalone-component dashboard, served by FastAPI in production
and via `ng serve --proxy-config proxy.conf.json` during development.

## Develop

```bash
cd dashboard
npm install
npm start              # http://localhost:4200, proxies /api → :19532
```

## Build (production)

```bash
npm run build          # outputs to ../tickwise/static/
```

The FastAPI app picks up `tickwise/static/index.html` automatically and
serves the dashboard from `/`. While `tickwise/static/` is empty, the
root path returns a small JSON pointer to `/api/docs`.
