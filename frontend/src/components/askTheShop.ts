// A tiny bridge from any page to the chat panel (Problem 10): "Ask the bulldog about this item"
// opens the counter with a question drafted, and the shopper decides whether to send it.
export const ASK_EVENT = 'cc:ask'

export interface AskDetail {
  question: string
}

export function askTheShop(question: string): void {
  window.dispatchEvent(new CustomEvent<AskDetail>(ASK_EVENT, { detail: { question } }))
}
