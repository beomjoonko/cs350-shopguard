"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export default function HomePage() {
  const router = useRouter();
  const [url, setUrl] = useState("");

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    router.push(`/search?url=${encodeURIComponent(url.trim())}`);
  }

  async function pasteFromClipboard() {
    try {
      const text = await navigator.clipboard.readText();
      if (text) setUrl(text);
    } catch {
      // permission denied
    }
  }

  return (
    <section className="flex flex-col items-center pt-12 text-center">
      <div className="text-5xl" aria-hidden>🛡️</div>
      <h1 className="mt-4 text-3xl font-bold">
        Safe Shopping with <span className="text-blue-600">ShopGuard</span>
      </h1>
      <p className="mt-2 text-slate-600">Enter a product link to check fraud risk</p>

      <form onSubmit={onSubmit} className="mt-6 flex w-full max-w-xl gap-2">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste product link here"
          className="flex-1 rounded-lg border border-slate-300 px-4 py-2 focus:border-blue-500 focus:outline-none"
        />
        <button
          type="button"
          onClick={pasteFromClipboard}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50"
        >
          Paste
        </button>
        <button
          type="submit"
          className="rounded-lg bg-slate-900 px-5 py-2 font-medium text-white hover:bg-slate-800"
        >
          Search
        </button>
      </form>
    </section>
  );
}
