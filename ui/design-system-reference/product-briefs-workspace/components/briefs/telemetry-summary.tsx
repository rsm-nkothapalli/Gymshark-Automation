'use client'

import { useState } from 'react'
import { UsersIcon, TrendingUpIcon, PackageIcon, SendIcon } from '@/components/icons'

const cohortData: Record<string, { count: number; reach: number }> = {
  'Tier 1 Athletes': { count: 24, reach: 12500000 },
  'Fitness Influencers': { count: 156, reach: 45000000 },
  'Powerlifters': { count: 42, reach: 8200000 },
  'CrossFit Athletes': { count: 38, reach: 6800000 },
  'Yoga & Wellness': { count: 67, reach: 15400000 },
  'Running Community': { count: 89, reach: 18900000 },
  'Bodybuilders': { count: 31, reach: 9100000 },
  'Emerging Talent': { count: 203, reach: 4200000 },
}

interface TelemetrySummaryProps {
  selectedProducts: string[]
  selectedCohorts: string[]
}

export function TelemetrySummary({ selectedProducts, selectedCohorts }: TelemetrySummaryProps) {
  const [isDispatching, setIsDispatching] = useState(false)

  const totalRecipients = selectedCohorts.reduce((acc, cohort) => {
    return acc + (cohortData[cohort]?.count || 0)
  }, 0)

  const totalReach = selectedCohorts.reduce((acc, cohort) => {
    return acc + (cohortData[cohort]?.reach || 0)
  }, 0)

  const dispatchPacks = totalRecipients * selectedProducts.length

  const formatReach = (num: number) => {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M`
    }
    if (num >= 1000) {
      return `${(num / 1000).toFixed(0)}K`
    }
    return num.toString()
  }

  const handleDispatch = async () => {
    setIsDispatching(true)
    // Simulate dispatch
    await new Promise(resolve => setTimeout(resolve, 2000))
    setIsDispatching(false)
  }

  return (
    <div className="bg-panel border border-border rounded-lg overflow-hidden flex-1 flex flex-col">
      {/* Header */}
      <div className="p-3 border-b border-border flex-shrink-0">
        <div className="font-mono text-[9px] text-t3 tracking-[0.14em] uppercase mb-0.5">
          Section 04
        </div>
        <h2 className="font-extrabold text-[14px] text-t1 tracking-[-0.005em]">
          Telemetry & Execution
        </h2>
      </div>

      <div className="p-3 flex-1 flex flex-col">
        {/* Live Dispatch Summary */}
        <div className="mb-3">
          <div className="grid grid-cols-3 gap-2">
            {/* Recipients */}
            <div className="bg-panel-2 border border-border rounded-lg p-2">
              <div className="flex items-center gap-1.5 mb-1">
                <div className="w-5 h-5 rounded-md bg-lime/14 flex items-center justify-center">
                  <UsersIcon className="w-3 h-3 text-lime" />
                </div>
              </div>
              <div className="font-extrabold text-[18px] text-t1 tracking-tight leading-none">
                {totalRecipients}
              </div>
              <div className="font-mono text-[8px] text-t3 tracking-[0.1em] uppercase mt-0.5">
                Recipients
              </div>
            </div>

            {/* Est. Reach */}
            <div className="bg-panel-2 border border-border rounded-lg p-2">
              <div className="flex items-center gap-1.5 mb-1">
                <div className="w-5 h-5 rounded-md bg-lime/14 flex items-center justify-center">
                  <TrendingUpIcon className="w-3 h-3 text-lime" />
                </div>
              </div>
              <div className="font-extrabold text-[18px] text-t1 tracking-tight leading-none">
                {formatReach(totalReach)}
              </div>
              <div className="font-mono text-[8px] text-t3 tracking-[0.1em] uppercase mt-0.5">
                Est. Reach
              </div>
            </div>

            {/* Dispatch Packs */}
            <div className="bg-panel-2 border border-border rounded-lg p-2">
              <div className="flex items-center gap-1.5 mb-1">
                <div className="w-5 h-5 rounded-md bg-lime/14 flex items-center justify-center">
                  <PackageIcon className="w-3 h-3 text-lime" />
                </div>
              </div>
              <div className="font-extrabold text-[18px] text-t1 tracking-tight leading-none">
                {dispatchPacks}
              </div>
              <div className="font-mono text-[8px] text-t3 tracking-[0.1em] uppercase mt-0.5">
                Packs
              </div>
            </div>
          </div>
        </div>

        {/* Execution Details */}
        <div className="bg-panel-3 border border-border rounded-lg p-2 mb-3">
          <div className="grid grid-cols-2 gap-2 text-[10px]">
            <div>
              <span className="text-t3">Products:</span>
              <span className="text-t1 ml-1 font-medium">{selectedProducts.length}</span>
            </div>
            <div>
              <span className="text-t3">Cohorts:</span>
              <span className="text-t1 ml-1 font-medium">{selectedCohorts.length}</span>
            </div>
            <div>
              <span className="text-t3">Est. Cost:</span>
              <span className="text-lime ml-1 font-medium">${(dispatchPacks * 45).toLocaleString()}</span>
            </div>
            <div>
              <span className="text-t3">Ship:</span>
              <span className="text-t1 ml-1 font-medium">T+2 Days</span>
            </div>
          </div>
        </div>

        {/* Primary CTA */}
        <div className="mt-auto">
          <button
            onClick={handleDispatch}
            disabled={isDispatching || selectedProducts.length === 0 || selectedCohorts.length === 0}
            className={`w-full py-3 rounded-lg font-extrabold text-[12px] tracking-[0.08em] uppercase transition-all duration-200 flex items-center justify-center gap-2 ${
              isDispatching || selectedProducts.length === 0 || selectedCohorts.length === 0
                ? 'bg-panel-2 text-t3 border border-border cursor-not-allowed'
                : 'bg-lime text-bg hover:bg-lime-2 cta-glow'
            }`}
          >
            {isDispatching ? (
              <>
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Dispatching...
              </>
            ) : (
              <>
                <SendIcon className="w-4 h-4" />
                Send Brief & Dispatch
              </>
            )}
          </button>

          {(selectedProducts.length === 0 || selectedCohorts.length === 0) && (
            <p className="text-center text-[10px] text-t3 mt-1.5">
              Select products and cohorts to enable
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
