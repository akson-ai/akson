import { customAlphabet } from "nanoid";
import { alphanumeric } from "nanoid-dictionary";

const nanoid = customAlphabet(alphanumeric, 8);

export function generateChatId() {
  return nanoid();
}

export function generateMessageId() {
  return nanoid();
}
