'use client'

import { useCallback, useEffect, useState } from 'react'
import { AppShell } from '@/components/app-shell'
import { SendIcon, YouTubeIcon, InstagramIcon, TikTokIcon } from '@/components/icons'

interface Social {
  kind: 'youtube' | 'instagram' | 'tiktok'
  label: string
  count: string
  er?: string
}

interface Breakdown {
  authenticity: number
  niche: number
  engagement: number
  sentiment: number
  // legacy aliases
  visual: number
  quality: number
  cadence: number
}

interface Projections {
  reach: string
  conv: string
  roi: string
}

interface Creator {
  id: string
  handle: string
  name: string
  sub: string
  niche: string
  tagline: string
  gfs: string
  gfs_tier: 'GREEN' | 'AMBER'
  status: 'ready' | 'review' | 'drafting' | 'responded' | 'no_reply'
  img: string
  followers: string
  engagement: string
  auth: string
  sentiment: string
  breakdown: Breakdown
  projections: Projections
  socials: Social[]
  responded?: boolean
  response_date?: string
  response_notes?: string
  outreach_sent_date?: string
  account_manager?: string
  outreach_channel?: string
  follow_up_date?: string
  proposed_next_step?: string
  priority?: string
  signals?: string[]
}

interface DraftResponse {
  draft: string
  word_count: number
  tier: string
  label: string
  type: string
  llm_generated: boolean
}

const TIER_META: Record<string, { label: string; type: string }> = {
  '1': { label: 'Seeded Creator', type: 'Gift Seeding' },
  '2': { label: 'Ambassador',     type: 'Ambassador Track' },
  '3': { label: 'Core Athlete',   type: 'Core Roster Pitch' },
}

const STATUS_LABELS: Record<string, { lbl: string; cls: string }> = {
  ready:     { lbl: 'Ready to Contact', cls: 'bg-lime/15 text-lime border-lime/25' },
  review:    { lbl: 'Human Review',     cls: 'bg-amber/15 text-amber border-amber/25' },
  drafting:  { lbl: 'Drafting',         cls: 'bg-t3/15 text-t2 border-t3/25' },
  responded: { lbl: 'Responded',        cls: 'bg-lime/15 text-lime border-lime/25' },
  no_reply:  { lbl: 'No Reply',         cls: 'bg-t4/30 text-t3 border-t4/25' },
}

const normalizeCreator = (raw: any): Creator => {
  const gfsValue = Number(raw.gfs ?? raw.gymshark_brand_fit ?? 0)
  const followCount = Number(raw.subscribers ?? raw.sub ?? 0)
  const followers = String(raw.followers ?? raw.subscribers_fmt ?? `${followCount}`)
  const engagement = Number(raw.engagement ?? raw.engagement_score ?? 0)
  const auth = Number(raw.auth ?? raw.authenticity_score ?? 0)
  const sentiment = Number(raw.sentiment ?? raw.sentiment_positive_pct ?? 0)
  const niche = String(raw.niche || 'General Fitness')
  const handle = String(raw.handle || raw.youtube_handle || '@creator')
  const name = String(raw.name || 'Creator')

  return {
    id: String(raw.id ?? raw.creator_id ?? handle),
    handle,
    name,
    sub: String(raw.sub ?? followCount),
    niche,
    tagline: String(raw.tagline ?? `${niche} creator`),
    gfs: String(raw.gfs ?? gfsValue.toFixed(1)),
    gfs_tier: gfsValue >= 7 ? 'GREEN' : 'AMBER',
    status: String(raw.status ?? (raw.outreach_recommended ? 'ready' : 'review')) as Creator['status'],
    img:
      raw.img ||
      `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(name)}`,
    followers,
    engagement: String(raw.engagement ?? `${engagement.toFixed(1)}%`),
    auth: String(raw.auth ?? auth.toFixed(1)),
    sentiment: String(raw.sentiment ?? `${sentiment.toFixed(0)}%`),
    breakdown: {
      authenticity: Number(raw.breakdown?.authenticity ?? raw.authenticity_score ?? auth ?? 0),
      niche: Number(raw.breakdown?.niche ?? raw.niche_score ?? 0),
      engagement: Number(raw.breakdown?.engagement ?? raw.engagement_score ?? engagement ?? 0),
      sentiment: Number(raw.breakdown?.sentiment ?? raw.sentiment_positive_pct ?? sentiment ?? 0),
      visual: Number(raw.breakdown?.visual ?? raw.authenticity_score ?? auth ?? 0),
      quality: Number(raw.breakdown?.quality ?? raw.niche_score ?? 0),
      cadence: Number(raw.breakdown?.cadence ?? raw.engagement_score ?? engagement ?? 0),
    },
    projections: {
      reach: String(raw.projections?.reach ?? `${followers}`),
      conv: String(raw.projections?.conv ?? '—'),
      roi: String(raw.projections?.roi ?? '—'),
    },
    socials: [
      {
        kind: 'youtube',
        label: handle,
        count: followers,
        er: raw.engagement_score ? `${Number(raw.engagement_score).toFixed(1)}%` : undefined,
      },
    ],
    responded: Boolean(raw.responded),
    response_date: raw.response_date,
    response_notes: raw.response_notes,
    outreach_sent_date: raw.outreach_sent_date,
    account_manager: raw.account_manager,
    outreach_channel: raw.outreach_channel,
    follow_up_date: raw.follow_up_date,
    proposed_next_step: raw.proposed_next_step,
    priority: raw.priority,
    signals: raw.signals || [`#${niche.toUpperCase().replace(/\s+/g, '_')}`, `GFS ${gfsValue.toFixed(1)}`],
  }
}

