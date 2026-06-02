import type { History } from "./database/types";
import type { Sheet } from "./sheet/Sheet";

const encoder = new TextEncoder();
const decoder = new TextDecoder();

const bookmarkVersion = "b2";
const bookmarkEncodingDeflate = "d";
const bookmarkEncodingRaw = "r";

export const bookmarkUrlSoftLimit = 350000;

export type BookmarkSharePayload = {
  version: number;
  title: string;
  history: History;
  sheet: Sheet;
  checksum: string;
};

type BookmarkShareBody = [
  title: string,
  history: History,
  sheet: Sheet
];

type BookmarkShareEncodedBody = [
  title: string,
  history: History,
  sheet: Sheet,
  checksum: string
];

async function digestBase64Url(input: string, bytes = 12): Promise<string> {
  const hash = await crypto.subtle.digest("SHA-256", encoder.encode(input));
  return base64UrlEncode(new Uint8Array(hash).subarray(0, bytes));
}

function supportsDeflateCompression(): boolean {
  return typeof CompressionStream !== "undefined" && typeof DecompressionStream !== "undefined";
}

async function deflateCompress(input: Uint8Array): Promise<Uint8Array> {
  const stream = new Blob([input]).stream().pipeThrough(new CompressionStream("deflate"));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

async function deflateDecompress(input: Uint8Array): Promise<Uint8Array> {
  const stream = new Blob([input]).stream().pipeThrough(new DecompressionStream("deflate"));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
  }

  if (typeof btoa === "function") {
    return btoa(binary);
  }

  // @ts-ignore
  return Buffer.from(binary, "binary").toString("base64");
}

function base64ToBytes(input: string): Uint8Array {
  let binary: string;
  if (typeof atob === "function") {
    binary = atob(input);
  } else {
    // @ts-ignore
    binary = Buffer.from(input, "base64").toString("binary");
  }

  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }

  return bytes;
}

function base64UrlEncode(input: Uint8Array): string {
  return bytesToBase64(input)
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

function base64UrlDecode(input: string): Uint8Array {
  let base64 = input.replace(/-/g, "+").replace(/_/g, "/");
  while (base64.length % 4 !== 0) {
    base64 += "=";
  }

  return base64ToBytes(base64);
}

async function encodeBody(body: BookmarkShareEncodedBody): Promise<{ encoding: string; payload: string; }> {
  const json = JSON.stringify(body);
  const bytes = encoder.encode(json);

  if (supportsDeflateCompression()) {
    const compressed = await deflateCompress(bytes);
    return {
      encoding: bookmarkEncodingDeflate,
      payload: base64UrlEncode(compressed)
    };
  }

  return {
    encoding: bookmarkEncodingRaw,
    payload: base64UrlEncode(bytes)
  };
}

async function decodeBody(encoding: string, payload: string): Promise<BookmarkShareEncodedBody> {
  const bytes = base64UrlDecode(payload);
  let rawBytes: Uint8Array;

  if (encoding === bookmarkEncodingDeflate) {
    if (!supportsDeflateCompression()) {
      throw new Error("This browser cannot decompress bookmark links.");
    }
    rawBytes = await deflateDecompress(bytes);
  } else if (encoding === bookmarkEncodingRaw) {
    rawBytes = bytes;
  } else {
    throw new Error(`Unsupported bookmark encoding: ${encoding}`);
  }

  return JSON.parse(decoder.decode(rawBytes)) as BookmarkShareEncodedBody;
}

export function formatBookmarkTitle(title: string): string {
  const trimmedTitle = title.trim() || "Untitled";
  const prefix = "MathPad · ";
  const maxTitleLength = 60;

  if (trimmedTitle.length <= maxTitleLength) {
    return `${prefix}${trimmedTitle}`;
  }

  const chars = Array.from(trimmedTitle);
  return `${prefix}${chars.slice(0, maxTitleLength - 1).join("")}…`;
}

export function isBookmarkShareFragment(hash: string): boolean {
  return hash.startsWith(`#${bookmarkVersion}.`);
}

export function getBookmarkShareFragment(hash: string): string | null {
  if (!isBookmarkShareFragment(hash)) {
    return null;
  }

  return hash.slice(1);
}

export async function createBookmarkShareFragment(sheet: Sheet, history: History, title: string): Promise<string> {
  const body: BookmarkShareBody = [title, history, sheet];
  const checksum = await digestBase64Url(JSON.stringify(body));
  const encoded = await encodeBody([title, history, sheet, checksum]);

  return `${bookmarkVersion}.${encoded.encoding}.${encoded.payload}`;
}

export async function createBookmarkShareUrl(origin: string, sheet: Sheet, history: History, title: string): Promise<{ url: string; bookmarkTitle: string; fragmentLength: number; }> {
  const bookmarkTitle = formatBookmarkTitle(title);
  const fragment = await createBookmarkShareFragment(sheet, history, title);
  const url = new URL(origin);
  url.pathname = "/";
  url.hash = fragment;

  return {
    url: url.toString(),
    bookmarkTitle,
    fragmentLength: fragment.length
  };
}

export async function decodeBookmarkShareFragment(fragment: string): Promise<BookmarkSharePayload> {
  const rawFragment = fragment.startsWith("#") ? fragment.slice(1) : fragment;
  const parts = rawFragment.split(".");

  if (parts.length < 3 || parts[0] !== bookmarkVersion) {
    throw new Error("Invalid bookmark share link.");
  }

  const encoding = parts[1];
  const payload = parts.slice(2).join(".");
  const body = await decodeBody(encoding, payload) as BookmarkShareEncodedBody;
  const [title, history, sheet, checksum] = body;
  const expectedChecksum = await digestBase64Url(JSON.stringify([title, history, sheet]));

  if (checksum !== expectedChecksum) {
    throw new Error("Bookmark share link checksum mismatch.");
  }

  return {
    version: 2,
    title,
    history,
    sheet,
    checksum
  };
}
