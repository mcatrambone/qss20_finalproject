import { Fragment } from 'react'
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  Customized,
} from 'recharts'
import { correlations, outcomes, measures } from '../data/correlations.js'
import { primaryAllCause, specialistOutcomes } from '../data/modelFit.js'
import { regional } from '../data/regional.js'

/* ----------------------------- shared bits ----------------------------- */

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

function FigureFrame({ label, title, interp, children }) {
  return (
    <figure className="reveal mb-16 last:mb-0">
      <div className="overflow-hidden rounded-xl border border-ink-200 bg-white">
        <div className="border-b border-ink-100 px-5 py-3">
          <span className="font-mono text-[12px] font-semibold uppercase tracking-wider text-forest-700">
            {label}
          </span>
        </div>
        <div className="p-4 sm:p-6">{children}</div>
      </div>
      <figcaption className="mt-4 max-w-reading">
        <p className="font-semibold text-ink-900">{title}</p>
        <p className="mt-1 text-[15px] leading-relaxed text-ink-500">{interp}</p>
      </figcaption>
    </figure>
  )
}

/* --------------------------- recharts heatmap -------------------------- */

// Map a (negative) partial-rho to a sequential blue, matching the source figure.
function blueFor(rho) {
  const t = Math.min(Math.abs(rho) / 0.5, 1) // magnitude 0..1
  // light blue (#eaf2fa) -> deep blue (#1c4f87)
  const a = [234, 242, 250]
  const b = [28, 79, 135]
  const mix = a.map((c, i) => Math.round(c + (b[i] - c) * t))
  return `rgb(${mix[0]}, ${mix[1]}, ${mix[2]})`
}

// Heat layer drawn with direct access to recharts' axis scales, so cells tile
// perfectly and stay responsive.
function HeatLayer(props) {
  const { xAxisMap, yAxisMap } = props
  if (!xAxisMap || !yAxisMap) return null
  const xAxis = Object.values(xAxisMap)[0]
  const yAxis = Object.values(yAxisMap)[0]
  if (!xAxis?.scale || !yAxis?.scale) return null

  const xScale = xAxis.scale
  const yScale = yAxis.scale
  const cellW = Math.abs(xScale(1) - xScale(0)) - 6
  const cellH = Math.abs(yScale(1) - yScale(0)) - 6

  const cells = []
  outcomes.forEach((outcome, xi) => {
    measures.forEach((measure, yi) => {
      const entry = correlations[`${measure}|${outcome}`]
      if (!entry) return
      const cx = xScale(xi)
      const cy = yScale(yi)
      const fill = blueFor(entry.rho)
      const dark = Math.abs(entry.rho) > 0.28
      cells.push(
        <g key={`${xi}-${yi}`}>
          <rect
            x={cx - cellW / 2}
            y={cy - cellH / 2}
            width={cellW}
            height={cellH}
            rx={3}
            fill={fill}
            stroke="#ffffff"
            strokeWidth={1.5}
          />
          <text
            x={cx}
            y={cy + 5}
            textAnchor="middle"
            fontSize={15}
            fontFamily="'IBM Plex Mono', monospace"
            fontWeight={600}
            fill={dark ? '#ffffff' : '#1e293b'}
          >
            {entry.rho.toFixed(2)}
          </text>
          <text
            x={cx + cellW / 2 - 6}
            y={cy - cellH / 2 + 16}
            textAnchor="end"
            fontSize={12}
            fill={dark ? '#e2e8f0' : '#475569'}
          >
            {entry.sig}
          </text>
        </g>
      )
    })
  })
  return <g>{cells}</g>
}

// Custom wrapping tick for the long Y-axis measure labels.
function YTick({ x, y, payload }) {
  const label = measures[payload.value] ?? ''
  return (
    <text
      x={x}
      y={y}
      dy={4}
      textAnchor="end"
      fontSize={12.5}
      fill="#475569"
      fontFamily="Inter, sans-serif"
    >
      {label}
    </text>
  )
}

function XTick({ x, y, payload }) {
  const label = outcomes[payload.value] ?? ''
  return (
    <text
      x={x}
      y={y + 12}
      textAnchor="middle"
      fontSize={12.5}
      fontWeight={500}
      fill="#334155"
      fontFamily="Inter, sans-serif"
    >
      {label.replace(' mortality', '')}
    </text>
  )
}

