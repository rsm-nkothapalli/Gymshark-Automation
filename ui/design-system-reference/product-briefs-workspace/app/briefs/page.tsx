'use client'

import { useState } from 'react'
import { AppShell } from '@/components/app-shell'
import { ProductInventory } from '@/components/briefs/product-inventory'
import { VisualBriefing } from '@/components/briefs/visual-briefing'
import { FulfillmentConfig } from '@/components/briefs/fulfillment-config'
import { TelemetrySummary } from '@/components/briefs/telemetry-summary'

export default function BriefsPage() {
  const [selectedProducts, setSelectedProducts] = useState<string[]>(['APEX-LS-001', 'APEX-JG-003'])
  const [selectedCohorts, setSelectedCohorts] = useState<string[]>(['Tier 1 Athletes', 'Fitness Influencers'])
  const [distributionMode, setDistributionMode] = useState<'push' | 'selection'>('push')

  return (
    <AppShell currentPage="briefs">
      <div className="h-full overflow-hidden p-4 bg-bg">
        <div className="max-w-[1800px] mx-auto h-full flex flex-col">
          {/* Page Header */}
          <div className="mb-4 flex-shrink-0">
            <div className="font-mono text-[10px] text-t3 tracking-[0.22em] uppercase mb-1">
              Campaign Workspace
            </div>
            <h1 className="font-extrabold text-[22px] text-t1 tracking-[-0.02em]">
              Product Briefs Workspace
            </h1>
          </div>

          {/* Main Grid Layout */}
          <div className="grid grid-cols-12 gap-3 flex-1 min-h-0">
            {/* Left Column - Product Inventory */}
            <div className="col-span-3 h-full">
              <ProductInventory 
                selectedProducts={selectedProducts}
                onSelectionChange={setSelectedProducts}
              />
            </div>

            {/* Center Column - Visual Briefing */}
            <div className="col-span-5 h-full">
              <VisualBriefing />
            </div>

            {/* Right Column - Configuration & Telemetry */}
            <div className="col-span-4 flex flex-col gap-3 h-full">
              <FulfillmentConfig 
                selectedCohorts={selectedCohorts}
                onCohortsChange={setSelectedCohorts}
                distributionMode={distributionMode}
                onDistributionModeChange={setDistributionMode}
              />
              <TelemetrySummary 
                selectedProducts={selectedProducts}
                selectedCohorts={selectedCohorts}
              />
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  )
}
