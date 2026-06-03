'use client'

import { useEffect, useState, useCallback } from 'react'
import { AppShell } from '@/components/app-shell'

interface Brief {
  brief_id: string
  creator_id: string
  creator_name: string
  handle: string
  followers: string
  img: string
  niche: string
  tier: string
  deal_type: string
  product_line: string
  product_line_desc: string
  items: string[]
  key_message: string
  content_format: string
  must_include: string
  avoid: string
  posting_window: string
  promo_code?: string
  commission?: string
}

interface ProductLine {
  id: string
  desc: string
  items: string[]
  creator_count: number
}

interface BriefsData {
  briefs: Brief[]
  product_lines: ProductLine[]
  cohorts: { name: string; count: number; reach: number }[]
  summary: { total: number; gift_seeding: number; affiliate: number; total_reach: number; reach_fmt: string }
}

type Channel = 'Email' | 'DM' | 'Call'

function formatBriefText(brief: Brief, channel: Channel): string {
  const now = new Date().toISOString().slice(0, 19).replace('T', ' ') + ' UTC'
  const div  = '═'.repeat(64)
  const sub  = '─'.repeat(64)
  const pad  = (label: string, value: string) => `${label.padEnd(16)}: ${value}`

  const lines = [
    div,
    `PRODUCT BRIEF — ${brief.creator_name} (${brief.handle})`,
    div,
    pad('Deal Type', brief.deal_type),
    pad('Tier', brief.tier.toUpperCase()),
    pad('Niche', brief.niche),
    pad('Followers', brief.followers),
    '',
    sub,
    'PRODUCT RECOMMENDATION',
    sub,
    pad('Line', `${brief.product_line} — ${brief.product_line_desc}`),
    pad('Send', brief.items.join(', ')),
    ...(brief.promo_code  ? [pad('Promo Code', brief.promo_code)]  : []),
    ...(brief.commission  ? [pad('Commission', brief.commission)]   : []),
    '',
    sub,
    'CREATIVE BRIEF',
    sub,
    pad('KEY MESSAGE',    brief.key_message),
    pad('CONTENT FORMAT', brief.content_format),
    pad('MUST INCLUDE',   brief.must_include),
    pad('AVOID',          brief.avoid),
    pad('POST WINDOW',    brief.posting_window),
    '',
    sub,
    'DISPATCH',
    sub,
    pad('Channel', channel.toUpperCase()),
    pad('Generated', now),
    div,
  ]

  return lines.join('\n')
}

const HOW_IT_WORKS = [
  {
    n: '01',
    title: 'Creator + Deal Matching',
    body: 'Pipeline cross-references creator niche, tier, and engagement signals against Gymshark product lines to select the highest-fit SKU bundle.',
  },
  {
    n: '02',
    title: 'LLM Brief Generation',
    body: 'An LLM synthesises brand tone, creator voice, and campaign objectives into a single coherent brief — key message, content format, and compliance guardrails.',
  },
  {
    n: '03',
    title: 'Channel Dispatch',
    body: 'Brief is packaged for the selected outreach channel (Email / DM / Call) and logged to CRM with creator ID, deal type, and timestamp.',
  },
]

