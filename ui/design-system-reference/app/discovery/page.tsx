'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AppShell } from '@/components/app-shell'
import { PlayIcon, YouTubeIcon, InstagramIcon, TikTokIcon, ArrowRightIcon } from '@/components/icons'

interface Social {
  kind: 'youtube' | 'instagram' | 'tiktok'
  label: string
  count: string
  er?: string
}

interface Creator {
  id: string
  handle: string
  youtube_channel_url: string
  name: string
  sub: string
  niche: string
  cat: string
  content_style: string
  followers: string
  engagement: string
  posts: string
  gfs: string
  gfsClass: string
  gfs_tier: string
  auth_score: number
  sentiment: string
  risk_level: string
  img: string
  cover: string
  socials: Social[]
  status: string
  recommendation: string
  brand_safety: string
  signals: string[]
}

const normalizeCreator = (raw: any): Creator => {
  const gfsValue = Number(raw.gfs ?? raw.gymshark_brand_fit ?? raw.score ?? 0)
  const gfsTier = gfsValue >= 7 ? 'GREEN' : gfsValue >= 5.5 ? 'AMBER' : 'RED'
  const handle = String(raw.handle || raw.youtube_handle || '@creator')
  const name = String(raw.name || 'Creator')
  const niche = String(raw.niche || 'General Fitness')
  const contentStyle = String(raw.content_style || 'Fitness Content')
  const subscribers = Number(raw.subscribers ?? raw.sub ?? 0)
  const followers = String(raw.followers ?? raw.subscribers_fmt ?? `${subscribers}`)
  const engagementScore = Number(raw.engagement ?? raw.engagement_score ?? 0)
  const authScore = Number(raw.auth_score ?? raw.authenticity_score ?? 0)
  const sentimentScore = Number(raw.sentiment ?? raw.sentiment_positive_pct ?? 0)

  return {
    id: String(raw.id ?? raw.creator_id ?? handle),
    handle,
    youtube_channel_url:
      raw.youtube_channel_url ||
      `https://www.youtube.com/${handle.replace(/^@/, '')}`,
    name,
    sub: String(raw.sub ?? subscribers ?? '0'),
    niche,
    cat: niche,
    content_style: contentStyle,
    followers,
    engagement: String(raw.engagement ?? `${engagementScore.toFixed(1)}%` ?? '—'),
    posts: String(raw.posts ?? raw.video_count ?? '—'),
    gfs: String(raw.gfs ?? gfsValue.toFixed(1)),
    gfsClass: gfsTier === 'AMBER' ? 'amber' : 'lime',
    gfs_tier: gfsTier,
    auth_score: authScore,
    sentiment: String(raw.sentiment ?? `${sentimentScore.toFixed(0)}%`),
    risk_level: String(raw.risk_level ?? 'UNKNOWN'),
    img:
      raw.img ||
      `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(name)}`,
    cover:
      raw.cover ||
      'https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=1200&q=80',
    socials: [
      {
        kind: 'youtube',
        label: handle,
        count: followers,
        er: raw.engagement_score ? `${Number(raw.engagement_score).toFixed(1)}%` : undefined,
      },
    ],
    status: String(raw.status ?? (raw.outreach_recommended ? 'responded' : 'no_reply')),
    recommendation: String(
      raw.recommendation ??
        (raw.outreach_recommended ? 'Recommended for outreach' : 'Hold for human review')
    ),
    brand_safety: String(raw.brand_safety ?? 'GREEN'),
    signals:
      Array.isArray(raw.signals) && raw.signals.length > 0
        ? raw.signals
        : [
            `#${niche.toUpperCase().replace(/\s+/g, '_')}`,
            `GFS: ${gfsValue.toFixed(1)}`,
            `AUTH: ${authScore.toFixed(1)}`,
            `RISK: ${String(raw.risk_level ?? 'UNKNOWN')}`,
          ],
  }
}

const CRM_TIERS = [
  { id: '1', label: '1. Seeded Creator' },
  { id: '2', label: '2. Ambassador' },
  { id: '3', label: '3. Core Athlete' },
]

