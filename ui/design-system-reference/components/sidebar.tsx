'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  DashboardIcon,
  DiscoveryIcon,
  OutreachIcon,
  ProductBriefIcon,
  TrendingUpIcon,
  ChevronLeft,
  ChevronRight,
  SettingsIcon
} from './icons'

const phases = [
  {
    id: 'dashboard',
    href: '/',
    num: 'Home',
    title: 'Master Console',
    desc: 'Global operations overview & cross-module activity',
    icon: DashboardIcon,
    live: false,
  },
  {
    id: 'discovery',
    href: '/discovery',
    num: 'Phase 01',
    title: 'Discovery',
    desc: 'AI-scored creator profiles across YouTube, Instagram, TikTok',
    icon: DiscoveryIcon,
    live: true,
  },
  {
    id: 'outreach',
    href: '/outreach',
    num: 'Phase 02',
    title: 'Outreach',
    desc: 'Deep analytics & contact war-room for shortlisted creators',
    icon: OutreachIcon,
    live: true,
  },
  {
    id: 'product-briefs',
    href: '/product-briefs',
    num: 'Phase 03',
    title: 'Product Briefs',
    desc: 'Creator product briefs, seeding inventory & campaign dispatch',
    icon: ProductBriefIcon,
    live: true,
  },
  {
    id: 'analytics',
    href: '/analytics',
    num: 'Skill 04',
    title: 'Analytics',
    desc: 'Campaign performance, ROI breakdowns & UTM-tracked revenue',
    icon: TrendingUpIcon,
    live: true,
  },
]

export function Sidebar() {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)
  
  // Load collapsed state from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem('gymshark-nexus-sidebar-collapsed')
    if (stored === '1') {
      setCollapsed(true)
    }
  }, [])

  const toggleCollapsed = () => {
    const newValue = !collapsed
    setCollapsed(newValue)
    localStorage.setItem('gymshark-nexus-sidebar-collapsed', newValue ? '1' : '0')
  }

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/'
    return pathname.startsWith(href)
  }

  return (
    <aside 
      className={`bg-panel border-r border-border flex flex-col py-[18px] px-3 gap-3 sticky top-[52px] h-[calc(100vh-52px)] overflow-hidden transition-all duration-300 ${
        collapsed ? 'w-[72px] px-[10px]' : 'w-[260px]'
      }`}
    >
      <div className={`flex items-center justify-between px-1 pb-[2px] gap-2 ${collapsed ? 'justify-center p-0' : ''}`}>
        {!collapsed && (
          <div className="font-mono text-[12px] text-t3 tracking-[0.22em] uppercase whitespace-nowrap">
            Platform Phases
          </div>
        )}
        <button
          onClick={toggleCollapsed}
          className={`w-[30px] h-[30px] rounded-md flex items-center justify-center transition-all duration-150 flex-shrink-0 bg-panel-h border border-border ${
            collapsed 
              ? 'text-lime border-lime/30' 
              : 'text-t2 hover:bg-lime-bg hover:text-lime hover:border-lime'
          }`}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <ChevronLeft className={`w-[14px] h-[14px] transition-transform duration-250 ${collapsed ? 'rotate-180' : ''}`} />
        </button>
      </div>

      <div className="flex flex-col gap-[6px] overflow-y-auto">
        {phases.map((phase) => {
          const Icon = phase.icon
          const active = isActive(phase.href)
          
          return (
            <Link
              key={phase.id}
              href={phase.href}
              className={`relative rounded-lg border transition-all duration-200 cursor-pointer overflow-hidden ${
                collapsed 
                  ? 'p-[6px] justify-items-center grid' 
                  : 'grid grid-cols-[36px_1fr_12px] gap-[10px] items-start p-[11px_12px]'
              } ${
                active
                  ? 'bg-lime/12 border-lime card-glow-active'
                  : 'bg-lime/5 border-lime/18 hover:bg-lime/10 hover:border-lime hover:translate-x-[2px]'
              }`}
            >
              <div 
                className={`w-9 h-9 rounded-[7px] flex items-center justify-center flex-shrink-0 border ${
                  active 
                    ? 'bg-lime/14 border-lime/25 text-lime' 
                    : 'bg-lime/14 border-lime/25 text-lime'
                }`}
              >
                <Icon className="w-4 h-4" />
              </div>
              
              {!collapsed && (
                <>
                  <div className="min-w-0">
                    <div className="font-mono text-[13px] text-t3 tracking-[0.14em] uppercase mb-[2px]">
                      {phase.num}
                    </div>
                    <div className="font-extrabold text-[15px] text-t1 tracking-[-0.005em] leading-[1.2] mb-1">
                      {phase.title}
                    </div>
                    <div className="text-[13px] text-t2 leading-[1.4]">
                      {phase.desc}
                    </div>
                    {phase.live && (
                      <span className="inline-flex items-center gap-[5px] mt-[6px] px-2 py-[2px] rounded-full bg-lime/14 text-lime font-mono text-[13px] tracking-[0.1em] uppercase font-bold">
                        <span className="w-[5px] h-[5px] rounded-full bg-current animate-pulse-dot"></span>
                        Live
                      </span>
                    )}
                  </div>
                  <span className={`self-center flex items-center justify-center text-t3 transition-all duration-150 ${active ? 'text-lime' : ''}`}>
                    <ChevronRight className="w-[14px] h-[14px]" />
                  </span>
                </>
              )}
            </Link>
          )
        })}
      </div>

      <div className="mt-auto pt-3 border-t border-border flex items-center gap-[10px]">
        {!collapsed && (
          <div className="flex-1 min-w-0 font-mono text-[13px] text-t3 tracking-[0.06em] uppercase leading-[1.5]">
            Operator<br/>
            <strong className="text-t1 font-semibold">D. Kapoor</strong>
          </div>
        )}
        <button className={`w-8 h-8 rounded-md flex items-center justify-center text-t3 transition-all duration-150 hover:bg-panel-h hover:text-t1 ${collapsed ? 'mx-auto' : ''}`} title="Settings">
          <SettingsIcon />
        </button>
      </div>
    </aside>
  )
}
