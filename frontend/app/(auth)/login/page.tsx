import Link from "next/link";
import { AuthForm } from "@/components/auth-form";

export default function LoginPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <h1 className="text-3xl font-bold mb-8">Login to IRONMIND</h1>
      <AuthForm mode="login" />
      <p className="mt-4 text-sm text-gray-600">
        Don't have an account?{" "}
        <Link href="/register" className="text-blue-600 hover:underline">
          Register
        </Link>
      </p>
    </main>
  );
}
