# Accessibility checklist (WCAG 2.1 AA)

Started 2026-10-18 before the first UI. Ticked as each item is built and verified; the verification section is filled before the build is called done.

## Design commitments (set before coding)
- Colours: background `#0a0f1c` (navy-black), text `#f3f5f9`, muted text `#b8c0d0`, Yale blue surface `#00356b`, Yale blue light `#5aa0ff` for links on dark, pink accent `#ff4fa3` for primary buttons and highlights. Pink on navy-black: 7.6:1 (text ok). Light blue on navy-black: 7.0:1. Muted text on navy-black: 10.5:1. White on Yale blue: 11.4:1.
- Focus ring: 3px pink outline with 2px offset on every focusable element.
- Motion: hover transitions only, all wrapped in `@media (prefers-reduced-motion: no-preference)`.
- Layout: single column under 720px, no fixed widths over 100%, nav collapses to a menu button with `aria-expanded`.

## Structure
- [x] Headings in order (one `h1` per page, no skipped levels); landmarks (`header`, `main`, `nav`, `footer`) (Problem 3)
- [x] Buttons are `<button>`, links are `<a>`; no click handlers on `div`s (Problem 3)
- [x] Page has a descriptive `<title>` per route and `lang="en"` (`usePageTitle`, Problem 3)
- [x] Skip link to main content as the first focusable element (Problem 3)

## Keyboard
- [x] Every control reachable and operable by keyboard (native links, buttons, inputs only)
- [x] Visible focus ring on all focusable elements (`:focus-visible` pink ring)
- [x] No keyboard traps; mobile menu closes with Escape

## Visual
- [x] Text contrast at least 4.5:1; large text and UI borders at least 3:1 (pairs above, computed)
- [x] Meaning never conveyed by colour alone: stock rows say "In stock", "Only a few left", "Sold out"; the Halloween switch shows on/off text (Problem 4)
- [~] Usable at 320px wide with no horizontal scroll; usable at 200% zoom. CSS has the 760px breakpoint and no fixed widths; not yet screenshot-verified because the automation window would not resize below 767px. Check in DevTools device mode before done.
- [x] `prefers-reduced-motion` respected; nothing flashes

## Labels and announcements
- [x] Every input has a visible label (Log in, Create Account)
- [x] Icon-only controls have `aria-label` (brand link); current nav link uses `aria-current="page"` (NavLink default)
- [x] Product images have alt text from the product name; all Halloween decoration is `aria-hidden` and `pointer-events: none` (Problem 4)

## Halloween mode (Problem 4)
- [x] Every animation is inside `@media (prefers-reduced-motion: no-preference)`; with reduced motion the webs are static and the pop-out fades instead of springing
- [x] No flashing content; the pop-out is a single soft scale-in, then a slow wiggle
- [x] No sound
- [x] Pop-out is `role="status"` (polite), auto-hides after 4 s, and has a Dismiss button; the photo is a labelled `<button>` only when Halloween is on, so keyboard users know a surprise follows
- [x] Toggle is `role="switch"` with `aria-checked` and a visible on/off label
- [x] Chat panel: non-modal dialog with a label, `role="log"` messages with `aria-live="polite"`, Escape closes and returns focus to the launcher

## Chat (Problem 5)
- [x] Reply log is `role="log"` with `aria-live="polite"`; a "Checking the shelves…" turn announces loading; the input and Send are disabled while a reply is pending
- [x] Product cards in the chat are links with the product name as text and decorative images (`alt=""`); "Show these on the Products page" is a plain link
- [x] The signed-in / guest note explains what is stored before the first message
- [x] Sold-out ghost on the item page is `aria-hidden`; the words "Sold out" carry the meaning (Problem 6)
- [x] Chat matches on the page: a labelled section with an `aria-live="polite"` status line, the same ProductCard links as the grid, a Clear button; the scroll-into-view is instant under reduced motion (Problem 7)

