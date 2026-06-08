const POINTS = [
  {
    n: '01',
    title: 'Access ≠ density',
    body: 'The E2SFCA score is statistically orthogonal to physician density — they capture genuinely different things. A county can have few resident doctors yet good drive-time access, or vice versa. Treating them as interchangeable would be a mistake.',
  },
  {
    n: '02',
    title: 'Nationally, neither moves the needle',
    body: 'At the U.S. county level, neither access measure explains the rural mortality penalty beyond what state fixed effects and age structure already account for. The headline gain from adding the access score to all-cause mortality is a negligible +0.003 in adjusted R².',
  },
  {
    n: '03',
    title: 'Regionally, the picture changes',
    body: 'In Appalachia and the Great Plains, spatiotemporal access gains real traction — correlations strengthen by up to Δρ = −0.21. The implication: these measures earn their keep at finer geographic resolution, where local road networks and provider scarcity actually bind.',
  },
]

export default function Takeaway() {
  return (
    <section
      id="takeaway"
      className="border-t border-ink-200/70 bg-ink-900 px-5 py-24 text-ink-100 sm:py-28"
    >
      <div className="mx-auto max-w-6xl">
        <div className="reveal mb-12 max-w-reading">
          <p className="mb-3 font-mono text-[12px] font-medium uppercase tracking-[0.16em] text-forest-300">
            04 — Takeaway
          </p>
          <h2 className="font-serif text-4xl font-600 tracking-tight text-white sm:text-5xl">
            So — does drive time do better?
          </h2>
          <p className="mt-6 text-lg leading-relaxed text-ink-300">
            Mostly no, sometimes yes — and the “sometimes” is the interesting
            part. A sophisticated access measure isn’t a free upgrade over RUCC
            codes nationally, but geography decides whether it matters.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
          {POINTS.map((p) => (
            <div
              key={p.n}
              className="reveal rounded-xl border border-ink-700 bg-ink-800/60 p-6"
            >
              <span className="font-mono text-sm font-semibold text-forest-300">
                {p.n}
              </span>
              <h3 className="mt-3 font-serif text-xl font-600 text-white">{p.title}</h3>
              <p className="mt-3 text-[15px] leading-relaxed text-ink-300">{p.body}</p>
            </div>
          ))}
        </div>

        <div className="reveal mt-12 max-w-reading rounded-xl border border-forest-700/50 bg-forest-900/40 p-6">
          <p className="text-[15px] leading-relaxed text-forest-100">
            <span className="font-semibold text-white">The bottom line:</span> the
            rural mortality penalty is real, but at the county scale it lives in
            broad structural factors — age, state policy, rurality itself — more
            than in any single measure of how far the nearest doctor is. Spatial
            access methods like E2SFCA are most valuable precisely where the
            geography is hardest.
          </p>
        </div>
      </div>
    </section>
  )
}
