export default function Hero() {
  return (
    <section
      id="question"
      className="relative flex min-h-screen items-center overflow-hidden px-5 pt-20"
    >
      {/* soft accent wash */}
      <div className="pointer-events-none absolute -right-40 -top-40 h-[520px] w-[520px] rounded-full bg-forest-200/40 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-40 -left-40 h-[480px] w-[480px] rounded-full bg-forest-100/60 blur-3xl" />

      <div className="relative mx-auto w-full max-w-5xl">
        <p className="reveal mb-6 inline-flex items-center gap-2 rounded-full border border-forest-300 bg-forest-100/60 px-3.5 py-1.5 font-mono text-[12px] font-medium uppercase tracking-[0.14em] text-forest-800">
          <span className="h-1.5 w-1.5 rounded-full bg-forest-600" />
          County-level spatial epidemiology · 3,072 counties
        </p>

        <h1 className="reveal font-serif text-[2.6rem] font-600 leading-[1.05] tracking-tight text-ink-900 sm:text-6xl md:text-7xl">
          Can people in rural America
          <br className="hidden sm:block" />{' '}
          actually <span className="text-forest-700">reach</span> a doctor?
        </h1>

        <p className="reveal prose-col mt-7 text-xl leading-relaxed text-ink-600">
          Standard rurality measures like RUCC codes tell you how remote a county
          is — not whether its residents can get to care. This project asks a
          sharper question: does a{' '}
          <span className="font-semibold text-ink-800">
            drive-time-weighted access score (E2SFCA)
          </span>{' '}
          explain the rural mortality penalty any better than the blunt
          instruments we already use?
        </p>

        <div className="reveal mt-10 flex flex-wrap items-center gap-3">
          <a
            href="#findings"
            className="rounded-lg bg-forest-700 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-forest-800"
          >
            Jump to the findings →
          </a>
          <a
            href="#data"
            className="rounded-lg border border-ink-300 bg-white px-5 py-3 text-sm font-semibold text-ink-700 transition hover:border-ink-400 hover:bg-ink-50"
          >
            How it was built
          </a>
        </div>

        <p className="reveal mt-12 max-w-reading text-sm text-ink-400">
          A 2–3 minute read. No prior knowledge required.
        </p>
      </div>
    </section>
  )
}
