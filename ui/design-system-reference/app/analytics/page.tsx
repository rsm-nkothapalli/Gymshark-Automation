'use client'

import { useEffect, useState } from 'react'
import { AppShell } from '@/components/app-shell'

interface CreatorRow {
  name: string
  niche: string
  tier: string
  deal_type: string
  roi: number
  roi_fmt: string
  revenue_fmt: string
  conv_fmt: string
  renewal: string
}

interface TierRow {
  tier: string
  roi_fmt: string
  revenue_fmt: string
  campaigns: number
}

interface Summary {
  total_revenue: string
  overall_roi: string
  total_reach: string
  active_partners: number
  total_campaigns: number
}

interface AnalyticsData {
  summary: Summary
  top_performers: CreatorRow[]
  tier_breakdown: TierRow[]
}

const TIER_PILL: Record<string, string> = {
  micro: 'bg-lime/15 text-lime border border-lime/30',
  mid:   'bg-amber/15 text-amber border border-amber/30',
  macro: 'bg-orange-400/15 text-orange-400 border border-orange-400/30',
  mega:  'bg-red-400/15 text-red-400 border border-red-400/30',
}

const TIER_DOT: Record<string, string> = {
  micro: 'bg-lime',
  mid:   'bg-amber',
  macro: 'bg-orange-400',
  mega:  'bg-red-400',
}

