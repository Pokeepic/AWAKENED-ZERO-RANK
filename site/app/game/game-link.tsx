"use client";

import type { ComponentProps } from "react";
import NextLink from "next/link";

export default function GameLink(props: ComponentProps<typeof NextLink>) {
  return <NextLink {...props} prefetch={false} />;
}
