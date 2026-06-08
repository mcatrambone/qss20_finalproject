import { useEffect, useState } from 'react'
import Hero from './components/Hero.jsx'
import DataSection from './components/DataSection.jsx'
import MethodSection from './components/MethodSection.jsx'
import FindingsSection from './components/FindingsSection.jsx'
import Takeaway from './components/Takeaway.jsx'
import Footer from './components/Footer.jsx'

const SECTIONS = [
  { id: 'question', label: 'Question' },
  { id: 'data', label: 'Data' },
  { id: 'method', label: 'Method' },
  { id: 'findings', label: 'Findings' },
  { id: 'takeaway', label: 'Takeaway' },
]

function Nav({ active }) {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 border-b border-ink-200/70 bg-ink-50/85 backdrop-blur-md">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3">
        <a href="#question" className="group flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-sm bg-forest-700 font-mono text-[11px] font-medium text-white">
            R
          </span>
          <span className="hidden text-sm font-semibold tracking-tight text-ink-800 sm:inline">
            Rural Access &amp; Mortality
          </span>
        </a>
        <ul className="flex items-center gap-1 sm:gap-2">
          {SECTIONS.map((s) => (
            <li key={s.id}>
              <a
                href={`#${s.id}`}
                className={`rounded-full px-3 py-1.5 text-[13px] font-medium transition-colors ${
                  active === s.id
                    ? 'bg-forest-700 text-white'
                    : 'text-ink-500 hover:bg-ink-100 hover:text-ink-800'
                }`}
              >
                {s.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>
    </header>
  )
}

export default function App() {
  const [active, setActive] = useState('question')

  // Scroll-spy for nav highlighting
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) setActive(entry.target.id)
        })
      },
      { rootMargin: '-45% 0px -50% 0px', threshold: 0 }
    )
    SECTIONS.forEach((s) => {
      const el = document.getElementById(s.id)
      if (el) observer.observe(el)
    })
    return () => observer.disconnect()
  }, [])

  // Reveal-on-scroll for elements with .reveal
  useEffect(() => {
    const els = document.querySelectorAll('.reveal')
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible')
            obs.unobserve(entry.target)
          }
        })
      },
      { threshold: 0.12 }
    )
    els.forEach((el) => obs.observe(el))
    return () => obs.disconnect()
  }, [])

  return (
    <div className="grain-bg min-h-screen">
      <Nav active={active} />
      <main>
        <Hero />
        <DataSection />
        <MethodSection />
        <FindingsSection />
        <Takeaway />
      </main>
      <Footer />
    </div>
  )
}
