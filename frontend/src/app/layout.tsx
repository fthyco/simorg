import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
    title: "OrgKernel — Organizational Structure Visualizer",
    description:
        "Deterministic organizational kernel — event-sourced structure visualization with graph analysis",
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en">
            <body>{children}</body>
        </html>
    );
}