const SocialIcon = ({ kind }: { kind: 'youtube' | 'instagram' | 'tiktok' }) => {
  switch (kind) {
    case 'youtube':   return <YouTubeIcon className="w-3.5 h-3.5" />
    case 'instagram': return <InstagramIcon className="w-3.5 h-3.5" />
    case 'tiktok':    return <TikTokIcon className="w-3.5 h-3.5" />
  }
}

export default function DiscoveryPage() {
  const router = useRouter()
  const [creators, setCreators] = useState<Creator[]>([])
  const [loading, setLoading] = useState(true)
  const [activeCreator, setActiveCreator] = useState<Creator | null>(null)
  const [filterNiche, setFilterNiche] = useState('all')
  const [filterGender, setFilterGender] = useState('all')
  const [activeTier, setActiveTier] = useState('1')
  const [ladderOpen, setLadderOpen] = useState(true)
  const [activeTab, setActiveTab] = useState('recent')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  useEffect(() => {
    fetch('/api/creators')
      .then((r) => r.json())
      .then((data: any[]) => {
        const normalized = data.map(normalizeCreator)
        setCreators(normalized)
        if (normalized.length) setActiveCreator(normalized[0])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const nicheOptions = Array.from(new Set(creators.map((c) => c.niche).filter(Boolean))).sort()

  const filteredCreators = creators.filter((c) => {
    if (filterNiche !== 'all' && c.niche !== filterNiche) return false
    return true
  })

  const toggleSelect = (e: { stopPropagation: () => void }, id: string) => {
    e.stopPropagation()
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleOutreach = () => {
    if (selectedIds.size > 0) {
      localStorage.setItem('gymshark-nexus-selected-creators', JSON.stringify([...selectedIds]))
    } else {
      localStorage.removeItem('gymshark-nexus-selected-creators')
    }
    router.push('/outreach')
  }

  if (loading) {
    return (
      <AppShell currentPage="Discovery">
        <div className="flex items-center justify-center h-[calc(100vh-52px)]">
          <div className="font-mono text-[17px] text-t3 tracking-[0.14em] uppercase flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-lime animate-pulse-dot" />
            Loading pipeline data…
          </div>
        </div>
      </AppShell>
    )
  }

  if (!activeCreator) {
    return (
      <AppShell currentPage="Discovery">
        <div className="flex items-center justify-center h-[calc(100vh-52px)]">
          <div className="font-mono text-[17px] text-t3 tracking-[0.14em] uppercase">No creators found in pipeline.</div>
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell currentPage="Discovery">
      <div className="grid grid-cols-[280px_1fr_340px] h-[calc(100vh-52px)]">

        {/* Column 1: Creator Shortlist Queue */}
        <section className="border-r border-border flex flex-col overflow-hidden">
          <div className="p-4 border-b border-border bg-panel-2">
            <div className="font-bold text-[17px] text-t1 tracking-[0.12em] uppercase mb-1">
              Creator Shortlist Queue
            </div>
            <div className="font-mono text-[14px] text-t3 tracking-[0.06em] uppercase">
              {filteredCreators.length} creators · AI-scored
            </div>
          </div>

          {/* Filters */}
          <div className="p-3 border-b border-border bg-panel flex gap-2">
            <div className="flex-1">
              <label className="block font-mono text-[17px] text-t3 tracking-[0.1em] uppercase mb-1">Niche</label>
              <select
                value={filterNiche}
                onChange={(e) => setFilterNiche(e.target.value)}
                className="w-full bg-panel-2 border border-border rounded px-2 py-1.5 text-[17px] text-t1 font-medium focus:border-lime focus:outline-none"
              >
                <option value="all">All Niches</option>
                {nicheOptions.map((cat) => (
                  <option key={cat} value={cat}>{cat.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}</option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label className="block font-mono text-[17px] text-t3 tracking-[0.1em] uppercase mb-1">Outreach</label>
              <select
                value={filterGender}
                onChange={(e) => setFilterGender(e.target.value)}
                className="w-full bg-panel-2 border border-border rounded px-2 py-1.5 text-[17px] text-t1 font-medium focus:border-lime focus:outline-none"
              >
                <option value="all">All</option>
                <option value="responded">Responded</option>
                <option value="no_reply">No Reply</option>
              </select>
            </div>
          </div>

          {/* Select all row */}
          {(() => {
            const visible = filteredCreators.filter((c) => filterGender === 'all' || c.status === filterGender)
            const allSelected = visible.length > 0 && visible.every((c) => selectedIds.has(c.id))
            return (
              <div className="px-3 py-2 border-b border-border flex items-center justify-between bg-panel">
                <button
                  onClick={() => {
                    if (allSelected) {
                      setSelectedIds((prev) => {
                        const next = new Set(prev)
                        visible.forEach((c) => next.delete(c.id))
                        return next
                      })
                    } else {
                      setSelectedIds((prev) => {
                        const next = new Set(prev)
                        visible.forEach((c) => next.add(c.id))
                        return next
                      })
                    }
                  }}
                  className="flex items-center gap-2 group"
                >
                  <div className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-all duration-150 ${
                    allSelected ? 'bg-lime border-lime' : 'border-border group-hover:border-lime/60'
                  }`}>
                    {allSelected && (
                      <svg className="w-2.5 h-2.5 text-[#0A0A0A]" viewBox="0 0 10 10" fill="none">
                        <path d="M1.5 5L4 7.5L8.5 2.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    )}
                  </div>
                  <span className="font-mono text-[11px] text-t3 tracking-[0.1em] uppercase group-hover:text-t1 transition-colors">
                    {allSelected ? 'Deselect All' : 'Select All'}
                  </span>
                </button>
                {selectedIds.size > 0 && (
                  <span className="font-mono text-[11px] text-lime tracking-[0.1em] uppercase">
                    {selectedIds.size} selected
                  </span>
                )}
              </div>
            )
          })()}

          {/* Queue */}
          <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
            {filteredCreators
              .filter((c) => filterGender === 'all' || c.status === filterGender)
              .map((creator) => {
                const selected = selectedIds.has(creator.id)
                return (
                  <button
                    key={creator.id}
                    onClick={() => setActiveCreator(creator)}
                    className={`w-full text-left p-3 rounded-lg border transition-all duration-200 ${
                      activeCreator?.id === creator.id
                        ? 'bg-lime/12 border-lime card-glow-active'
                        : 'bg-panel border-border hover:bg-panel-h hover:border-t3'
                    }`}
                  >
                    <div className="flex items-start gap-2.5">
                      {/* Checkbox */}
                      <div
                        onClick={(e) => toggleSelect(e, creator.id)}
                        className={`mt-0.5 w-4 h-4 rounded flex-shrink-0 border-2 flex items-center justify-center transition-all duration-150 ${
                          selected
                            ? 'bg-lime border-lime'
                            : 'border-border hover:border-lime/60'
                        }`}
                      >
                        {selected && (
                          <svg className="w-2.5 h-2.5 text-[#0A0A0A]" viewBox="0 0 10 10" fill="currentColor">
                            <path d="M1.5 5L4 7.5L8.5 2.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
                          </svg>
                        )}
                      </div>
                      <div
                        className="w-10 h-10 rounded-full bg-cover bg-center border border-border-2 flex-shrink-0"
                        style={{ backgroundImage: `url(${creator.img})` }}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2 mb-0.5">
                          <span className="font-bold text-[17px] text-t1 truncate">{creator.handle}</span>
                          <span className={`font-mono text-[14px] font-bold ${creator.gfsClass === 'amber' ? 'text-amber' : 'text-lime'}`}>
                            {creator.gfs}
                          </span>
                        </div>
                        <div className="font-mono text-[17px] text-t3 tracking-[0.06em] uppercase truncate">
                          {creator.niche.toUpperCase()} · {creator.followers}
                        </div>
                      </div>
                    </div>
                  </button>
                )
              })}
          </div>
        </section>

        {/* Column 2: Theater */}
        <section className="border-r border-border flex flex-col overflow-hidden bg-bg">
          <div className="p-4 border-b border-border bg-panel-2">
            <div className="font-bold text-[17px] text-t1 tracking-[0.12em] uppercase mb-1">
              Content Theater
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-5">
            {/* Theater Title */}
            <div className="mb-4">
              <a
                href={activeCreator.youtube_channel_url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-black text-[30px] text-lime leading-tight tracking-[-0.01em] hover:underline inline-flex items-center gap-2 group"
              >
                {activeCreator.handle}
                <YouTubeIcon className="w-5 h-5 opacity-60 group-hover:opacity-100 transition-opacity" />
              </a>
              <div className="text-[14px] text-t2">
                {activeCreator.name} · {activeCreator.niche} · {activeCreator.content_style}
              </div>
            </div>

            {/* Cover Image / Channel Banner */}
            <div className="relative aspect-[21/9] max-h-[340px] w-full bg-panel rounded-lg overflow-hidden mb-4 group">
              <div
                className="absolute inset-0 bg-cover bg-center"
                style={{ backgroundImage: `url(${activeCreator.cover})` }}
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
              {/* Crosshair guides */}
              <div className="absolute inset-0 pointer-events-none">
                <div className="absolute top-1/2 left-0 right-0 h-px bg-lime/20" />
                <div className="absolute left-1/2 top-0 bottom-0 w-px bg-lime/20" />
                <div className="absolute top-4 left-4 w-4 h-4 border-l-2 border-t-2 border-lime/50" />
                <div className="absolute top-4 right-4 w-4 h-4 border-r-2 border-t-2 border-lime/50" />
                <div className="absolute bottom-4 left-4 w-4 h-4 border-l-2 border-b-2 border-lime/50" />
                <div className="absolute bottom-4 right-4 w-4 h-4 border-r-2 border-b-2 border-lime/50" />
              </div>
              <a
                href={activeCreator.youtube_channel_url}
                target="_blank"
                rel="noopener noreferrer"
                className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-16 h-16 rounded-full bg-lime flex items-center justify-center text-[#0A0A0A] transition-transform duration-200 group-hover:scale-110 cta-glow"
                title={`Open ${activeCreator.handle} on YouTube`}
              >
                <PlayIcon className="w-6 h-6 ml-1" />
              </a>
            </div>

            {/* Recommendation badge */}
            <div className="flex items-center gap-3 p-3 bg-panel rounded border border-border mb-5">
              <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
                activeCreator.brand_safety === 'AMBER' ? 'bg-amber' : 'bg-lime'
              }`} />
              <div className="flex-1 min-w-0">
                <div className="font-mono text-[17px] text-t3 tracking-[0.1em] uppercase mb-0.5">AI Recommendation</div>
                <div className="text-[17px] text-t1 truncate">{activeCreator.recommendation || 'Pending evaluation'}</div>
              </div>
            </div>

            {/* Feed Tabs */}
            <div className="flex border-b border-border mb-4">
              {['recent', 'audience', 'collabs'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-4 py-2.5 font-bold text-[10.5px] tracking-[0.1em] uppercase transition-all duration-150 border-b-2 -mb-px ${
                    activeTab === tab
                      ? 'text-lime border-lime'
                      : 'text-t3 border-transparent hover:text-t1'
                  }`}
                >
                  {tab === 'recent' ? 'Recent Feed' : tab === 'audience' ? 'Audience Performance' : 'Historic Collabs'}
                </button>
              ))}
            </div>

            <div className="bg-panel border border-border rounded p-4">
              <div className="font-mono text-[14px] text-t3 tracking-[0.1em] uppercase mb-2">
                {activeTab === 'recent' ? 'Latest Content' : activeTab === 'audience' ? 'Audience Metrics' : 'Brand Collaborations'}
              </div>
              <p className="text-[17px] text-t2 leading-relaxed">
                {activeTab === 'recent' && `${activeCreator.posts} videos published. Content style: ${activeCreator.content_style}. Engagement rate: ${activeCreator.engagement}.`}
                {activeTab === 'audience' && `${activeCreator.followers} subscribers · ${activeCreator.engagement} engagement · Sentiment: ${activeCreator.sentiment}% positive · Risk: ${activeCreator.risk_level}`}
                {activeTab === 'collabs' && `Brand safety: ${activeCreator.brand_safety}. No competing brand loyalty detected. Outreach recommended per AI scoring.`}
              </p>
            </div>
          </div>
        </section>

        {/* Column 3: Insights + CRM */}
        <section className="flex flex-col overflow-hidden bg-panel">
          <div className="p-4 border-b border-border bg-panel-2">
            <div className="font-bold text-[17px] text-t1 tracking-[0.12em] uppercase mb-1">
              Creator Insights
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Creator Info Card */}
            <div className="bg-panel-2 rounded-lg border border-border p-4">
              <div className="flex items-center gap-3 mb-4">
                <a
                  href={activeCreator.youtube_channel_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-14 h-14 rounded-full bg-cover bg-center border-2 border-lime flex-shrink-0 hover:border-lime/70 transition-all"
                  style={{ backgroundImage: `url(${activeCreator.img})` }}
                  title={`${activeCreator.handle} on YouTube`}
                />
                <div>
                  <a
                    href={activeCreator.youtube_channel_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-bold text-[17px] text-t1 hover:text-lime transition-colors"
                  >
                    {activeCreator.handle}
                  </a>
                  <div className="text-[17px] text-t2">{activeCreator.niche}</div>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div className="bg-panel rounded p-2 text-center">
                  <div className="font-black text-[20px] text-t1">{activeCreator.followers}</div>
                  <div className="font-mono text-[14px] text-t3 tracking-[0.1em] uppercase">Followers</div>
                </div>
                <div className="bg-panel rounded p-2 text-center">
                  <div className="font-black text-[20px] text-lime">{activeCreator.engagement}</div>
                  <div className="font-mono text-[14px] text-t3 tracking-[0.1em] uppercase">Engage</div>
                </div>
                <div className="bg-panel rounded p-2 text-center">
                  <div className="font-black text-[20px] text-t1">{activeCreator.posts}</div>
                  <div className="font-mono text-[14px] text-t3 tracking-[0.1em] uppercase">Posts</div>
                </div>
              </div>
            </div>

            {/* GFS Score */}
            <div className="bg-panel-2 rounded-lg border border-border p-4">
              <div className="font-mono text-[17px] text-t3 tracking-[0.14em] uppercase mb-3">
                Gymshark Fit Score
              </div>
              <div className="flex items-center gap-4">
                <div className={`w-20 h-20 rounded-full border-4 flex items-center justify-center ${
                  activeCreator.gfs_tier === 'AMBER' ? 'border-amber' : 'border-lime'
                }`}>
                  <span className={`font-black text-[30px] ${activeCreator.gfs_tier === 'AMBER' ? 'text-amber' : 'text-lime'}`}>
                    {activeCreator.gfs}
                  </span>
                </div>
                <div className="flex-1">
                  <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-[17px] font-bold tracking-[0.1em] uppercase mb-2 ${
                    activeCreator.gfs_tier === 'AMBER' ? 'bg-amber/15 text-amber' : 'bg-lime/15 text-lime'
                  }`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${activeCreator.gfs_tier === 'AMBER' ? 'bg-amber' : 'bg-lime'} animate-pulse-dot`} />
                    {activeCreator.gfs_tier}
                  </div>
                  <div className="text-[17px] text-t2">
                    {activeCreator.gfs_tier === 'GREEN'
                      ? 'High brand alignment with Gymshark audience'
                      : 'Borderline — human review recommended'}
                  </div>
                </div>
              </div>
            </div>

            {/* AI Context Signals */}
            <div className="bg-panel-2 rounded-lg border border-border p-4">
              <div className="font-mono text-[17px] text-t3 tracking-[0.14em] uppercase mb-3">
                AI Context Signals
              </div>
              <div className="flex flex-wrap gap-1.5">
                {(activeCreator.signals && activeCreator.signals.length > 0
                  ? activeCreator.signals
                  : [
                      `#${activeCreator.niche.toUpperCase().replace(/ /g, '_')}`,
                      `GFS: ${activeCreator.gfs}`,
                      `AUTH: ${Math.round(activeCreator.auth_score * 10)}`,
                      `SENTIMENT: ${activeCreator.sentiment}%`,
                      `RISK: ${activeCreator.risk_level}`,
                    ]
                ).map((signal) => (
                  <span key={signal} className="px-2 py-1 bg-lime/10 border border-lime/20 rounded text-[17px] text-lime font-mono tracking-[0.04em]">
                    {signal}
                  </span>
                ))}
              </div>
            </div>

            {/* Social Links */}
            <div className="bg-panel-2 rounded-lg border border-border p-4">
              <div className="font-mono text-[17px] text-t3 tracking-[0.14em] uppercase mb-3">
                Social Profiles
              </div>
              <div className="space-y-2">
                {activeCreator.socials.map((social) => (
                  <a
                    key={social.label}
                    href="#"
                    className="flex items-center gap-3 p-2 bg-panel rounded border border-border hover:border-lime hover:bg-lime/5 transition-all duration-150"
                  >
                    <span className="w-7 h-7 rounded bg-lime/10 flex items-center justify-center text-lime">
                      <SocialIcon kind={social.kind} />
                    </span>
                    <div className="flex-1">
                      <div className="text-[17px] text-t1 font-medium">{social.label}</div>
                      <div className="font-mono text-[17px] text-t3">{social.count} followers{social.er ? ` · ${social.er} ER` : ''}</div>
                    </div>
                  </a>
                ))}
              </div>
            </div>

            {/* CRM Ladder */}
            <div className="bg-panel-2 rounded-lg border border-border p-4">
              <div className="font-mono text-[17px] text-t3 tracking-[0.14em] uppercase mb-3">
                CRM Ladder Progression
              </div>
              <div className={`rounded border border-border overflow-hidden ${ladderOpen ? 'bg-panel' : ''}`}>
                <button
                  onClick={() => setLadderOpen(!ladderOpen)}
                  className="w-full flex items-center justify-between p-3 bg-panel-3 hover:bg-panel-h transition-colors"
                >
                  <span className="font-bold text-[14px] text-t1">
                    {CRM_TIERS.find((t) => t.id === activeTier)?.label}
                  </span>
                  <span className={`text-lime text-[17px] transition-transform duration-200 ${ladderOpen ? 'rotate-180' : ''}`}>▼</span>
                </button>
                {ladderOpen && (
                  <div className="border-t border-border">
                    {CRM_TIERS.map((tier) => (
                      <button
                        key={tier.id}
                        onClick={() => setActiveTier(tier.id)}
                        className={`w-full text-left p-3 border-b border-border last:border-b-0 font-bold text-[14px] tracking-[0.08em] uppercase transition-all duration-150 ${
                          activeTier === tier.id
                            ? 'text-lime bg-lime-bg'
                            : 'text-t2 hover:bg-panel-h hover:text-t1'
                        }`}
                      >
                        {tier.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Move to Outreach CTA */}
          <div className="p-4 border-t border-border bg-panel flex flex-col gap-2">
            {selectedIds.size > 0 && (
              <div className="flex items-center justify-between font-mono text-[11px] text-t3 tracking-[0.1em] uppercase px-1">
                <span><span className="text-lime font-bold">{selectedIds.size}</span> creator{selectedIds.size !== 1 ? 's' : ''} selected</span>
                <button
                  onClick={() => setSelectedIds(new Set())}
                  className="text-t4 hover:text-t2 transition-colors"
                >
                  clear
                </button>
              </div>
            )}
            <button
              onClick={handleOutreach}
              className="flex items-center justify-center gap-2 w-full px-4 py-3.5 rounded-full bg-lime text-[#0A0A0A] font-black text-[14px] tracking-[0.12em] uppercase cta-glow hover:bg-lime-2 transition-colors"
            >
              <ArrowRightIcon className="w-4 h-4" />
              {selectedIds.size > 0 ? `Move ${selectedIds.size} to Outreach` : 'Move to Outreach Queue'}
            </button>
          </div>
        </section>
      </div>
    </AppShell>
  )
}
