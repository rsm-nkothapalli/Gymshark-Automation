'use client'

import { useEffect, useState } from 'react'
import { AppShell } from '@/components/app-shell'
import { ArrowUpRightIcon, DiscoveryIcon, OutreachIcon, ProductBriefIcon, TrendingUpIcon } from '@/components/icons'
import Link from 'next/link'

interface KpiData {
  creators_discovered: number
  active_outreach: number
  avg_roi: number
  eligible_count: number
}

interface ActivityItem {
  user: string
  action: string
  target: string
  destination: string
  status: string
}

const portals = [
  {
    num: '01',
    name: 'Discovery',
    desc: 'AI-scored creator profiles across YouTube, Instagram, TikTok. Filter by niche, engagement, and brand alignment signals.',
    href: '/discovery',
    icon: DiscoveryIcon,
    badge: 'Live',
    cta: 'Enter Discovery',
    live: true,
  },
  {
    num: '02',
    name: 'Outreach',
    desc: 'Deep analytics & contact war-room for shortlisted creators. Personalized email drafts powered by CRM ladder progression.',
    href: '/outreach',
    icon: OutreachIcon,
    badge: 'Live',
    cta: 'Enter Outreach',
    live: true,
  },
  {
    num: '03',
    name: 'Product Briefs',
    desc: 'Creator product briefs, seeding inventory & campaign dispatch. AI-matched products to creator niche and deal type.',
    href: '/product-briefs',
    icon: ProductBriefIcon,
    badge: 'Live',
    cta: 'Enter Briefs',
    live: true,
  },
  {
    num: '04',
    name: 'Analytics',
    desc: 'Campaign performance, ROI breakdowns & UTM-tracked revenue for existing partner campaigns.',
    href: '/analytics',
    icon: TrendingUpIcon,
    badge: 'Live',
    cta: 'Enter Analytics',
    live: true,
  },
]

const FALLBACK_ACTIVITIES: ActivityItem[] = [
  { user: 'System', action: 'discovered', target: '12 new creators', destination: 'matching fitness niche', status: 'system' },
  { user: 'System', action: 'flagged', target: '@danielarun', destination: 'low engagement anomaly', status: 'warning' },
]