function Heatmap() {
  // dummy data just to establish the scatter domain
  const data = [{ x: 0, y: 0 }]
  return (
    <div className="min-w-[520px]">
      <ResponsiveContainer width="100%" height={430}>
        <ScatterChart margin={{ top: 16, right: 24, bottom: 28, left: 150 }}>
          <XAxis
            type="number"
            dataKey="x"
            domain={[-0.5, outcomes.length - 0.5]}
            ticks={outcomes.map((_, i) => i)}
            tick={<XTick />}
            tickLine={false}
            axisLine={false}
            interval={0}
          />
          <YAxis
            type="number"
            dataKey="y"
            domain={[-0.5, measures.length - 0.5]}
            ticks={measures.map((_, i) => i)}
            tick={<YTick />}
            tickLine={false}
            axisLine={false}
            interval={0}
          />
          <Scatter data={data} fill="transparent" />
          <Customized component={HeatLayer} />
        </ScatterChart>
      </ResponsiveContainer>
      {/* legend */}
      <div className="mt-2 flex items-center justify-end gap-3 pr-2 text-[11px] text-ink-400">
        <span>weaker</span>
        <div
          className="h-3 w-32 rounded-full"
          style={{ background: 'linear-gradient(90deg, #eaf2fa, #1c4f87)' }}
        />
        <span>stronger (|ρ|)</span>
      </div>
    </div>
  )
}

/* ------------------------------- tables -------------------------------- */

function fmt(v, plus = false) {
  if (v === null || v === undefined) return '—'
  const s = v.toFixed(3)
  return plus && v > 0 ? `+${s}` : s
}

