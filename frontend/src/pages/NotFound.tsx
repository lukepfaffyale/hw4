import { Link } from 'react-router-dom'
import { usePageTitle } from '../usePageTitle'

export default function NotFound() {
  usePageTitle('Page not found')

  return (
    <>
      <h1>Page not found</h1>
      <p className="muted">That page is not in the shop.</p>
      <p>
        <Link className="btn btn-primary" to="/">
          Back to home
        </Link>
      </p>
    </>
  )
}
