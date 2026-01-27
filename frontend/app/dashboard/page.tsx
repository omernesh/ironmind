"use client";

import { useSession, signOut } from "@/lib/auth-client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function DashboardPage() {
  const { data: session, isPending } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (!isPending && !session) {
      router.push("/login");
    }
  }, [session, isPending, router]);

  if (isPending) {
    return <div className="p-8">Loading...</div>;
  }

  if (!session) {
    return null;
  }

  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold mb-4">Dashboard</h1>
      <p className="mb-4">Welcome, {session.user.name || session.user.email}</p>
      <p className="text-sm text-gray-600 mb-4">User ID: {session.user.id}</p>
      <button
        onClick={() => signOut().then(() => router.push("/"))}
        className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
      >
        Sign Out
      </button>
    </main>
  );
}
