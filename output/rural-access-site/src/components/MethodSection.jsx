import { modelLabels } from '../data/modelFit.js'

const MEASURES = [
  {
    n: '1',
    name: 'RUCC Code',
    type: 'Classification',
    desc: 'The USDA Rural–Urban Continuum: a 1–9 ordinal code based on population size and metro adjacency. Simple, ubiquitous — but blind to whether providers actually exist nearby.',
  },
  {
    n: '2',
    name: 'Physician density',
    type: 'Supply count',
    desc: 'Providers per 10,000 residents within a county. Counts supply but ignores county borders — a doctor one mile across the county line is invisible to it.',
  },
  {
    n: '3',
    name: 'E2SFCA access score',
    type: 'Spatial gravity',
    desc: 'The Enhanced Two-Step Floating Catchment Area method (Luo & Qi 2009). Weights provider supply by real drive time, so access decays smoothly with distance and crosses county lines.',
    highlight: true,
  },
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

// Conceptual diagram of the E2SFCA gravity model: a population point reaches
// providers across three drive-time zones, each down-weighted by a decay factor.
function E2SFCADiagram() {
  return (
    <svg
      viewBox="0 0 420 360"
      className="h-auto w-full"
      role="img"
      aria-label="Diagram of the E2SFCA gravity model showing three drive-time catchment zones around a population centroid, each with a distance-decay weight."
    >
      {/* three concentric catchment zones */}
      <circle cx="170" cy="180" r="150" fill="#e3f2ed" stroke="#bfe0d7" strokeWidth="1.5" />
      <circle cx="170" cy="180" r="100" fill="#bfe0d7" stroke="#8cc4b6" strokeWidth="1.5" />
      <circle cx="170" cy="180" r="52" fill="#8cc4b6" stroke="#5ba593" strokeWidth="1.5" />

      {/* zone labels with decay weights */}
      <g className="font-mono" fontSize="11" fill="#225a4b">
        <text x="170" y="150" textAnchor="middle" fontWeight="600">0–10 min</text>
        <text x="170" y="164" textAnchor="middle">w = 1.00</text>
        <text x="170" y="100" textAnchor="middle" fontWeight="600">10–20 min</text>
        <text x="170" y="250" textAnchor="middle" fontWeight="600">20–30 min</text>
        <text x="170" y="264" textAnchor="middle">w = 0.42</text>
      </g>

      {/* population centroid */}
      <circle cx="170" cy="180" r="7" fill="#0f172a" />
      <text x="170" y="200" textAnchor="middle" fontSize="10" fill="#0f172a" fontWeight="600">
        population
      </text>

      {/* providers scattered across zones */}
      <g fill="#225a4b">
        <rect x="150" y="135" width="9" height="9" rx="1.5" />
        <rect x="120" y="120" width="9" height="9" rx="1.5" />
        <rect x="230" y="200" width="9" height="9" rx="1.5" />
        <rect x="90" y="230" width="9" height="9" rx="1.5" />
        <rect x="255" y="120" width="9" height="9" rx="1.5" />
      </g>

      {/* formula caption */}
      <g className="font-mono" fontSize="12" fill="#334155">
        <text x="210" y="340" textAnchor="middle" fontWeight="600">
          Aᵢ = Σ Rⱼ · W(dᵢⱼ)
        </text>
      </g>
      <text x="210" y="356" textAnchor="middle" fontSize="9.5" fill="#64748b">
        access = supply-to-demand ratios, decay-weighted by drive time
      </text>
    </svg>
  )
}

export default function MethodSection() {
  return (
    <section id="method" className="border-t border-ink-200/70 px-5 py-24 sm:py-28">
      <div className="mx-auto max-w-6xl">
        <SectionHeader kicker="02 — The method" title="Three ways to measure “access”" />

        <div className="grid grid-cols-1 gap-12 lg:grid-cols-[1fr_minmax(0,460px)] lg:gap-16">
          {/* left: the three measures */}
          <div className="reveal space-y-4">
            <p className="prose-col mb-8">
              The whole project hinges on a definition. “Access” can mean three
              very different things — and the question is whether the most
              sophisticated one earns its complexity.
            </p>
            {MEASURES.map((m) => (
              <div
                key={m.name}
                className={`rounded-xl border p-5 transition ${
                  m.highlight
                    ? 'border-forest-400 bg-forest-100/50 shadow-sm'
                    : 'border-ink-200 bg-white'
                }`}
              >
                <div className="flex items-baseline gap-3">
                  <span
                    className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full font-mono text-[13px] font-semibold ${
                      m.highlight ? 'bg-forest-700 text-white' : 'bg-ink-100 text-ink-600'
                    }`}
                  >
                    {m.n}
                  </span>
                  <div>
                    <h3 className="text-lg font-semibold text-ink-900">{m.name}</h3>
                    <span className="font-mono text-[11px] uppercase tracking-wider text-ink-400">
                      {m.type}
                    </span>
                  </div>
                </div>
                <p className="mt-3 text-[15px] leading-relaxed text-ink-600">{m.desc}</p>
              </div>
            ))}
          </div>

          {/* right: the diagram */}
          <div className="reveal lg:sticky lg:top-24 lg:self-start">
            <div className="rounded-xl border border-ink-200 bg-white p-6">
              <h3 className="mb-1 text-sm font-semibold text-ink-900">
                The E2SFCA gravity model
              </h3>
              <p className="mb-4 text-[13px] leading-relaxed text-ink-500">
                Each population centroid “floats” a catchment outward in three
                drive-time zones. Nearby providers count fully; distant ones are
                down-weighted by a Gaussian decay. Supply and demand are
                reconciled in two passes.
              </p>
              <E2SFCADiagram />
            </div>
          </div>
        </div>

        {/* model sequence */}
        <div className="reveal mt-20">
          <h3 className="mb-2 font-serif text-2xl font-600 text-ink-900">
            The incremental model sequence
          </h3>
          <p className="prose-col mb-8">
            Each mortality outcome is regressed on access using weighted least
            squares (weighted by county population), adding one layer at a time.
            If the access score matters, it should improve fit{' '}
            <em>after</em> the baseline confounders are already in.
          </p>
          <ol className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {Object.entries(modelLabels).map(([key, label], i) => (
              <li
                key={key}
                className="relative rounded-lg border border-ink-200 bg-white p-4"
              >
                <span className="font-mono text-[12px] font-semibold text-forest-700">
                  Model {i}
                </span>
                <p className="mt-1.5 text-sm font-medium leading-snug text-ink-700">
                  {label}
                </p>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  )
}
