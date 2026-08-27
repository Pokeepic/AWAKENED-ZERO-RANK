import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Playable Prologue — AWAKENED: ZERO RANK",
  description: "A private point-and-click scene from Ren Takahashi's authenticated chronicle.",
  alternates: { canonical: "/game" },
};

export default function GameLayout({ children }: { children: React.ReactNode }) {
  return children;
}