function ModelFitTable() {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] border-collapse text-left text-sm">
        <thead>
          <tr className="border-b-2 border-ink-300 text-ink-500">
            <th className="py-2.5 pr-4 font-semibold">Model</th>
            <th className="py-2.5 pr-4 font-semibold">Predictors added</th>
            <th className="py-2.5 pr-4 text-right font-semibold">Adj. R²</th>
            <th className="py-2.5 pr-4 text-right font-semibold">ΔR² vs M1</th>
            <th className="py-2.5 pr-4 text-right font-semibold">Partial R² (access)</th>
            <th className="py-2.5 text-right font-semibold">CV R²</th>
          </tr>
        </thead>
        <tbody>
          {primaryAllCause.map((r) => {
            const isAccess = r.model === 'Model 3' || r.model === 'Model 4'
            return (
              <tr
                key={r.model}
                className={`border-b border-ink-100 ${
                  isAccess ? 'bg-forest-100/40' : ''
                }`}
              >
                <td className="whitespace-nowrap py-2.5 pr-4 font-semibold text-ink-800">
                  {r.model}
                </td>
                <td className="py-2.5 pr-4 text-ink-600">{r.predictors}</td>
                <td className="py-2.5 pr-4 text-right tnum text-ink-800">{fmt(r.adjR2)}</td>
                <td className="py-2.5 pr-4 text-right tnum text-ink-600">
                  {fmt(r.dR2, true)}
                </td>
                <td className="py-2.5 pr-4 text-right tnum text-ink-600">
                  {fmt(r.partialR2)}
                </td>
                <td className="py-2.5 text-right tnum text-ink-600">{fmt(r.cvR2)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function SpecialistTable() {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] border-collapse text-left text-sm">
        <thead>
          <tr className="border-b-2 border-ink-300 text-ink-500">
            <th className="py-2.5 pr-4 font-semibold">Outcome</th>
            <th className="py-2.5 pr-4 font-semibold">Model</th>
            <th className="py-2.5 pr-4 text-right font-semibold">Adj. R²</th>
            <th className="py-2.5 pr-4 text-right font-semibold">ΔR² vs M1</th>
            <th className="py-2.5 text-right font-semibold">Partial R² (access)</th>
          </tr>
        </thead>
        <tbody>
          {specialistOutcomes.map((r, i) => {
            const firstOfGroup =
              i === 0 || specialistOutcomes[i - 1].outcome !== r.outcome
            const isAccess = r.model === 'Model 4'
            return (
              <tr
                key={`${r.outcome}-${r.model}`}
                className={`border-b border-ink-100 ${isAccess ? 'bg-forest-100/40' : ''} ${
                  firstOfGroup ? 'border-t-2 border-t-ink-200' : ''
                }`}
              >
                <td className="py-2.5 pr-4 font-semibold text-ink-800">
                  {firstOfGroup ? r.outcome : ''}
                </td>
                <td className="py-2.5 pr-4 text-ink-600">{r.predictors}</td>
                <td className="py-2.5 pr-4 text-right tnum text-ink-800">{fmt(r.adjR2)}</td>
                <td className="py-2.5 pr-4 text-right tnum text-ink-600">
                  {fmt(r.dR2, true)}
                </td>
                <td className="py-2.5 text-right tnum text-ink-600">{fmt(r.partialR2)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function RegionalTable() {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[620px] border-collapse text-left text-sm">
        <thead>
          <tr className="border-b-2 border-ink-300 text-ink-500">
            <th className="py-2.5 pr-4 font-semibold">Predictor</th>
            <th className="py-2.5 pr-4 text-right font-semibold">ρ (full)</th>
            <th className="py-2.5 pr-4 text-right font-semibold">ρ (subsample)</th>
            <th className="py-2.5 pr-4 text-right font-semibold">Δρ</th>
            <th className="py-2.5 text-right font-semibold">n (full / sub)</th>
          </tr>
        </thead>
        <tbody>
          {regional.map((block, bi) => (
            <Fragment key={`block-${bi}`}>
              <tr className="bg-ink-100/70">
                <td colSpan={5} className="px-1 py-2 text-[13px]">
                  <span className="font-semibold text-ink-800">{block.region}</span>
                  <span className="text-ink-400"> · {block.outcome}</span>
                </td>
              </tr>
              {block.rows.map((row) => (
                <tr
                  key={`${bi}-${row.predictor}`}
                  className={`border-b border-ink-100 ${
                    !row.isRef ? 'bg-forest-100/40' : ''
                  }`}
                >
                  <td className="py-2.5 pr-4 text-ink-700">
                    {row.predictor}
                    {row.isRef && (
                      <span className="ml-2 rounded bg-ink-100 px-1.5 py-0.5 font-mono text-[10px] uppercase text-ink-400">
                        ref
                      </span>
                    )}
                  </td>
                  <td className="py-2.5 pr-4 text-right tnum text-ink-600">{row.full}</td>
                  <td className="py-2.5 pr-4 text-right tnum text-ink-800">{row.sub}</td>
                  <td
                    className={`py-2.5 pr-4 text-right tnum font-semibold ${
                      row.dRho <= -0.1 ? 'text-forest-700' : 'text-ink-600'
                    }`}
                  >
                    {row.dRho.toFixed(2)}
                  </td>
                  <td className="py-2.5 text-right tnum text-ink-400">
                    {row.nFull} / {row.nSub}
                  </td>
                </tr>
              ))}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* ------------------------------ section -------------------------------- */

export default function FindingsSection() {
  return (
    <section id="findings" className="border-t border-ink-200/70 px-5 py-24 sm:py-28">
      <div className="mx-auto max-w-6xl">
        <SectionHeader kicker="03 — Key findings" title="What the data actually shows" />

        <p className="reveal prose-col mb-14">
          Four results, in order: where the access measures disagree on the map,
          how each correlates with mortality, whether they improve model fit
          nationally, and where they finally start to matter — regionally.
        </p>

        {/* a. Choropleth triptych */}
        <FigureFrame
          label="Figure 1 — Choropleth triptych"
          title="E2SFCA and physician density classify different counties as access-poor."
          interp="The three maps don't line up. Rurality (RUCC), raw provider density, and the drive-time access score each paint a different picture of where care is hardest to reach — so the choice of measure is not cosmetic."
        >
          <img
            src="/figures/choropleth_primary_access.png"
            alt="Three U.S. county choropleth maps comparing RUCC rurality code, primary care physicians per 10,000, and the primary care access score."
            className="mx-auto w-full max-w-4xl"
            loading="lazy"
          />
        </FigureFrame>

        {/* b. Correlation heatmap (recharts) */}
        <FigureFrame
          label="Figure 2 — Partial correlation matrix"
          title="Every access measure is negatively associated with mortality — but RUCC is the strongest."
          interp="Partial Spearman ρ (residualised on age structure and state). Each access measure tracks its matched outcome, yet the blunt RUCC code shows the largest associations across the board — a hint that access may be riding on rurality rather than adding to it."
        >
          <div className="overflow-x-auto">
            <Heatmap />
          </div>
        </FigureFrame>

        {/* c. Model fit table */}
        <FigureFrame
          label="Table 1 — Incremental model fit (all-cause mortality)"
          title="The access score adds almost nothing once age and state are controlled."
          interp="Going from Model 1 to Model 3 (adding the E2SFCA score) lifts adjusted R² by just +0.003, with a partial R² of 0.011. Provider density helps a little more, but neither access measure meaningfully explains all-cause mortality beyond the baseline confounders."
        >
          <ModelFitTable />
        </FigureFrame>

        {/* c-supplement. Specialist outcomes */}
        <FigureFrame
          label="Table 2 — Cause-specific outcomes (supplementary)"
          title="The one exception: respiratory mortality and emergency-medicine supply."
          interp="Across IHD, stroke, and respiratory deaths the access scores again add little. The standout is respiratory mortality, where EM physician density lifts R² by +0.028 — the only place a supply measure earns real explanatory weight at the national level."
        >
          <SpecialistTable />
        </FigureFrame>

        {/* d. Regional subgroup table */}
        <FigureFrame
          label="Table 3 — Regional subgroup analysis"
          title="Zoom into a region and the access scores suddenly start to matter."
          interp="Restricting to Appalachia and the Great Plains, the access measures strengthen sharply (Δρ as large as −0.21). What looks like noise nationally becomes signal locally — suggesting these measures earn their keep at finer geographic resolution."
        >
          <RegionalTable />
          <p className="mt-4 max-w-reading text-[13px] leading-relaxed text-ink-400">
            Partial Spearman ρ, residualised on % under 65 and state fixed
            effects. Δρ = subsample − full sample; only rows where the access
            measure improves by Δρ &lt; −0.05 are shown. *** p&lt;0.001, * p&lt;0.05.
          </p>
        </FigureFrame>
      </div>
    </section>
  )
}