## Accounts (Problem 4)
- [x] Every sign-in and create-account input has a visible label and the right `autocomplete` token
- [x] Password rules shown as a live checklist next to the field (`aria-describedby`), each item with hidden "met / not met" text so the state is not colour-only
- [x] Show/hide password is a `<button>` with `aria-pressed`; confirm field sets `aria-invalid` while it mismatches
- [x] Errors and progress go through `role="status"` `aria-live="polite"`; the generated password is an `<output>` region
- [x] Delete account is a two-step confirm, both steps real buttons
- [x] Lightning: two brightenings in 1.8 s (about one per second, under the three-per-second limit), an SVG bolt inside the scene band plus a soft page-background glow that sits beneath the content; static under reduced motion; the scene is `aria-hidden`
- [x] Halloween effects never overlap text: the night scene is a block in the page flow between content and footer (or under the Account heading); fixed decorations appear only at 1460px and wider and stay in the empty side gutters; webs kept faint (0.32 in gutters, 0.55 in the scene)
- [x] Easter eggs: the hidden friend is a `<button>` with an accessible name, sits only in text-free spots (scene ground, footer end, product photo corner, wide-screen gutter), bobs only without reduced motion; the coupon dialog is `role="dialog"` with a label, takes focus, closes on Escape, and returns focus to the friend
- [x] Loading, error, and success states announced via `aria-live` (form status lines, Products placeholder)

## Usability improvements (Problem 9)
- [x] Size chips on product cards: a list with an `aria-label` naming the product, each chip carrying visually hidden "M in stock" / "M sold out" text; the strike-through and the Halloween 👻 are decorative (`aria-hidden`), never the only signal
- [x] Products filters: every control has a visible label (`Category`, `Sort by`, `Max price ($)`, `In stock only`, `Search`); changes are reflected in the URL and in a `role="status"` line that reads the applied filters in words; "Clear filters" is a real button
- [x] Nav badge "2/4" carries an `aria-label` ("2 of 4 hidden friends found this season"); the badge colour pair (pink on near-black text) passes 4.5:1
- [x] Hidden-friend dialog unchanged in behaviour (dialog role, focus, Escape); a found friend stays as a disabled button named "<friend>, found." so focus is not lost after the dialog closes
- [x] Account page collection: the tray is a labelled list, each slot has the friend's name or "Not found yet" as text; the progress bar is a `<progress>` element with an `aria-label`; the invite link button reports "Link copied" in its own text
- [x] Restock requests: "Request a restock" is a `<button>` per sold-out row; the result ("Requested. See your Account page.") replaces the button as text; guests get a plain "Sign in to request" link; the shopper's list uses text statuses (OPEN, ORDERED, CANCELLED) next to colour
- [x] Staff queue: a `<table>` with a caption, column headers with `scope`, and real buttons for "Mark ordered" and the CSV download
- [x] Chat page links: rendered as a link button in the message log so they are reachable by keyboard and announced with the reply; the page moves on its own only when the shopper asked to go there, and the link stays in the log afterwards ("Opened: …") so the change of page is explained

## Design polish (Problem 10)
- [x] Fonts: Fraunces (headings) and Alfa Slab One (wordmark, prices) are self-hosted and fall back to Georgia; body text stays the system sans at 16px; headings keep their semantic levels
- [x] Contrast: gold `#f2c230` on near-black 11.5:1 (motto, Y tag); pink `#ff4fa3` on `#0a0f1c` 7.4:1 (eyebrows, prices); the storefront strip is white on Yale Blue `#00356b` 9.9:1; the giant Y sits behind text at 55% of Yale Blue and never reduces the headline contrast below 4.5:1 (checked on the Home page)
- [x] Motion: page entrance, card stagger, hover lift and zoom, typing dots and the chat launcher all live inside `prefers-reduced-motion: no-preference`; with reduced motion the page renders complete and still
- [x] Swatches are decorative (`aria-hidden` on the item page; on cards the list carries `aria-label="Colours: …"` and each swatch a visually hidden name); the "Few left" and "Sold out" badges are text
- [x] "Ask the bulldog about this item" is a real button that opens the chat with the draft filled and focuses the input; the shopper still presses Send
- [x] Chat: typing dots are `aria-hidden` with hidden "Checking the shelves" text; suggested questions are buttons in a labelled list; the bulldog avatar is decorative; the launcher text still reads "Ask the bulldog" / "Hide the counter"
- [x] Home: the drop strip friend avatars are `aria-hidden` (the text carries the count); category cards are single links with the heading as the link text and a decorative photo (`alt=""`); college chips are plain links
- [x] Account tray: locked days show a padlock drawing plus the text "Not out yet, Arrives Oct N"; the progress bar is a labelled `<progress>`
- [x] Staff page: the reason the viewer can see it is stated in text; non-staff see a plain "Shop staff only" message, and the server refuses the data regardless

## Verification
- Keyboard-only pass done on (date):
- Screen reader pass (NVDA) done on (date):
- Contrast checks (tool + results): computed from the hex pairs above; re-check in browser dev tools before done.
