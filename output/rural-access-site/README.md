# Spatial Access & Rural Mortality

A single-page research site for a QSS 20 final project: does a drive-time-weighted
spatial access score (E2SFCA) explain the rural mortality penalty better than
standard rurality measures (RUCC codes)?

**Author:** Matthew Catrambone · Dartmouth College · June 2026

## Stack

- React 18 + Vite
- Tailwind CSS
- Recharts (correlation heatmap)
- Deploys to Vercel

## Local development

```bash
npm install
npm run dev
```

Open the printed `localhost` URL.

## Build

```bash
npm run build      # outputs to dist/
npm run preview    # preview the production build
```

## Deploy to Vercel

Push to GitHub, then import the repo at vercel.com. No configuration needed —
Vercel auto-detects Vite. `vercel.json` handles SPA fallback routing.

Or from the CLI:

```bash
npm i -g vercel
vercel
```

## Project structure

```
src/
  App.jsx                  main layout, sticky nav, scroll-spy
  components/
    Hero.jsx               the research question
    DataSection.jsx        4 data sources + study facts
    MethodSection.jsx      3 access measures + E2SFCA diagram + model sequence
    FindingsSection.jsx    all 4 figures (choropleth, heatmap, 2 tables)
    Takeaway.jsx           discussion / conclusions
    Footer.jsx             attribution + repo link
  data/
    correlations.js        partial Spearman rho for the heatmap
    modelFit.js            incremental WLS model fit tables
    regional.js            regional subgroup analysis
public/
  figures/
    choropleth_primary_access.png       main choropleth triptych (real figure)
    correlation_heatmap_source.png      source heatmap (reference; recreated in recharts)
```
