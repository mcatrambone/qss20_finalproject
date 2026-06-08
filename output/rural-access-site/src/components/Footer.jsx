export default function Footer() {
  return (
    <footer className="border-t border-ink-200 bg-ink-50 px-5 py-12">
      <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-6 sm:flex-row sm:items-center">
        <div>
          <p className="font-serif text-lg font-600 text-ink-900">
            Spatial Access &amp; Rural Mortality
          </p>
          <p className="mt-1 text-sm text-ink-500">
            Matthew Catrambone · Dartmouth College · QSS 20 · June 2026
          </p>
        </div>
        <a
          href="https://github.com/mcatrambone/qss20_finalproject"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 rounded-lg border border-ink-300 bg-white px-4 py-2.5 text-sm font-semibold text-ink-700 transition hover:border-ink-400 hover:bg-ink-100"
        >
          <svg
            viewBox="0 0 16 16"
            width="18"
            height="18"
            fill="currentColor"
            aria-hidden="true"
          >
            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
          </svg>
          View repository
        </a>
      </div>
      <p className="mx-auto mt-8 max-w-6xl text-xs leading-relaxed text-ink-400">
        Cross-sectional county-level analysis (2022–2023), n = 3,072. Data:
        Area Health Resources Files 2025, CDC PLACES, U.S. Census TIGER/Line,
        and OSRM drive-time routing. Findings are observational and
        ecological; associations should not be read as individual-level causal
        effects.
      </p>
    </footer>
  )
}
