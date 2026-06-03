'use client'

import Link from 'next/link'
import { BrandLogo, SearchIcon, HelpIcon, NotificationIcon } from './icons'

interface TopbarProps {
  currentPage: string
}

export function Topbar({ currentPage }: TopbarProps) {
  const pageLabels: Record<string, string> = {
    dashboard: 'Master Console',
    discovery: 'Discovery Matrix',
    outreach: 'Outreach War Room',
    'product-briefs': 'Product Briefs',
    analytics: 'Campaign Analytics',
  }

  return (
    <header className="col-span-full bg-panel border-b border-border flex items-center px-[18px] pl-[14px] gap-[14px] h-[52px] z-10 sticky top-0">
      <div className="w-8 h-8 flex items-center justify-center text-t1">
        <BrandLogo className="w-5 h-5" />
      </div>
      <div className="font-extrabold text-[15px] tracking-[0.08em] text-t1 uppercase">
        GYMSHARK <span className="text-lime">NEXUS</span>
      </div>
      <span className="text-t4">/</span>
      <div className="font-mono text-[13px] text-t3 tracking-[0.06em] uppercase">
        <span className="text-lime mr-[6px] inline-flex items-center gap-[5px]">
          <span className="animate-pulse-dot">●</span>
          LIVE
        </span>
        {pageLabels[currentPage] || 'Console'}
      </div>

      <div className="ml-auto flex items-center gap-[6px]">
        <button className="w-8 h-8 rounded-md flex items-center justify-center text-t2 transition-all duration-150 hover:bg-panel-h hover:text-t1 relative" aria-label="Search">
          <SearchIcon />
        </button>
        <button className="w-8 h-8 rounded-md flex items-center justify-center text-t2 transition-all duration-150 hover:bg-panel-h hover:text-t1 relative" aria-label="Help">
          <HelpIcon />
        </button>
        <button className="w-8 h-8 rounded-md flex items-center justify-center text-t2 transition-all duration-150 hover:bg-panel-h hover:text-t1 relative" aria-label="Notifications">
          <NotificationIcon />
          <span className="absolute top-[6px] right-[7px] w-[7px] h-[7px] rounded-full bg-lime border-2 border-panel"></span>
        </button>
        <div className="w-[30px] h-[30px] rounded-full bg-panel-2 border border-border-2 ml-1 flex items-center justify-center">
          <div className="w-full h-full rounded-full bg-gradient-to-b from-panel-2 to-panel flex items-center justify-center">
            <span className="text-lime text-xs font-bold">DK</span>
          </div>
        </div>
      </div>
    </header>
  )
}
