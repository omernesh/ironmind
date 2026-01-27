import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <h1 className="text-4xl font-bold mb-8">IRONMIND</h1>
      <p className="text-lg text-gray-600 mb-8">
        Technical Document Intelligence for Aerospace & Defense
      </p>
      <div className="flex gap-4">
        <Link
          href="/login"
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Login
        </Link>
        <Link
          href="/register"
          className="px-6 py-3 border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50"
        >
          Register
        </Link>
      </div>
    </main>
  );
}