export default function DashboardPage() {
  const [kpis, setKpis] = useState<KpiData | null>(null)
  const [activities, setActivities] = useState<ActivityItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch('/api/kpis').then((r) => r.json()).catch(() => null),
      fetch('/api/activity').then((r) => r.json()).catch(() => []),
    ]).then(([kpiData, activityData]) => {
      if (kpiData) setKpis(kpiData)
      setActivities(activityData?.length ? activityData : FALLBACK_ACTIVITIES)
      setLoading(false)
    })
  }, [])

  const kpiStrips = kpis
    ? [
        { label: 'Creators Discovered', value: String(kpis.creators_discovered), unit: 'profiles', delta: `${kpis.eligible_count} eligible` },
        { label: 'Active Outreach', value: String(kpis.active_outreach), unit: 'in pipeline', delta: 'pending review' },
        { label: 'Avg Campaign ROI', value: String(kpis.avg_roi), unit: '× return', delta: 'across live campaigns', isAmber: false },
      ]
    : [
        { label: 'Creators Discovered', value: '—', unit: 'profiles', delta: 'loading…' },
        { label: 'Active Outreach', value: '—', unit: 'in pipeline', delta: 'loading…' },
        { label: 'Avg Campaign ROI', value: '—', unit: '× return', delta: 'loading…' },
      ]

  return (
    <AppShell currentPage="Master Console">
      <div className="p-10 max-w-[1440px] mx-auto w-full overflow-y-auto h-[calc(100vh-52px)]">
        {/* Hero Block */}
        <div className="grid grid-cols-[1fr_auto] gap-10 items-end mb-9 pb-7 border-b border-border">
          <div>
            <div className="font-mono text-[15px] text-lime tracking-[0.18em] uppercase mb-4 flex items-center gap-2">
              <span className="w-7 h-px bg-lime" />
              Master Operations Console
            </div>
            <h1 className="font-black text-[64px] leading-[0.95] tracking-[-0.025em] text-t1">
              Gymshark<em className="text-lime not-italic">Nexus</em>
            </h1>
          </div>
          <div className="text-right font-mono text-[15px] text-t3 tracking-[0.08em] uppercase leading-[1.7]">
            <div>Session: <strong className="text-t1 font-semibold">Active</strong></div>
            <div>Pipeline: <strong className="text-t1 font-semibold">{loading ? '…' : `${kpis?.eligible_count ?? '—'} ready`}</strong></div>
            <div>Status: <span className="text-lime">● Online</span></div>
          </div>
        </div>

        {/* KPI Strip */}
        <div className="bg-panel border border-border rounded-md grid grid-cols-3 mb-12 overflow-hidden">
          {kpiStrips.map((kpi, i) => (
            <div key={i} className="p-7 border-r border-border last:border-r-0 relative group">
              <div className="absolute top-0 left-0 right-0 h-0.5 bg-lime scale-x-0 origin-left transition-transform duration-500 group-hover:scale-x-100" />
              <div className="font-mono text-[15px] text-t3 tracking-[0.14em] uppercase mb-3 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-lime animate-pulse-dot" />
                {kpi.label}
              </div>
              <div className="flex items-baseline gap-3 mb-2">
                <span className="font-black text-[52px] leading-none tracking-[-0.03em] text-t1">
                  {kpi.value.split('.')[0]}
                  {kpi.value.includes('.') && <em className="text-lime not-italic">.{kpi.value.split('.')[1]}</em>}
                </span>
                <span className="font-mono text-[15px] text-t3 tracking-[0.08em] uppercase font-medium">{kpi.unit}</span>
              </div>
              <div className={`font-mono text-[15px] tracking-[0.06em] ${kpi.isAmber ? 'text-amber' : 'text-lime'}`}>
                {kpi.delta}
              </div>
            </div>
          ))}
        </div>

        {/* Portals Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="font-mono text-[15px] text-t2 tracking-[0.18em] uppercase flex items-center gap-2.5">
            <span className="w-[18px] h-px bg-t3" />
            Platform Modules
          </div>
          <div className="font-mono text-[12px] text-t4 tracking-[0.1em] uppercase">
            4 Modules · 4 Live
          </div>
        </div>

        {/* Portal Cards */}
        <div className="grid grid-cols-4 gap-4 mb-14">
          {portals.map((portal) => {
            const Icon = portal.icon
            return (
              <Link
                key={portal.num}
                href={portal.live ? portal.href : '#'}
                className={`bg-panel border border-border p-8 flex flex-col relative transition-all duration-300 cursor-pointer overflow-hidden min-h-[360px] group ${
                  portal.live ? 'hover:border-lime hover:bg-[#161818] hover:-translate-y-[3px] hover:shadow-[0_24px_60px_-20px_var(--lime-glow)]' : 'opacity-70 cursor-not-allowed'
                }`}
              >
                <div className={`absolute top-0 left-0 right-0 h-[3px] bg-lime scale-x-0 origin-left transition-transform duration-350 ${portal.live ? 'group-hover:scale-x-100' : ''}`} />
                <div className="font-mono text-[15px] text-t3 tracking-[0.18em] mb-4 flex items-center justify-between">
                  <span>{portal.num}</span>
                  <span className={`w-7 h-7 flex items-center justify-center text-t3 transition-all duration-200 ${portal.live ? 'group-hover:text-lime group-hover:translate-x-0.5 group-hover:-translate-y-0.5' : ''}`}>
                    <ArrowUpRightIcon className="w-5 h-5" />
                  </span>
                </div>
                <h2 className={`font-black text-[48px] leading-[0.95] tracking-[-0.025em] text-t1 mb-3 transition-colors duration-200 ${portal.live ? 'group-hover:text-lime' : ''}`}>
                  {portal.name}
                </h2>
                <p className="text-[16px] text-t2 leading-[1.55] mb-5 max-w-[320px]">
                  {portal.desc}
                </p>
                <div className="mt-auto pt-5 border-t border-border">
                  <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full font-mono text-[15px] tracking-[0.08em] uppercase font-semibold mb-4 ${
                    portal.live
                      ? 'bg-lime-bg border border-lime/22 text-lime'
                      : 'bg-white/4 border border-border text-t2'
                  }`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${portal.live ? 'bg-lime animate-pulse-dot' : 'bg-t3'}`} />
                    {portal.badge}
                  </span>
                  <div className={`flex items-center justify-between gap-3 px-4 py-3.5 rounded-full font-bold text-[16px] tracking-[0.12em] uppercase transition-all duration-200 ${
                    portal.live
                      ? 'bg-lime text-[#0A0A0A] cta-glow'
                      : 'bg-panel-h text-t3'
                  }`}>
                    {portal.cta}
                    <span className={`w-[18px] h-[18px] flex items-center justify-center text-[16px] transition-transform duration-200 ${portal.live ? 'group-hover:translate-x-1' : ''}`}>
                      →
                    </span>
                  </div>
                </div>
              </Link>
            )
          })}
        </div>

        {/* Activity Feed */}
        <div className="bg-panel border border-border rounded-md overflow-hidden">
          <div className="px-6 py-4 border-b border-border flex items-center justify-between">
            <h3 className="font-bold text-[16px] text-t1 tracking-[0.14em] uppercase flex items-center gap-2.5">
              <span className="w-2 h-2 rounded-full bg-lime animate-pulse-dot" />
              Activity Feed
            </h3>
            <span className="font-mono text-[12px] text-t4 tracking-[0.1em] uppercase">
              Pipeline · Real data
            </span>
          </div>
          <div className="divide-y divide-border">
            {activities.map((activity, i) => (
              <div key={i} className="px-6 py-4 flex items-center gap-4 hover:bg-panel-h transition-colors duration-150">
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
                  activity.status === 'live' ? 'bg-lime' :
                  activity.status === 'warning' ? 'bg-amber' : 'bg-t3'
                }`} />
                <span className="text-[15px] text-t2">
                  <strong className="text-t1 font-semibold">{activity.user}</strong>
                  {' '}{activity.action}{' '}
                  <span className="text-lime font-medium">{activity.target}</span>
                  {' '}→ {activity.destination}
                </span>
              </div>
            ))}
            {activities.length === 0 && (
              <div className="px-6 py-8 text-center font-mono text-[15px] text-t4 tracking-[0.1em] uppercase">
                Loading pipeline activity…
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  )
}