export default function ProductBriefsPage() {
  const [data, setData]           = useState<BriefsData | null>(null)
  const [loading, setLoading]     = useState(true)
  const [active, setActive]       = useState<Brief | null>(null)
  const [channel, setChannel]     = useState<Channel>('Email')
  const [output, setOutput]       = useState<string>('')
  const [generated, setGenerated] = useState(false)
  const [copied, setCopied]       = useState(false)

  useEffect(() => {
    fetch('/api/product-briefs')
      .then((r) => r.json())
      .then((d: BriefsData) => {
        setData(d)
        if (d.briefs.length) setActive(d.briefs[0])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const handleGenerate = useCallback(() => {
    if (!active) return
    setOutput(formatBriefText(active, channel))
    setGenerated(true)
    setCopied(false)
  }, [active, channel])

  const handleCopy = useCallback(() => {
    if (!output) return
    navigator.clipboard.writeText(output).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }, [output])

  if (loading) {
    return (
      <AppShell currentPage="product-briefs">
        <div className="flex items-center justify-center h-[calc(100vh-52px)]">
          <div className="font-mono text-[17px] text-t3 tracking-[0.14em] uppercase flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-lime animate-pulse-dot" />
            Loading product briefs…
          </div>
        </div>
      </AppShell>
    )
  }

  if (!data) {
    return (
      <AppShell currentPage="product-briefs">
        <div className="flex items-center justify-center h-[calc(100vh-52px)]">
          <div className="font-mono text-[17px] text-t3 tracking-[0.14em] uppercase">No brief data found.</div>
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell currentPage="product-briefs">
      <div className="h-[calc(100vh-52px)] overflow-y-auto p-6 flex flex-col gap-5">

        {/* ── TOP ROW ──────────────────────────────────────────────── */}
        <div className="grid grid-cols-[1fr_1fr] gap-5 flex-shrink-0">

          {/* Left: Generate Brief */}
          <div className="bg-panel border border-border flex flex-col">
            {/* Header */}
            <div className="px-5 py-3 border-b border-border flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-lime animate-pulse-dot" />
              <span className="font-mono text-[16px] text-t3 tracking-[0.2em] uppercase">Generate Brief</span>
            </div>

            <div className="p-5 flex flex-col gap-5 flex-1">
              {/* Creator selector */}
              <div>
                <label className="block font-mono text-[17px] text-t4 tracking-[0.18em] uppercase mb-2">
                  Creator
                </label>
                <div className="relative">
                  <select
                    value={active?.creator_id ?? ''}
                    onChange={(e) => {
                      const found = data.briefs.find((b) => b.creator_id === e.target.value)
                      if (found) { setActive(found); setGenerated(false) }
                    }}
                    className="w-full bg-[#0C0F0F] border border-border text-t1 font-mono text-[16px] px-4 py-3 appearance-none focus:outline-none focus:border-lime transition-colors cursor-pointer"
                  >
                    {data.briefs.map((b) => (
                      <option key={b.creator_id} value={b.creator_id}>
                        {b.creator_name} ({b.tier.toLowerCase()} · {b.deal_type.toLowerCase()})
                      </option>
                    ))}
                  </select>
                  <span className="absolute right-4 top-1/2 -translate-y-1/2 text-t3 pointer-events-none font-mono text-[16px]">▾</span>
                </div>
              </div>

              {/* Deal channel */}
              <div>
                <label className="block font-mono text-[17px] text-t4 tracking-[0.18em] uppercase mb-2">
                  Dispatch Channel
                </label>
                <div className="flex gap-2">
                  {(['Email', 'DM', 'Call'] as Channel[]).map((ch) => (
                    <button
                      key={ch}
                      onClick={() => setChannel(ch)}
                      className={`flex-1 py-2 font-mono text-[17px] tracking-[0.12em] uppercase border transition-all duration-150 ${
                        channel === ch
                          ? 'bg-lime text-[#0A0A0A] border-lime font-bold'
                          : 'bg-transparent text-t3 border-border hover:border-t3 hover:text-t2'
                      }`}
                    >
                      {ch}
                    </button>
                  ))}
                </div>
              </div>

              {/* CTA */}
              <button
                onClick={handleGenerate}
                disabled={!active}
                className="mt-auto w-full py-4 bg-lime text-[#0A0A0A] font-black text-[17px] tracking-[0.18em] uppercase hover:bg-lime/90 active:scale-[0.99] transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed cta-glow"
              >
                ► GENERATE PRODUCT BRIEF
              </button>
            </div>
          </div>

          {/* Right: How It Works */}
          <div className="bg-panel border border-border flex flex-col">
            <div className="px-5 py-3 border-b border-border flex items-center gap-2">
              <span className="font-mono text-[16px] text-t3 tracking-[0.2em] uppercase">How It Works</span>
            </div>

            <div className="p-5 flex flex-col gap-4 flex-1">
              {HOW_IT_WORKS.map((step) => (
                <div key={step.n} className="flex gap-4">
                  <span className="font-mono text-[28px] font-black text-lime/25 leading-none flex-shrink-0 w-9">{step.n}</span>
                  <div>
                    <div className="font-bold text-[16px] text-t1 mb-0.5">{step.title}</div>
                    <div className="text-[17px] text-t3 leading-[1.55]">{step.body}</div>
                  </div>
                </div>
              ))}

              {/* Product lines inset */}
              <div className="mt-auto border border-border bg-[#0C0F0F] p-4">
                <div className="font-mono text-[17px] text-t4 tracking-[0.2em] uppercase mb-3">Available Product Lines</div>
                <div className="flex flex-col gap-2">
                  {data.product_lines.map((pl) => (
                    <div key={pl.id} className="flex items-start gap-3">
                      <span className="font-mono text-[16px] text-lime font-bold w-20 flex-shrink-0">{pl.id}</span>
                      <span className="font-mono text-[16px] text-t3 leading-[1.4]">{pl.desc}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── BOTTOM ROW: TELEMETRY CONSOLE ────────────────────────── */}
        <div className="bg-panel border border-border flex flex-col flex-1 min-h-0">

          {/* Console header */}
          <div className="px-5 py-3 border-b border-border flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex gap-1.5">
                <span className="w-3 h-3 rounded-full bg-[#FF5F57]" />
                <span className="w-3 h-3 rounded-full bg-[#FFBD2E]" />
                <span className="w-3 h-3 rounded-full bg-[#27C840]" />
              </div>
              <span className="font-mono text-[16px] text-t3 tracking-[0.18em] uppercase ml-2">
                Product Brief
                {active && generated && (
                  <span className="text-lime"> — {active.creator_name}</span>
                )}
              </span>
            </div>
            <div className="flex items-center gap-3">
              {generated && (
                <span className="font-mono text-[17px] text-lime tracking-[0.14em] uppercase flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-lime animate-pulse-dot" />
                  Ready
                </span>
              )}
              <button
                onClick={handleCopy}
                disabled={!generated}
                className={`font-mono text-[16px] tracking-[0.14em] uppercase px-3 py-1.5 border transition-all duration-150 ${
                  copied
                    ? 'bg-lime/15 border-lime/40 text-lime'
                    : 'border-border text-t3 hover:border-t3 hover:text-t1 disabled:opacity-30 disabled:cursor-not-allowed'
                }`}
              >
                {copied ? '✓ COPIED' : 'COPY'}
              </button>
            </div>
          </div>

          {/* Monospace output */}
          <div className="flex-1 bg-[#0C0F0F] overflow-auto p-6 min-h-0">
            {generated && output ? (
              <pre className="font-mono text-[17px] leading-[1.7] text-t2 whitespace-pre">
                {output.split('\n').map((line, i) => {
                  const isDiv     = line.startsWith('═')
                  const isSub     = line.startsWith('─')
                  const isHeader  = i === 1
                  const isSection = isSub
                    ? false
                    : /^[A-Z][A-Z ]+$/.test(line.trim()) && line.trim().length > 2
                  return (
                    <span
                      key={i}
                      className={`block ${
                        isDiv     ? 'text-lime/40' :
                        isSub     ? 'text-t4'      :
                        isHeader  ? 'text-lime font-bold' :
                        isSection ? 'text-lime/80 font-semibold' :
                        ''
                      }`}
                    >
                      {line || ' '}
                    </span>
                  )
                })}
              </pre>
            ) : (
              <div className="h-full flex flex-col items-center justify-center gap-3 select-none">
                <span className="font-mono text-[17px] text-t4 tracking-[0.2em] uppercase">
                  {!active ? 'No creators loaded' : 'Select a creator and press GENERATE'}
                </span>
                <span className="font-mono text-[32px] text-t4/20">{'// awaiting input'}</span>
              </div>
            )}
          </div>
        </div>

      </div>
    </AppShell>
  )
}
