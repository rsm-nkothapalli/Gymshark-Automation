'use client'

import { useState } from 'react'
import { TagIcon, XIcon, ZapIcon } from '@/components/icons'

const availableCohorts = [
  { id: '1', name: 'Tier 1 Athletes', count: 24, tag: 'elite' },
  { id: '2', name: 'Fitness Influencers', count: 156, tag: 'influencer' },
  { id: '3', name: 'Powerlifters', count: 42, tag: 'strength' },
  { id: '4', name: 'CrossFit Athletes', count: 38, tag: 'crossfit' },
  { id: '5', name: 'Yoga & Wellness', count: 67, tag: 'wellness' },
  { id: '6', name: 'Running Community', count: 89, tag: 'running' },
  { id: '7', name: 'Bodybuilders', count: 31, tag: 'physique' },
  { id: '8', name: 'Emerging Talent', count: 203, tag: 'emerging' },
]

interface FulfillmentConfigProps {
  selectedCohorts: string[]
  onCohortsChange: (cohorts: string[]) => void
  distributionMode: 'push' | 'selection'
  onDistributionModeChange: (mode: 'push' | 'selection') => void
}

export function FulfillmentConfig({ 
  selectedCohorts, 
  onCohortsChange, 
  distributionMode, 
  onDistributionModeChange 
}: FulfillmentConfigProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)

  const filteredCohorts = availableCohorts.filter(c => 
    c.name.toLowerCase().includes(searchQuery.toLowerCase()) &&
    !selectedCohorts.includes(c.name)
  )

  const addCohort = (name: string) => {
    onCohortsChange([...selectedCohorts, name])
    setSearchQuery('')
    setIsDropdownOpen(false)
  }

  const removeCohort = (name: string) => {
    onCohortsChange(selectedCohorts.filter(c => c !== name))
  }

  const getRecipeReadout = () => {
    const totalCreators = selectedCohorts.reduce((acc, cohortName) => {
      const cohort = availableCohorts.find(c => c.name === cohortName)
      return acc + (cohort?.count || 0)
    }, 0)

    if (distributionMode === 'push') {
      return `FORCED PUSH mode active. All ${totalCreators} recipients in selected cohorts will automatically receive product dispatch. No opt-out available. Shipping labels will be generated immediately upon execution.`
    } else {
      return `ALLOW SELECTION mode active. ${totalCreators} eligible creators will receive brief notification. Recipients can select preferred sizes/colorways within 72hr window. Dispatch occurs after selection deadline.`
    }
  }

  return (
    <div className="bg-panel border border-border rounded-lg overflow-hidden">
      {/* Header */}
      <div className="p-3 border-b border-border">
        <div className="font-mono text-[9px] text-t3 tracking-[0.14em] uppercase mb-0.5">
          Section 03
        </div>
        <h2 className="font-extrabold text-[14px] text-t1 tracking-[-0.005em]">
          Fulfillment Config
        </h2>
      </div>

      <div className="p-3 space-y-3">
        {/* Cohort Multi-Select */}
        <div>
          <label className="block font-mono text-[9px] text-t3 tracking-[0.14em] uppercase mb-1.5">
            Target Cohorts
          </label>
          
          {/* Selected Tags */}
          <div className="flex flex-wrap gap-1.5 mb-1.5">
            {selectedCohorts.map((cohortName) => {
              const cohort = availableCohorts.find(c => c.name === cohortName)
              return (
                <span
                  key={cohortName}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-lime/14 text-lime text-[10px] font-medium border border-lime/30"
                >
                  <TagIcon className="w-2.5 h-2.5" />
                  {cohortName}
                  <button
                    onClick={() => removeCohort(cohortName)}
                    className="ml-0.5 hover:bg-lime/20 rounded-full p-0.5 transition-colors"
                  >
                    <XIcon className="w-2.5 h-2.5" />
                  </button>
                </span>
              )
            })}
          </div>

          {/* Search Input */}
          <div className="relative">
            <input
              type="text"
              placeholder="Add cohorts..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value)
                setIsDropdownOpen(true)
              }}
              onFocus={() => setIsDropdownOpen(true)}
              className="w-full bg-panel-2 border border-border rounded-md px-3 py-2 text-[13px] text-t1 placeholder:text-t3 focus:outline-none focus:border-lime focus:ring-1 focus:ring-lime/30"
            />
            {isDropdownOpen && filteredCohorts.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-panel-2 border border-border rounded-md overflow-hidden z-10 max-h-[140px] overflow-y-auto">
                {filteredCohorts.map((cohort) => (
                  <button
                    key={cohort.id}
                    onClick={() => addCohort(cohort.name)}
                    className="w-full px-3 py-1.5 text-[12px] text-left hover:bg-panel-h transition-colors flex items-center justify-between"
                  >
                    <span className="text-t1">{cohort.name}</span>
                    <span className="text-t3 font-mono text-[9px]">{cohort.count}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Distribution Strategy Toggle */}
        <div>
          <label className="block font-mono text-[9px] text-t3 tracking-[0.14em] uppercase mb-1.5">
            Distribution Strategy
          </label>
          <div className="flex gap-2">
            <button
              onClick={() => onDistributionModeChange('push')}
              className={`flex-1 px-3 py-2 rounded-lg border transition-all duration-200 ${
                distributionMode === 'push'
                  ? 'bg-lime/12 border-lime text-lime card-glow-active'
                  : 'bg-panel-2 border-border text-t2 hover:border-lime/50'
              }`}
            >
              <div className="flex items-center justify-center gap-1.5">
                <ZapIcon className="w-3.5 h-3.5" />
                <span className="font-mono text-[10px] tracking-wider uppercase font-bold">Forced Push</span>
              </div>
            </button>
            <button
              onClick={() => onDistributionModeChange('selection')}
              className={`flex-1 px-3 py-2 rounded-lg border transition-all duration-200 ${
                distributionMode === 'selection'
                  ? 'bg-lime/12 border-lime text-lime card-glow-active'
                  : 'bg-panel-2 border-border text-t2 hover:border-lime/50'
              }`}
            >
              <div className="flex items-center justify-center gap-1.5">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8 9l4-4 4 4m0 6l-4 4-4-4" />
                </svg>
                <span className="font-mono text-[10px] tracking-wider uppercase font-bold">Selection</span>
              </div>
            </button>
          </div>
        </div>

        {/* Live Recipe Readout */}
        <div>
          <label className="block font-mono text-[9px] text-t3 tracking-[0.14em] uppercase mb-1.5">
            Live Recipe
          </label>
          <div className="bg-panel-3 border border-border rounded-lg p-2">
            <div className="flex items-start gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-lime animate-pulse-dot mt-1 flex-shrink-0"></div>
              <p className="text-[10px] text-t2 leading-relaxed font-mono">
                {getRecipeReadout()}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
