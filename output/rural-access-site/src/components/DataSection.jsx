const SOURCES = [
  {
    tag: 'AHRF 2025',
    name: 'Area Health Resources Files',
    desc: 'County-level physician supply: primary care, cardiology, and emergency medicine provider counts.',
  },
  {
    tag: 'CDC PLACES',
    name: 'Local health estimates',
    desc: 'Model-based county prevalence of behavioral and clinical risk factors used as confounders.',
  },
  {
    tag: 'Census TIGER/Line',
    name: 'Geographic boundaries',
    desc: 'County and tract geometries plus population-weighted centroids for the travel-time network.',
  },
  {
    tag: 'OSRM',
    name: 'Open Source Routing Machine',
    desc: 'Real road-network drive times between population centroids and provider locations.',
  },
]

const FACTS = [
  { value: '3,072', label: 'U.S. counties' },
  { value: '4', label: 'data sources' },
  { value: '2022–23', label: 'cross-sectional' },
  { value: '4', label: 'mortality outcomes' },
]

function SectionHeader({ kicker, title }) {
  return (
    <div className="reveal mb-12 max-w-reading">
      <p className="mb-3 font-mono text-[12px] font-medium uppercase tracking-[0.16em] text-forest-700">
        {kicker}
      </p>
      <h2 className="font-serif text-4xl font-600 tracking-tight text-ink-900 sm:text-5xl">
        {title}
      </h2>
    </div>
  )
}

export default function DataSection() {
  return (
    <section id="data" className="border-t border-ink-200/70 px-5 py-24 sm:py-28">
      <div className="mx-auto max-w-6xl">
        <SectionHeader kicker="01 — The data" title="Four sources, one merged county panel" />

        <p className="reveal prose-col mb-12">
          Every county in the contiguous U.S. was joined into a single
          cross-sectional dataset spanning 2022–2023. The build links provider
          supply, population geography, real road-network travel times, and
          health risk factors — then aligns them to CDC mortality outcomes.
        </p>

        <div className="reveal grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {SOURCES.map((s) => (
            <div
              key={s.tag}
              className="group rounded-xl border border-ink-200 bg-white p-5 transition hover:border-forest-300 hover:shadow-md"
            >
              <span className="inline-block rounded-md bg-forest-100 px-2.5 py-1 font-mono text-[12px] font-medium text-forest-800">
                {s.tag}
              </span>
              <h3 className="mt-4 text-base font-semibold text-ink-900">{s.name}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-500">{s.desc}</p>
            </div>
          ))}
        </div>

        <div className="reveal mt-10 grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-ink-200 bg-ink-200 sm:grid-cols-4">
          {FACTS.map((f) => (
            <div key={f.label} className="bg-white px-5 py-6 text-center">
              <div className="font-serif text-3xl font-600 text-forest-700 tnum sm:text-4xl">
                {f.value}
              </div>
              <div className="mt-1 text-[13px] font-medium uppercase tracking-wide text-ink-500">
                {f.label}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