const SocialIcon = ({ kind }: { kind: 'youtube' | 'instagram' | 'tiktok' }) => {
  switch (kind) {
    case 'youtube':   return <YouTubeIcon className="w-3.5 h-3.5" />
    case 'instagram': return <InstagramIcon className="w-3.5 h-3.5" />
    case 'tiktok':    return <TikTokIcon className="w-3.5 h-3.5" />
  }
}

export default function OutreachPage() {
  const [creators, setCreators] = useState<Creator[]>([])
  const [loading, setLoading] = useState(true)
  const [activeCreator, setActiveCreator] = useState<Creator | null>(null)
  const [discoveryFilter, setDiscoveryFilter] = useState<Set<string>>(new Set())
  const [activeTier, setActiveTier] = useState('1')
  const [ladderOpen, setLadderOpen] = useState(false)
  const [emailDraft, setEmailDraft] = useState('')
  const [draftMeta, setDraftMeta] = useState<DraftResponse | null>(null)
  const [draftLoading, setDraftLoading] = useState(false)
  const [sendStatus, setSendStatus] = useState<'idle' | 'sending' | 'sent'>('idle')

  // Fetch draft from backend whenever creator or tier changes
  const fetchDraft = useCallback(async (creatorId: string, tier: string) => {
    setDraftLoading(true)
    try {
      const res = await fetch(`/api/creators/${creatorId}/draft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tier }),
      })
      const data: DraftResponse = await res.json()
      setEmailDraft(data.draft)
      setDraftMeta(data)
    } catch {
      setEmailDraft('Error loading draft — check that the backend is running.')
    } finally {
      setDraftLoading(false)
    }
  }, [])

  // Load creators on mount
  useEffect(() => {
    const stored = localStorage.getItem('gymshark-nexus-selected-creators')
    const filter = stored ? new Set<string>(JSON.parse(stored)) : new Set<string>()
    if (filter.size > 0) setDiscoveryFilter(filter)

    fetch('/api/creators')
      .then((r) => r.json())
      .then((data: any[]) => {
        const normalized = data.map(normalizeCreator)
        const visible = filter.size > 0 ? normalized.filter((c) => filter.has(c.id)) : normalized
        setCreators(visible)
        if (visible.length) {
          setActiveCreator(visible[0])
          fetchDraft(visible[0].id, '1')
        }
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [fetchDraft])

  const selectCreator = (creator: Creator) => {
    setActiveCreator(creator)
    setSendStatus('idle')
    fetchDraft(creator.id, activeTier)
  }

  const selectTier = (tier: string) => {
    setActiveTier(tier)
    setLadderOpen(false)
    setSendStatus('idle')
    if (activeCreator) fetchDraft(activeCreator.id, tier)
  }

  const handleSend = () => {
    setSendStatus('sending')
    // Simulate CRM sync (real integration would POST to a CRM endpoint)
    setTimeout(() => setSendStatus('sent'), 1200)
  }

  const wordCount = emailDraft.split(/\s+/).filter(Boolean).length
  const tierMeta = TIER_META[activeTier] ?? TIER_META['1']

  if (loading) {
    return (
      <AppShell currentPage="Outreach War Room">
        <div className="flex items-center justify-center h-[calc(100vh-52px)]">
          <div className="font-mono text-[15px] text-t3 tracking-[0.14em] uppercase flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-lime animate-pulse-dot" />
            Loading outreach pipeline…
          </div>
        </div>
      </AppShell>
    )
  }

  if (!activeCreator) {
    return (
      <AppShell currentPage="Outreach War Room">
        <div className="flex items-center justify-center h-[calc(100vh-52px)]">
          <div className="font-mono text-[15px] text-t3 tracking-[0.14em] uppercase">No creators in outreach pipeline.</div>
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell currentPage="Outreach War Room">
      <div className="grid grid-cols-[280px_1fr_380px] h-[calc(100vh-52px)]">

        {/* Column 1: Outreach Queue */}
        <section className="border-r border-border flex flex-col overflow-hidden">
          <div className="p-4 border-b border-border bg-panel-2">
            <div className="font-bold text-[15px] text-t1 tracking-[0.12em] uppercase mb-1">
              Outreach Queue
            </div>
            <div className="font-mono text-[14px] text-t3 tracking-[0.06em] uppercase">
              {creators.length} creators · in pipeline
            </div>
          </div>

          {/* Discovery filter banner */}
          {discoveryFilter.size > 0 && (
            <div className="px-3 py-2 bg-lime/8 border-b border-lime/20 flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5 font-mono text-[11px] text-lime tracking-[0.1em] uppercase">
                <span className="w-1.5 h-1.5 rounded-full bg-lime animate-pulse-dot" />
                {discoveryFilter.size} selected from Discovery
              </div>
              <button
                onClick={() => {
                  localStorage.removeItem('gymshark-nexus-selected-creators')
                  setDiscoveryFilter(new Set())
                  fetch('/api/creators').then(r => r.json()).then((data: any[]) => {
                    const normalized = data.map(normalizeCreator)
                    setCreators(normalized)
                    if (normalized.length) { setActiveCreator(normalized[0]); fetchDraft(normalized[0].id, activeTier) }
                  })
                }}
                className="font-mono text-[11px] text-t3 hover:text-t1 tracking-[0.1em] uppercase transition-colors"
              >
                show all
              </button>
            </div>
          )}

          <div className="flex-1 overflow-y-auto p-2 space-y-2">
            {creators.map((creator) => {
              const status = STATUS_LABELS[creator.status] ?? STATUS_LABELS.drafting
              return (
                <button
                  key={creator.id}
                  onClick={() => selectCreator(creator)}
                  className={`w-full text-left p-3 rounded-lg border transition-all duration-200 ${
                    activeCreator.id === creator.id
                      ? 'bg-lime/12 border-lime card-glow-active'
                      : 'bg-panel border-border hover:bg-panel-h hover:border-t3'
                  }`}
                >
                  <div className="flex items-start gap-3 mb-2">
                    <div
                      className="w-10 h-10 rounded-full bg-cover bg-center border border-border-2 flex-shrink-0"
                      style={{ backgroundImage: `url(${creator.img})` }}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2 mb-0.5">
                        <span className="font-bold text-[15px] text-t1 truncate">{creator.handle}</span>
                        <span className={`font-mono text-[14px] font-bold ${creator.gfs_tier === 'AMBER' ? 'text-amber' : 'text-lime'}`}>
                          {creator.gfs}
                        </span>
                      </div>
                      <div className="font-mono text-[15px] text-t3 tracking-[0.06em] uppercase truncate">
                        {creator.niche} · {creator.followers}
                      </div>
                    </div>
                  </div>
                  <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-[15px] font-bold tracking-[0.06em] uppercase border ${status.cls}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${
                      creator.status === 'ready'     ? 'bg-lime animate-pulse-dot' :
                      creator.status === 'responded' ? 'bg-lime' :
                      creator.status === 'review'    ? 'bg-amber' : 'bg-t3'
                    }`} />
                    {status.lbl}
                  </span>
                </button>
              )
            })}
          </div>
        </section>

        {/* Column 2: Email Studio */}
        <section className="border-r border-border flex flex-col overflow-hidden bg-bg">
          <div className="p-4 border-b border-border bg-panel-2 flex-shrink-0">
            <div className="font-bold text-[15px] text-t1 tracking-[0.12em] uppercase mb-1">
              Email Studio
            </div>
            <div className="font-mono text-[14px] text-t3 tracking-[0.06em] uppercase">
              Deep analytics · personalized outreach composer
            </div>
          </div>

          {/* Stats block — compact, fixed height */}
          <div className="flex-shrink-0 p-5 flex flex-col gap-4 border-b border-border">
            {/* Creator Header */}
            <div className="flex items-start gap-4">
              <div
                className="w-20 h-20 rounded-full bg-cover bg-center border-2 border-lime flex-shrink-0"
                style={{ backgroundImage: `url(${activeCreator.img})` }}
              />
              <div>
                <h2 className="font-black text-[34px] text-lime leading-tight tracking-[-0.01em]">
                  {activeCreator.handle}
                </h2>
                <div className="text-[15px] text-t2 mb-2">{activeCreator.tagline}</div>
                <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-[15px] font-bold tracking-[0.08em] uppercase ${
                  activeCreator.gfs_tier === 'AMBER' ? 'bg-amber/15 text-amber' : 'bg-lime/15 text-lime'
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${activeCreator.gfs_tier === 'AMBER' ? 'bg-amber' : 'bg-lime'} animate-pulse-dot`} />
                  GFS {activeCreator.gfs}
                </span>
              </div>
            </div>

            {/* Response Status Banner */}
            {(activeCreator.status === 'responded' || activeCreator.status === 'no_reply') && (
              <div className={`rounded-lg border p-3 ${
                activeCreator.status === 'responded' ? 'bg-lime/8 border-lime/25' : 'bg-t4/20 border-t4/25'
              }`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className={`w-2 h-2 rounded-full ${activeCreator.status === 'responded' ? 'bg-lime' : 'bg-t3'}`} />
                  <span className="font-mono text-[15px] tracking-[0.12em] uppercase font-bold text-t2">
                    {activeCreator.status === 'responded' ? 'Creator Responded' : 'No Reply Received'}
                  </span>
                  {activeCreator.response_date && (
                    <span className="font-mono text-[15px] text-t3 ml-auto">{activeCreator.response_date}</span>
                  )}
                </div>
                {activeCreator.response_notes && (
                  <p className="text-[15px] text-t2 leading-relaxed ml-4">{activeCreator.response_notes}</p>
                )}
                {activeCreator.outreach_sent_date && (
                  <div className="font-mono text-[15px] text-t3 ml-4 mt-1">
                    Outreach sent: {activeCreator.outreach_sent_date}
                  </div>
                )}
              </div>
            )}

            {/* KPI Grid */}
            <div className="grid grid-cols-4 gap-3">
              {[
                { label: 'Subscribers', value: activeCreator.followers },
                { label: 'Engagement',  value: activeCreator.engagement, highlight: true },
                { label: 'Auth Score',  value: activeCreator.auth },
                { label: 'Sentiment',   value: `${activeCreator.sentiment}%` },
              ].map((kpi) => (
                <div key={kpi.label} className="bg-panel border border-border rounded p-3 text-center">
                  <div className={`font-black text-[24px] leading-none mb-1 ${kpi.highlight ? 'text-lime' : 'text-t1'}`}>
                    {kpi.value}
                  </div>
                  <div className="font-mono text-[14px] text-t3 tracking-[0.1em] uppercase">{kpi.label}</div>
                </div>
              ))}
            </div>

            {/* Campaign Projections */}
            <div className="bg-panel border border-border rounded-lg p-4">
              <div className="font-mono text-[15px] text-t3 tracking-[0.14em] uppercase mb-3">
                Campaign Projections
              </div>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: 'Est. Reach',        value: activeCreator.projections.reach },
                  { label: 'Proj. Conversions', value: activeCreator.projections.conv },
                  { label: 'ROI Multiple',      value: activeCreator.projections.roi, highlight: true },
                ].map((item) => (
                  <div key={item.label} className="bg-panel-2 rounded p-3 text-center">
                    <div className={`font-black text-[20px] leading-none mb-1 ${item.highlight ? 'text-lime' : 'text-t1'}`}>
                      {item.value}
                    </div>
                    <div className="font-mono text-[14px] text-t3 tracking-[0.08em] uppercase">{item.label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Email Composer — fills remaining height */}
          <div className="flex-1 flex flex-col min-h-0 p-5 gap-2">
            <div className="font-mono text-[15px] text-t3 tracking-[0.14em] uppercase flex items-center justify-between flex-shrink-0">
              <span>Personalized Email Draft</span>
              {draftLoading && (
                <span className="flex items-center gap-1.5 text-lime">
                  <span className="w-1.5 h-1.5 rounded-full bg-lime animate-pulse-dot" />
                  Generating…
                </span>
              )}
            </div>
            <div className="flex-1 flex flex-col min-h-0 bg-[#0C0F0F] border border-[#1F2937] rounded-md overflow-hidden">
              <textarea
                value={emailDraft}
                onChange={(e) => setEmailDraft(e.target.value)}
                disabled={draftLoading}
                className="flex-1 min-h-0 w-full bg-transparent p-4 text-[15px] text-white leading-[1.8] resize-none focus:outline-none transition-all disabled:opacity-60"
                placeholder="Loading draft…"
              />
            </div>
            <div className="flex items-center justify-between flex-shrink-0 font-mono text-[11px] text-t4 tracking-[0.1em] uppercase">
              <span>TIER {activeTier} — {tierMeta.type.toUpperCase()} // {wordCount} WORDS</span>
              <span className={draftMeta?.llm_generated ? 'text-lime' : 'text-t3'}>
                {draftMeta?.llm_generated ? '// LLM GENERATED' : '// TEMPLATE DRAFT'}
              </span>
            </div>
          </div>
        </section>

        {/* Column 3: Action Execution */}
        <section className="flex flex-col overflow-hidden bg-panel">
          <div className="p-4 border-b border-border bg-panel-2 flex-shrink-0">
            <div className="font-bold text-[15px] text-t1 tracking-[0.12em] uppercase mb-1">
              Action Execution
            </div>
            <div className="font-mono text-[14px] text-t3 tracking-[0.06em] uppercase">
              CRM ladder · score signals
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
            {/* CRM Ladder */}
            <div>
              <div className="font-mono text-[15px] text-t3 tracking-[0.14em] uppercase mb-2">
                CRM Ladder Progression
              </div>
              <div className="rounded border border-border overflow-hidden">
                <button
                  onClick={() => setLadderOpen(!ladderOpen)}
                  className="w-full flex items-center justify-between p-3 bg-panel-3 hover:bg-panel-h transition-colors"
                >
                  <span className="font-bold text-[14px] text-t1">{tierMeta.label}</span>
                  <span className={`text-lime text-[15px] transition-transform duration-200 ${ladderOpen ? 'rotate-180' : ''}`}>▼</span>
                </button>
                {ladderOpen && (
                  <div className="border-t border-border bg-panel-2">
                    {Object.entries(TIER_META).map(([id, meta]) => (
                      <button
                        key={id}
                        onClick={() => selectTier(id)}
                        className={`w-full text-left p-3 border-b border-border last:border-b-0 font-bold text-[14px] tracking-[0.08em] uppercase transition-all duration-150 ${
                          activeTier === id
                            ? 'text-lime bg-lime-bg'
                            : 'text-t2 hover:bg-panel-h hover:text-t1'
                        }`}
                      >
                        {id}. {meta.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* CRM Context */}
            {(activeCreator.account_manager || activeCreator.outreach_channel || activeCreator.follow_up_date || activeCreator.proposed_next_step) && (
              <div>
                <div className="font-mono text-[15px] text-t3 tracking-[0.14em] uppercase mb-2">CRM Context</div>
                <div className="bg-panel-2 rounded border border-border divide-y divide-border">
                  {activeCreator.account_manager && (
                    <div className="flex items-center justify-between px-3 py-2">
                      <span className="font-mono text-[15px] text-t3 tracking-[0.08em] uppercase">Account Manager</span>
                      <span className="text-[15px] text-t1 font-medium">{activeCreator.account_manager}</span>
                    </div>
                  )}
                  {activeCreator.outreach_channel && (
                    <div className="flex items-center justify-between px-3 py-2">
                      <span className="font-mono text-[15px] text-t3 tracking-[0.08em] uppercase">Channel</span>
                      <span className="text-[15px] text-t1 font-medium capitalize">{activeCreator.outreach_channel}</span>
                    </div>
                  )}
                  {activeCreator.follow_up_date && (
                    <div className="flex items-center justify-between px-3 py-2">
                      <span className="font-mono text-[15px] text-t3 tracking-[0.08em] uppercase">Follow-Up Date</span>
                      <span className="text-[15px] text-t1 font-medium">{activeCreator.follow_up_date}</span>
                    </div>
                  )}
                  {activeCreator.proposed_next_step && (
                    <div className="px-3 py-2">
                      <div className="font-mono text-[15px] text-t3 tracking-[0.08em] uppercase mb-1">Next Step</div>
                      <div className="text-[15px] text-t2 leading-relaxed">{activeCreator.proposed_next_step}</div>
                    </div>
                  )}
                  {activeCreator.priority && (
                    <div className="flex items-center justify-between px-3 py-2">
                      <span className="font-mono text-[15px] text-t3 tracking-[0.08em] uppercase">Priority</span>
                      <span className={`text-[15px] font-bold tracking-[0.08em] uppercase px-2 py-0.5 rounded ${
                        activeCreator.priority === 'high' ? 'bg-lime/15 text-lime' :
                        activeCreator.priority === 'medium' ? 'bg-amber/15 text-amber' : 'bg-t3/15 text-t3'
                      }`}>{activeCreator.priority}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Score Breakdown */}
            <div>
              <div className="font-mono text-[11px] text-[#9CA0A6] tracking-[0.18em] uppercase mb-2">Score Breakdown</div>
              <div className="bg-panel-2 border border-border rounded-lg p-4 flex flex-col gap-3">
                {[
                  { label: 'Authenticity',      value: activeCreator.breakdown.authenticity ?? activeCreator.breakdown.visual },
                  { label: 'Comment Sentiment', value: activeCreator.breakdown.sentiment },
                  { label: 'Niche Alignment',   value: activeCreator.breakdown.niche ?? activeCreator.breakdown.quality },
                  { label: 'Engagement',        value: activeCreator.breakdown.engagement ?? activeCreator.breakdown.cadence },
                ].map((item) => (
                  <div key={item.label}>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-mono text-[10px] text-[#9CA0A6] tracking-[0.1em] uppercase">{item.label}</span>
                      <span className="font-mono text-[10px] text-[#95FF00] font-bold tabular-nums">{item.value}</span>
                    </div>
                    <div className="h-[3px] bg-panel-h rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[#95FF00] rounded-full transition-all duration-700"
                        style={{ width: `${item.value}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Send Button — sticky footer */}
          <div className="flex-shrink-0 p-4 border-t border-border bg-panel">
            {sendStatus === 'sent' ? (
              <div className="flex items-center justify-center gap-2 w-full px-4 py-4 rounded-full bg-lime/15 border border-lime/30 text-lime font-bold text-[15px] tracking-[0.14em] uppercase">
                ✓ Sent & CRM Synced
              </div>
            ) : (
              <button
                onClick={handleSend}
                disabled={sendStatus === 'sending' || draftLoading || !emailDraft}
                className="flex items-center justify-center gap-2.5 w-full px-4 py-4 rounded-full bg-lime text-[#0A0A0A] font-black text-[15px] tracking-[0.14em] uppercase cta-glow hover:bg-lime-2 hover:-translate-y-0.5 transition-all duration-200 disabled:opacity-60 disabled:translate-y-0"
              >
                <SendIcon className="w-4 h-4" />
                {sendStatus === 'sending' ? 'Sending…' : 'Send Outreach & Sync CRM'}
              </button>
            )}
          </div>
        </section>
      </div>
    </AppShell>
  )
}
