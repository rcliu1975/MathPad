import type { History } from "./database/types";
import type { Sheet } from "./sheet/Sheet";

const encoder = new TextEncoder();
const decoder = new TextDecoder();

const bookmarkVersion = "bm1";
const bookmarkEncodingGzip = "gz";
const bookmarkEncodingRaw = "raw";

export const bookmarkUrlSoftLimit = 350000;

export type BookmarkSharePayload = {
  version: number;
  title: string;
  history: History;
  sheet: Sheet;
  checksum: string;
};

type BookmarkShareBody = Omit<BookmarkSharePayload, "checksum">;

function toHex(bytes: Uint8Array): string {
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

async function digestHex(input: string): Promise<string> {
  const hash = await crypto.subtle.digest("SHA-256", encoder.encode(input));
  return toHex(new Uint8Array(hash));
}

function supportsGzipCompression(): boolean {
  return typeof CompressionStream !== "undefined" && typeof DecompressionStream !== "undefined";
}

async function gzipCompress(input: Uint8Array): Promise<Uint8Array> {
  const stream = new Blob([input]).stream().pipeThrough(new CompressionStream("gzip"));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

async function gzipDecompress(input: Uint8Array): Promise<Uint8Array> {
  const stream = new Blob([input]).stream().pipeThrough(new DecompressionStream("gzip"));
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

async function encodeBody(body: BookmarkShareBody): Promise<{ encoding: string; payload: string; }> {
  const json = JSON.stringify(body);
  const bytes = encoder.encode(json);

  if (supportsGzipCompression()) {
    const compressed = await gzipCompress(bytes);
    return {
      encoding: bookmarkEncodingGzip,
      payload: base64UrlEncode(compressed)
    };
  }

  return {
    encoding: bookmarkEncodingRaw,
    payload: base64UrlEncode(bytes)
  };
}

async function decodeBody(encoding: string, payload: string): Promise<BookmarkShareBody> {
  const bytes = base64UrlDecode(payload);
  let rawBytes: Uint8Array;

  if (encoding === bookmarkEncodingGzip) {
    if (!supportsGzipCompression()) {
      throw new Error("This browser cannot decompress bookmark links.");
    }
    rawBytes = await gzipDecompress(bytes);
  } else if (encoding === bookmarkEncodingRaw) {
    rawBytes = bytes;
  } else {
    throw new Error(`Unsupported bookmark encoding: ${encoding}`);
  }

  return JSON.parse(decoder.decode(rawBytes)) as BookmarkShareBody;
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
  const body: BookmarkShareBody = {
    version: 1,
    title,
    history,
    sheet
  };

  const checksum = await digestHex(JSON.stringify(body));
  const encoded = await encodeBody({ ...body, checksum });

  return `${bookmarkVersion}.${encoded.encoding}.${encoded.payload}`;
}

export async function createBookmarkShareUrl(origin: string, pathname: string, sheet: Sheet, history: History, title: string): Promise<{ url: string; bookmarkTitle: string; fragmentLength: number; }> {
  const bookmarkTitle = formatBookmarkTitle(title);
  const fragment = await createBookmarkShareFragment(sheet, history, title);
  const url = new URL(origin);
  url.pathname = pathname;
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
  const body = await decodeBody(encoding, payload);
  const { checksum, ...withoutChecksum } = body as BookmarkSharePayload;
  const expectedChecksum = await digestHex(JSON.stringify(withoutChecksum));

  if (checksum !== expectedChecksum) {
    throw new Error("Bookmark share link checksum mismatch.");
  }

  return body as BookmarkSharePayload;
}
