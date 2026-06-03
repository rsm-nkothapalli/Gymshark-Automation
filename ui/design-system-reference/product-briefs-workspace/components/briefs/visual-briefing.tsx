'use client'

import { useState } from 'react'
import { ImageIcon } from '@/components/icons'

const thumbnailImages = [
  { id: '1', label: 'Black Colorway', active: true },
  { id: '2', label: 'Navy Colorway', active: false },
  { id: '3', label: 'Grey Colorway', active: false },
  { id: '4', label: 'Detail Shot 1', active: false },
  { id: '5', label: 'Detail Shot 2', active: false },
  { id: '6', label: 'Lifestyle', active: false },
]

export function VisualBriefing() {
  const [activeImage, setActiveImage] = useState('1')

  return (
    <div className="bg-panel border border-border rounded-lg overflow-hidden h-full flex flex-col">
      {/* Header */}
      <div className="p-3 border-b border-border flex-shrink-0">
        <div className="font-mono text-[9px] text-t3 tracking-[0.14em] uppercase mb-0.5">
          Section 02
        </div>
        <h2 className="font-extrabold text-[14px] text-t1 tracking-[-0.005em]">
          Visual Briefing Assets
        </h2>
      </div>

      {/* Main Media Canvas */}
      <div className="p-2 flex-1 flex flex-col min-h-0">
        <div className="relative flex-1 min-h-0 bg-panel-3 border border-border rounded-lg overflow-hidden">
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <ImageIcon className="w-12 h-12 text-t4 mx-auto mb-3" />
              <div className="font-mono text-[11px] text-t3 tracking-wider uppercase">
                Lookbook Image Canvas
              </div>
              <div className="text-[12px] text-t4 mt-1">
                Apex Drop 2026 — Collection Imagery
              </div>
            </div>
          </div>
          {/* Overlay Badge */}
          <div className="absolute top-3 left-3">
            <span className="inline-flex items-center gap-[5px] px-2 py-[3px] rounded-full bg-bg/80 backdrop-blur-sm text-lime font-mono text-[9px] tracking-[0.1em] uppercase font-bold border border-lime/30">
              <span className="w-[5px] h-[5px] rounded-full bg-current animate-pulse-dot"></span>
              Primary Asset
            </span>
          </div>
        </div>

        {/* Thumbnail Strip */}
        <div className="mt-2 flex gap-1.5 overflow-x-auto pb-1 flex-shrink-0">
          {thumbnailImages.map((img) => (
            <button
              key={img.id}
              onClick={() => setActiveImage(img.id)}
              className={`flex-shrink-0 w-[56px] h-[56px] rounded-md border transition-all duration-200 ${
                activeImage === img.id
                  ? 'border-lime bg-lime/10 ring-1 ring-lime/30'
                  : 'border-border bg-panel-3 hover:border-lime/50'
              }`}
            >
              <div className="w-full h-full flex items-center justify-center">
                <ImageIcon className={`w-4 h-4 ${activeImage === img.id ? 'text-lime' : 'text-t4'}`} />
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Campaign Objective Panel */}
      <div className="p-2 border-t border-border flex-shrink-0">
        <div className="bg-panel-2 border border-border rounded-lg p-3">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-5 h-5 rounded-md bg-lime/14 flex items-center justify-center">
              <svg className="w-3 h-3 text-lime" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <span className="font-mono text-[9px] text-t3 tracking-[0.14em] uppercase">Campaign Objective</span>
          </div>

          <div className="space-y-2 text-[11px] leading-relaxed">
            <div>
              <div className="font-semibold text-t1 mb-0.5">Strategy</div>
              <p className="text-t2">
                Drive Apex Drop 2026 awareness through strategic creator partnerships focusing on authentic fitness content.
              </p>
            </div>

            <div>
              <div className="font-semibold text-t1 mb-0.5">Deliverables</div>
              <p className="text-t2">
                1x Instagram Reel, 3x Stories with tags, 1x YouTube Short/TikTok
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
