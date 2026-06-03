'use client'

import { Topbar } from './topbar'
import { Sidebar } from './sidebar'

interface AppShellProps {
  children: React.ReactNode
  currentPage: string
}

export function AppShell({ children, currentPage }: AppShellProps) {
  return (
    <div className="grid grid-rows-[52px_1fr] min-h-screen">
      <Topbar currentPage={currentPage} />
      <div className="grid grid-cols-[auto_1fr] min-h-0">
        <Sidebar />
        <main className="min-h-0 overflow-hidden">
          {children}
        </main>
      </div>
    </div>
  )
}
