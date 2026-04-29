import Link from "next/link";

export default function Header() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link href="/" className="flex items-center gap-2 font-semibold text-slate-900">
          <span aria-hidden>🛡️</span>
          <span>ShopGuard</span>
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          <Link href="/report" className="hover:underline">Report</Link>
          <Link href="/my-page" className="hover:underline">My Page</Link>
          <Link href="/login" className="hover:underline">Login</Link>
        </nav>
      </div>
    </header>
  );
}
