import { Link } from 'react-router-dom'
import { usePageTitle } from '../usePageTitle'

export default function About() {
  usePageTitle('About Us')

  return (
    <>
      <h1>About Campus Customs</h1>
      <p className="lead muted">
        We are the Yale merch shop on Broadway in New Haven, and this is our online storefront.
      </p>

      <section className="section" aria-labelledby="what-we-sell">
        <h2 id="what-we-sell">What we sell</h2>
        <p>
          Officially licensed Yale apparel. The online catalogue focuses on the pieces people
          actually live in: pullover hoodies, crewneck sweatshirts, short-sleeve tees, quarter-zip
          pullovers, fleece and bomber jackets, and a few performance shirts. Designs range from the
          big arched YALE wordmark to small left-chest marks for the crew, hockey, sailing, fencing
          and baseball teams, to crests for every residential college.
        </p>
      </section>

      <section className="section" aria-labelledby="how-we-work">
        <h2 id="how-we-work">How this shop works</h2>
        <div className="grid">
          <article className="card">
            <h3>Honest stock</h3>
            <p className="muted">
              Every size shows its real availability. If a medium is sold out, the page and the
              chat assistant both say so.
            </p>
          </article>
          <article className="card">
            <h3>One price, no games</h3>
            <p className="muted">
              Tees from $32, crews from $58, hoodies at $68, jackets up to $98. The price on the
              card is the price you pay.
            </p>
          </article>
          <article className="card">
            <h3>Ask, don't scroll</h3>
            <p className="muted">
              Tell the chat assistant what you are after, "a gray crewneck under $60" or "anything
              with the bulldog", and matching items show up next to the conversation.
            </p>
          </article>
          <article className="card">
            <h3>Your data, your call</h3>
            <p className="muted">
              With an account the assistant remembers your chats. You can see and delete that
              history whenever you like.
            </p>
          </article>
        </div>
      </section>

      <section className="section" aria-labelledby="visit">
        <h2 id="visit">Visit the store</h2>
        <p>
          Campus Customs, 57 Broadway, New Haven, CT 06511. A short walk from Old Campus and the
          residential colleges.
        </p>
        <p>
          <Link className="btn btn-primary" to="/products">
            Browse the catalogue
          </Link>
        </p>
      </section>

      <p className="muted">
        This site is a class project built for MGT 409 at Yale SOM. It uses the Campus Customs
        name and catalogue as a teaching example and is not the store's official website.
      </p>
    </>
  )
}
