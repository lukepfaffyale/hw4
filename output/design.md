# Design notes (Problem 10)

What changed to make the site feel like a real Campus Customs storefront, and why each change should help a shopper stick around and buy. The brief: Yale things, the Campus Customs shop, wrapped in a fun Halloween theme. We looked at the real Yale Bulldog Blue site for the feel (white, Open Sans, flat product rows, a help bubble) and then did our own flavour: a night-time storefront in Yale Blue with a bulldog at the counter.

Everything below is live at http://localhost:5173. Screenshots: `docs/screenshots/p10-*.jpg`.

## 1. Type: a Yale voice

- **Headings** are set in Fraunces, a Caslon-flavoured serif (Yale's own typeface is a Caslon cousin), with its soft and "wonky" axes turned on a little so the big headline has character. **Wordmark, prices and the giant Y** use Alfa Slab One, a varsity slab. Body text stays the system sans for reading comfort. Both fonts are self-hosted from `node_modules` (`@fontsource`), so no request leaves the site for typography.
- Small uppercase, letter-spaced **eyebrows** ("Licensed Yale gear, made for New Haven weather", "Shop staff") give every page the same rhythm: eyebrow, serif heading, muted lead.

Why: a serif headline over a slab price reads as a college shop, not a generic SaaS page. Shoppers trust a store that looks like it knows what it sells.

## 2. Brand and hierarchy

- A **storefront strip** above the nav: where we are ("Licensed Yale gear. 57 Broadway, New Haven.") and what is on ("The Halloween drop is on: 31 friends are hiding. Find three for a coupon.").
- A **wordmark** with an original bulldog mark (Yale-blue collar, gold Y tag) and the stacked name "CAMPUS CUSTOMS / Yale gear, New Haven".
- The **hero** carries a huge Yale-blue "Y" behind the headline (decorative, behind the text, never over it) and two clear actions: shop the catalogue, or jump straight to "in stock, cheapest first".
- A **seasonal drop strip** under the hero with the latest friends and the day counter, then **category cards that show a real product photo** and a style count, then **residential college chips** (only the colleges that exist in the catalogue) and the family section.
- The footer carries "Lux et Veritas, Boola Boola" in the serif italic, in gold.

Why: the page now answers the three questions a shopper has in the first five seconds (what is this, what do you sell, what is going on today), in that order, with real photos instead of placeholder text.

## 3. Colour

Yale Blue (`#00356B`) stays the surface colour and the class pink (`#ff4fa3`) the call to action; Halloween mode swaps the pink for pumpkin orange and the blue surfaces for witch purple, as before. New: a gold accent (`#f2c230`) for the Y tag, the motto and small marks, the colour of the Yale shield. Contrast pairs are listed in `docs/accessibility.md` and all pass 4.5:1.

## 4. Product presentation

- Cards **lift and zoom** on hover, show **colour swatches** from the item's colour list (the names stay for screen readers and tooltips), a **"Few left" badge** when total stock is twelve or under, the **size chips** from Problem 9, a serif name and a slab price. Cards **stagger in** as the grid loads.
- The item page keeps its details **sticky** beside the photo on wide screens, shows large swatches next to the colour names, and adds **"Ask the bulldog about this item"**, which opens the chat with the question already drafted (the shopper still presses Send).

Why: scanning a grid of 102 items is faster when colour, scarcity and sizes are visible at a glance, and a stuck-on question is one click from an answer.

## 5. The shop counter (chat feel)

- The launcher is now **"Ask the bulldog"** with the bulldog's face. The panel is **"The shop counter"** with the bulldog as avatar, speech bubbles with tails, and animated **typing dots** while the shelves are checked (with hidden text for screen readers).
- **Suggested questions** ("Hoodies under $50", "What crewnecks are in stock in M?", "Cheapest Yale tee?", "Give me a clue for the hidden friends") appear on a fresh conversation; one tap sends them.
- Welcome line in the bulldog's voice: "Woof. I am the shop bulldog."

Why: a counter with a face gets more first questions than a form, and suggested questions show new shoppers what the assistant is good for.

## 6. Halloween, but Yale

- The night scene's haunted house is now **Evans Hall**, the SOM building: the long glass front with its colonnade of fins, windows glowing orange, the plaza lit beneath. **Harkness Tower** stands behind it with a lit clock face and glowing lancet windows, under the same moon, crows and storm. The dead tree moved to the edge; graveyard, fence, pumpkins, fog and the bats stay.
- The hidden friends are a **31-day Halloween set**: Totoro, Chu Totoro, Chibi Totoro, Catbus, Labubu, a Soot Sprite and No-Face in eight trick-or-treat costumes (witch, ghost, zombie, skeleton, vampire, mummy, pumpkin, devil), one new friend each day of October. Costumes are drawn as overlays on each character, so every pairing is a real drawing.

Why: the mood is still Halloween, but the landmarks say Yale and SOM, which is the whole point of the shop.

## 7. Motion, with limits

Page entrance (320 ms fade-up), card stagger (45 ms steps, capped), hover lifts and photo zoom, typing dots, the existing lightning and scene drift. Every one of them sits inside `prefers-reduced-motion: no-preference`; with reduced motion on, the site is still and complete. Nothing flashes faster than the lightning's two pulses in 1.8 s.

## What to look at

| Page | What changed |
|---|---|
| Home | strip, wordmark, Y hero, drop strip with the day counter, photo category cards, college chips, motto |
| Products | staggered cards with swatches, badges and size chips; serif names, slab prices |
| Item page | sticky details, large swatches, "Ask the bulldog about this item" |
| Chat | bulldog launcher and avatar, bubbles, typing dots, suggested questions |
| Scene (any page, Halloween on) | Evans Hall and Harkness Tower |
| Account | the 31-day tray with locked days and arrival dates; role line (shopper or staff) |
| Staff (staff accounts only) | the restock queue moved to its own page with a plain note on why you can see it |

Screenshots: `p10-home.jpg`, `p10-products.jpg`, `p10-item.jpg`, `p10-chat.jpg`, `p10-scene.jpg`, `p10-account-tray.jpg`, `p10-staff.jpg`.
