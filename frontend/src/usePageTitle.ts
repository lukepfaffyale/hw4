import { useEffect } from 'react'

/** Sets the document title per route so screen readers announce the page. */
export function usePageTitle(title: string) {
  useEffect(() => {
    document.title = title ? `${title} | Campus Customs` : 'Campus Customs'
  }, [title])
}
