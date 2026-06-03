'use client'

import { useState } from 'react'
import { SearchIcon, ChevronDown, PackageIcon } from '@/components/icons'

interface Product {
  id: string
  sku: string
  name: string
  collection: string
  stock: number
  status: 'in-stock' | 'low-stock' | 'out-of-stock'
}

const products: Product[] = [
  { id: '1', sku: 'APEX-LS-001', name: 'Apex Seamless Long Sleeve', collection: 'Apex Drop 2026', stock: 1250, status: 'in-stock' },
  { id: '2', sku: 'APEX-SH-002', name: 'Apex Performance Shorts', collection: 'Apex Drop 2026', stock: 890, status: 'in-stock' },
  { id: '3', sku: 'APEX-JG-003', name: 'Apex Joggers', collection: 'Apex Drop 2026', stock: 45, status: 'low-stock' },
  { id: '4', sku: 'APEX-BRA-004', name: 'Apex Sports Bra', collection: 'Apex Drop 2026', stock: 2100, status: 'in-stock' },
  { id: '5', sku: 'VTL-TS-001', name: 'Vital Tee', collection: 'Vital Essentials', stock: 3400, status: 'in-stock' },
  { id: '6', sku: 'VTL-LG-002', name: 'Vital Leggings', collection: 'Vital Essentials', stock: 0, status: 'out-of-stock' },
  { id: '7', sku: 'PWR-HD-001', name: 'Power Hoodie', collection: 'Power Series', stock: 780, status: 'in-stock' },
  { id: '8', sku: 'PWR-TK-002', name: 'Power Tank', collection: 'Power Series', stock: 120, status: 'low-stock' },
]

const collections = ['All Collections', 'Apex Drop 2026', 'Vital Essentials', 'Power Series']

interface ProductInventoryProps {
  selectedProducts: string[]
  onSelectionChange: (products: string[]) => void
}

export function ProductInventory({ selectedProducts, onSelectionChange }: ProductInventoryProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCollection, setSelectedCollection] = useState('All Collections')
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)

  const filteredProducts = products.filter(product => {
    const matchesSearch = product.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         product.sku.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesCollection = selectedCollection === 'All Collections' || product.collection === selectedCollection
    return matchesSearch && matchesCollection
  })

  const toggleProduct = (sku: string) => {
    if (selectedProducts.includes(sku)) {
      onSelectionChange(selectedProducts.filter(p => p !== sku))
    } else {
      onSelectionChange([...selectedProducts, sku])
    }
  }

  const getStatusBadge = (status: Product['status']) => {
    switch (status) {
      case 'in-stock':
        return <span className="px-2 py-[2px] rounded-full bg-lime/14 text-lime font-mono text-[9px] tracking-[0.1em] uppercase font-bold">In Stock</span>
      case 'low-stock':
        return <span className="px-2 py-[2px] rounded-full bg-amber/14 text-amber font-mono text-[9px] tracking-[0.1em] uppercase font-bold">Low Stock</span>
      case 'out-of-stock':
        return <span className="px-2 py-[2px] rounded-full bg-orange/14 text-orange font-mono text-[9px] tracking-[0.1em] uppercase font-bold">Out of Stock</span>
    }
  }

  return (
    <div className="bg-panel border border-border rounded-lg overflow-hidden h-full flex flex-col">
      {/* Header */}
      <div className="p-3 border-b border-border flex-shrink-0">
        <div className="font-mono text-[9px] text-t3 tracking-[0.14em] uppercase mb-0.5">
          Section 01
        </div>
        <h2 className="font-extrabold text-[14px] text-t1 tracking-[-0.005em]">
          Product Inventory
        </h2>
      </div>

      {/* Search & Filter */}
      <div className="p-2 border-b border-border space-y-2 flex-shrink-0">
        {/* Search Bar */}
        <div className="relative">
          <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-t3" />
          <input
            type="text"
            placeholder="Search by name or SKU..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-panel-2 border border-border rounded-md pl-9 pr-3 py-2 text-[13px] text-t1 placeholder:text-t3 focus:outline-none focus:border-lime focus:ring-1 focus:ring-lime/30"
          />
        </div>

        {/* Collection Dropdown */}
        <div className="relative">
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="w-full bg-panel-2 border border-border rounded-md px-3 py-2 text-[13px] text-t1 flex items-center justify-between hover:border-lime/50 transition-colors"
          >
            <span>{selectedCollection}</span>
            <ChevronDown className={`w-4 h-4 text-t3 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} />
          </button>
          {isDropdownOpen && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-panel-2 border border-border rounded-md overflow-hidden z-10">
              {collections.map((collection) => (
                <button
                  key={collection}
                  onClick={() => {
                    setSelectedCollection(collection)
                    setIsDropdownOpen(false)
                  }}
                  className={`w-full px-3 py-2 text-[13px] text-left hover:bg-panel-h transition-colors ${
                    selectedCollection === collection ? 'text-lime bg-lime/10' : 'text-t1'
                  }`}
                >
                  {collection}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Product List */}
      <div className="overflow-y-auto flex-1 min-h-0">
        <div className="p-2 space-y-1.5">
          {filteredProducts.map((product) => {
            const isSelected = selectedProducts.includes(product.sku)
            return (
              <button
                key={product.id}
                onClick={() => toggleProduct(product.sku)}
                className={`w-full p-2 rounded-lg border transition-all duration-200 text-left ${
                  isSelected
                    ? 'bg-lime/12 border-lime card-glow-active'
                    : 'bg-panel-2 border-border hover:border-lime/50 hover:bg-panel-h'
                }`}
              >
                <div className="flex gap-2 items-center">
                  {/* Product Thumbnail */}
                  <div className="w-9 h-9 rounded-md bg-panel-3 border border-border flex items-center justify-center flex-shrink-0">
                    <PackageIcon className="w-4 h-4 text-t3" />
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-[12px] text-t1 truncate">
                      {product.name}
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="font-mono text-[9px] text-t3 tracking-wider">
                        {product.sku}
                      </span>
                      {getStatusBadge(product.status)}
                    </div>
                  </div>

                  {/* Selection Indicator */}
                  <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
                    isSelected ? 'border-lime bg-lime' : 'border-t3'
                  }`}>
                    {isSelected && (
                      <svg className="w-2.5 h-2.5 text-bg" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </div>
                </div>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