function TierPill({ tier }: { tier: string }) {
  const cls = TIER_PILL[tier.toLowerCase()] ?? 'bg-t3/15 text-t2 border border-t3/25'
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 font-mono text-[17px] tracking-[0.1em] uppercase font-bold ${cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${TIER_DOT[tier.toLowerCase()] ?? 'bg-t3'}`} />
      {tier.toUpperCase()}
    </span>
  )
}

const KPI_CARDS = [
  { label: 'Total Revenue',    unit: 'Attributed',    key: 'total_revenue'   as const },
  { label: 'Overall ROI',      unit: 'All Campaigns', key: 'overall_roi'     as const },
  { label: 'Total Reach',      unit: 'Unique Viewers',key: 'total_reach'     as const },
  { label: 'Active Partners',  unit: '',              key: 'active_partners' as const, sub: 'total_campaigns' as const },
]

export default function AnalyticsPage() {
  const [data, setData]     = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/analytics')
      .then((r) => r.json())
      .then((d: AnalyticsData) => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <AppShell currentPage="analytics">
        <div className="flex items-center justify-center h-[calc(100vh-52px)]">
          <div className="font-mono text-[17px] text-t3 tracking-[0.14em] uppercase flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-lime animate-pulse-dot" />
            Loading analytics…
          </div>
        </div>
      </AppShell>
    )
  }

  if (!data) {
    return (
      <AppShell currentPage="analytics">
        <div className="flex items-center justify-center h-[calc(100vh-52px)]">
          <div className="font-mono text-[17px] text-t3 tracking-[0.14em] uppercase">No analytics data found.</div>
        </div>
      </AppShell>
    )
  }

  const { summary, top_performers, tier_breakdown } = data

  return (
    <AppShell currentPage="analytics">
      <div className="h-[calc(100vh-52px)] flex flex-col overflow-hidden">

        {/* ── HEADER SUB-BAR ───────────────────────────────────────── */}
        <div className="flex-shrink-0 border-b border-border bg-panel px-6 py-3 flex items-center justify-between">
          <div className="font-mono text-[16px] text-t3 tracking-[0.18em] uppercase flex items-center gap-3">
            <span className="text-lime font-bold">SKILL 04</span>
            <span className="text-t4">—</span>
            <span>CAMPAIGN ANALYTICS</span>
            <span className="text-t4">//</span>
            <span className="text-t2">Performance Overview</span>
            <span className="text-t4">//</span>
            <span className="text-t4">Existing partner campaigns · UTM-tracked revenue</span>
          </div>
          <div className="flex items-center gap-2 font-mono text-[17px] text-lime tracking-[0.14em] uppercase">
            <span className="w-1.5 h-1.5 rounded-full bg-lime animate-pulse-dot" />
            Live Data
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-5">

          {/* ── KPI STRIP ──────────────────────────────────────────── */}
          <div className="grid grid-cols-4 gap-4 flex-shrink-0">
            {KPI_CARDS.map((card) => {
              const value = String(summary[card.key])
              return (
                <div key={card.label} className="bg-panel border border-border p-5 relative group overflow-hidden">
                  <div className="absolute top-0 left-0 right-0 h-[2px] bg-lime scale-x-0 origin-left transition-transform duration-500 group-hover:scale-x-100" />
                  <div className="font-mono text-[16px] text-t3 tracking-[0.16em] uppercase mb-3 flex items-center gap-2">
                    <span className="w-1 h-1 rounded-full bg-lime" />
                    {card.label}
                  </div>
                  <div className="font-black text-[46px] leading-none tracking-[-0.03em] text-t1 mb-1">
                    {value}
                  </div>
                  <div className="font-mono text-[16px] text-t4 tracking-[0.1em] uppercase">
                    {card.sub
                      ? `${summary[card.sub]} Campaigns`
                      : card.unit}
                  </div>
                </div>
              )
            })}
          </div>

          {/* ── BOTTOM ROW 65 / 35 ─────────────────────────────────── */}
          <div className="grid grid-cols-[65fr_35fr] gap-4 flex-1 min-h-0">

            {/* ── LEFT: TOP PERFORMERS ─────────────────────────────── */}
            <div className="bg-panel border border-border flex flex-col min-h-0 overflow-hidden">
              <div className="flex-shrink-0 px-5 py-3 border-b border-border flex items-center justify-between">
                <div className="font-mono text-[16px] text-t3 tracking-[0.18em] uppercase flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full bg-lime" />
                  Top Performers
                </div>
                <span className="font-mono text-[17px] text-t4 tracking-[0.1em] uppercase">Ranked by ROI</span>
              </div>

              {/* Table header */}
              <div className="flex-shrink-0 grid grid-cols-[2fr_1.2fr_90px_100px_70px_80px_70px_60px] gap-x-4 px-5 py-2.5 border-b border-border bg-[#0C0F0F]">
                {['Creator', 'Niche', 'Tier', 'Deal', 'ROI', 'Revenue', 'Conv.', 'Renew'].map((h) => (
                  <span key={h} className="font-mono text-[17px] text-t4 tracking-[0.14em] uppercase">{h}</span>
                ))}
              </div>

              {/* Table rows */}
              <div className="flex-1 overflow-y-auto divide-y divide-border">
                {top_performers.map((creator, i) => (
                  <div
                    key={creator.name}
                    className="grid grid-cols-[2fr_1.2fr_90px_100px_70px_80px_70px_60px] gap-x-4 px-5 py-3 items-center hover:bg-panel-h transition-colors duration-100"
                  >
                    {/* Creator */}
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span className="font-mono text-[17px] text-t4 w-5 flex-shrink-0">{String(i + 1).padStart(2, '0')}</span>
                      <span className="font-semibold text-[16px] text-t1 truncate">{creator.name}</span>
                    </div>
                    {/* Niche */}
                    <span className="text-[17px] text-t3 truncate">{creator.niche}</span>
                    {/* Tier */}
                    <TierPill tier={creator.tier} />
                    {/* Deal */}
                    <span className="font-mono text-[17px] text-t3 tracking-[0.06em] truncate">{creator.deal_type}</span>
                    {/* ROI */}
                    <span className="font-mono text-[16px] text-lime font-bold">{creator.roi_fmt}</span>
                    {/* Revenue */}
                    <span className="font-mono text-[17px] text-t2">{creator.revenue_fmt}</span>
                    {/* Conv */}
                    <span className="font-mono text-[17px] text-t2">{creator.conv_fmt}</span>
                    {/* Renew */}
                    <span className={`font-mono text-[17px] tracking-[0.08em] uppercase ${creator.renewal === 'Yes' ? 'text-lime' : 'text-amber'}`}>
                      {creator.renewal === 'Yes' ? '✓ YES' : '✗ NO'}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* ── RIGHT: ROI BY TIER ───────────────────────────────── */}
            <div className="bg-panel border border-border flex flex-col min-h-0 overflow-hidden">
              <div className="flex-shrink-0 px-5 py-3 border-b border-border">
                <div className="font-mono text-[16px] text-t3 tracking-[0.18em] uppercase flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full bg-lime" />
                  ROI by Tier
                </div>
              </div>

              {/* Table header */}
              <div className="flex-shrink-0 grid grid-cols-[100px_1fr_1fr_1fr] gap-x-4 px-5 py-2.5 border-b border-border bg-[#0C0F0F]">
                {['Tier', 'Avg ROI', 'Revenue', 'Campaigns'].map((h) => (
                  <span key={h} className="font-mono text-[17px] text-t4 tracking-[0.14em] uppercase">{h}</span>
                ))}
              </div>

              {/* Tier rows */}
              <div className="flex-1 divide-y divide-border">
                {tier_breakdown.map((t) => (
                  <div key={t.tier} className="grid grid-cols-[100px_1fr_1fr_1fr] gap-x-4 px-5 py-4 items-center hover:bg-panel-h transition-colors duration-100">
                    <TierPill tier={t.tier} />
                    <span className="font-mono text-[17px] text-lime font-bold">{t.roi_fmt}</span>
                    <span className="font-mono text-[17px] text-t2">{t.revenue_fmt}</span>
                    <span className="font-mono text-[17px] text-t3">{t.campaigns}</span>
                  </div>
                ))}
              </div>

              {/* Bottom summary inset */}
              <div className="flex-shrink-0 border-t border-border bg-[#0C0F0F] px-5 py-4 mt-auto">
                <div className="font-mono text-[17px] text-t4 tracking-[0.16em] uppercase mb-3">Portfolio Summary</div>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { label: 'Total Revenue',  value: summary.total_revenue },
                    { label: 'Blended ROI',    value: summary.overall_roi },
                    { label: 'Total Reach',    value: summary.total_reach },
                    { label: 'Campaigns',      value: String(summary.total_campaigns) },
                  ].map((item) => (
                    <div key={item.label}>
                      <div className="font-mono text-[16px] text-t4 tracking-[0.12em] uppercase mb-0.5">{item.label}</div>
                      <div className="font-black text-[20px] text-t1 leading-none">{item.value}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>
    </AppShell>
  )
}
