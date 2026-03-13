/**
 * Shared utterance corpus for k6 load tests.
 *
 * Provides Hausa, English, and code-switched utterances grouped by intent.
 * Each intent maps to the agent that handles it (see src/agents/supervisor.py).
 */

export const INTENTS = {
  balance: [
    // Hausa
    "Ina son sanin kuɗin da ke cikin asusuna",
    "Nawa ne balance na?",
    "Ka nuna min yawan kuɗi na",
    // English
    "What is my account balance?",
    "How much money do I have?",
    // Code-switch
    "Ina son check balance na",
    "Please ka nuna min account balance",
  ],
  transfer: [
    // Hausa
    "Ina son tura kuɗi zuwa 08012345678",
    "Ka tura naira dubu biyar zuwa wannan lambar",
    "Aika kuɗi zuwa abokin na",
    // English
    "I want to send money to 08012345678",
    "Transfer five thousand naira",
    // Code-switch
    "Ina son transfer kuɗi zuwa account din friend na",
    "Please ka help ni send money",
  ],
  bills: [
    // Hausa
    "Ina son biyan kuɗin wutar lantarki",
    "Ka biya bill na na DSTV",
    "Ina son biyan kuɗin wayar hannu",
    // English
    "I want to pay my electricity bill",
    "Pay my DSTV subscription",
    // Code-switch
    "Ina son pay electricity bill na",
    "Help me biya DSTV subscription",
  ],
  general: [
    // Hausa
    "Yaya zan canza lambar sirri na?",
    "Ina samun matsala da app din",
    "Me zan iya yi da wannan sabis?",
    // English
    "How do I change my PIN?",
    "I am having trouble with the app",
    // Code-switch
    "Ina son change PIN na",
    "Ina having problem da account na",
  ],
};

/** Pick a random utterance from any intent. */
export function randomUtterance() {
  const intents = Object.keys(INTENTS);
  const intent = intents[Math.floor(Math.random() * intents.length)];
  const pool = INTENTS[intent];
  return {
    intent,
    text: pool[Math.floor(Math.random() * pool.length)],
  };
}

/** Pick a random utterance for a specific intent. */
export function utteranceForIntent(intent) {
  const pool = INTENTS[intent];
  if (!pool) {
    throw new Error(`Unknown intent: ${intent}`);
  }
  return pool[Math.floor(Math.random() * pool.length)];
}

/**
 * Generate a weighted intent mix reflecting realistic traffic.
 * Balance checks are most common, then transfers, then bills, then general.
 */
export function weightedIntent() {
  const r = Math.random();
  if (r < 0.35) return "balance";
  if (r < 0.60) return "transfer";
  if (r < 0.80) return "bills";
  return "general";
}
