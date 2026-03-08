"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";

/* ───────────────────── Animated counter ───────────────────── */
function AnimatedNumber({ target, duration = 1800 }: { target: number; duration?: number }) {
    const [value, setValue] = useState(0);
    useEffect(() => {
        let start = 0;
        const step = Math.ceil(target / (duration / 16));
        const id = setInterval(() => {
            start += step;
            if (start >= target) { setValue(target); clearInterval(id); }
            else setValue(start);
        }, 16);
        return () => clearInterval(id);
    }, [target, duration]);
    return <>{value.toLocaleString()}</>;
}

/* ───────────────────── Floating particles ───────────────────── */
function Particles() {
    const dots = Array.from({ length: 18 }, (_, i) => ({
        id: i,
        left: `${5 + (i * 5.3) % 90}%`,
        top: `${8 + (i * 7.1) % 80}%`,
        size: 3 + (i % 4),
        delay: (i * 0.4) % 5,
        dur: 6 + (i % 5),
    }));
    return (
        <div className="about-particles" aria-hidden>
            {dots.map(d => (
                <span
                    key={d.id}
                    className="about-particle"
                    style={{
                        left: d.left,
                        top: d.top,
                        width: d.size,
                        height: d.size,
                        animationDelay: `${d.delay}s`,
                        animationDuration: `${d.dur}s`,
                    }}
                />
            ))}
        </div>
    );
}

/* ───────────────────── Feature card ───────────────────── */
function FeatureCard({ icon, title, description }: { icon: string; title: string; description: string }) {
    return (
        <div className="about-feature-card">
            <div className="about-feature-icon">{icon}</div>
            <h3 className="about-feature-title">{title}</h3>
            <p className="about-feature-desc">{description}</p>
        </div>
    );
}

/* ───────────────────── Architecture layer ───────────────────── */
function ArchLayer({ label, items, accent }: { label: string; items: string[]; accent: string }) {
    return (
        <div className="about-arch-layer" style={{ borderLeftColor: accent }}>
            <div className="about-arch-label" style={{ color: accent }}>{label}</div>
            <div className="about-arch-items">
                {items.map((t, i) => <span key={i} className="about-arch-tag">{t}</span>)}
            </div>
        </div>
    );
}

/* ═══════════════════════════════════════════════════════════════
   ABOUT / WELCOME PAGE
   ═══════════════════════════════════════════════════════════════ */
export default function AboutPage() {
    const [visible, setVisible] = useState(false);
    useEffect(() => { setVisible(true); }, []);

    return (
        <div className={`about-page ${visible ? "about-visible" : ""}`}>
            <Particles />

            {/* ── Hero ── */}
            <section className="about-hero">
                <div className="about-hero-inner">
                    <div className="about-hero-badge">Deterministic Simulation Engine</div>
                    <h1 className="about-hero-title">
                        SimOrg<span className="about-hero-dot">.</span>
                    </h1>
                    <p className="about-hero-subtitle">
                        Model organizations as evolving structural graphs.
                        Apply pressures, inject shocks, observe adaptation — with
                        <strong> 100 % byte-identical replay</strong> across every environment.
                    </p>

                    <div className="about-hero-actions">
                        <Link href="/dashboard" className="btn btn-primary about-cta">
                            Enter Control Center
                        </Link>
                        <a
                            href="https://github.com/fthyco/simorg"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn btn-secondary about-cta"
                        >
                            View on GitHub
                        </a>
                    </div>
                </div>
            </section>

            {/* ── Stats ribbon ── */}
            <section className="about-stats">
                <div className="about-stat">
                    <div className="about-stat-value"><AnimatedNumber target={8} /></div>
                    <div className="about-stat-label">Event Types</div>
                </div>
                <div className="about-stat">
                    <div className="about-stat-value"><AnimatedNumber target={7} /></div>
                    <div className="about-stat-label">Hard Invariants</div>
                </div>
                <div className="about-stat">
                    <div className="about-stat-value"><AnimatedNumber target={20} /></div>
                    <div className="about-stat-label">Industry Templates</div>
                </div>
                <div className="about-stat">
                    <div className="about-stat-value">int64</div>
                    <div className="about-stat-label">Fixed-Point Math</div>
                </div>
            </section>

            {/* ── What is SimOrg ── */}
            <section className="about-section">
                <h2 className="about-section-title">What is SimOrg?</h2>
                <p className="about-section-body">
                    SimOrg is a deterministic, event-sourced organizational simulation engine.
                    It models companies as directed dependency graphs — roles connected by
                    operational, informational, and governance edges — and lets you
                    stress-test them under realistic constraints.
                </p>
                <p className="about-section-body">
                    Every state mutation is an immutable event. Every transition is validated
                    against seven structural invariants. Every final state is verified via
                    canonical SHA-256 hashing. There are no floats, no randomness,
                    no silent repairs. <strong>Structure is truth.</strong>
                </p>
            </section>

            {/* ── Features ── */}
            <section className="about-section">
                <h2 className="about-section-title">Core Capabilities</h2>
                <div className="about-feature-grid">
                    <FeatureCard
                        icon="E"
                        title="Event-Sourced Kernel"
                        description="8 event types — add roles, inject shocks, differentiate, compress — all deterministic, all replayable."
                    />
                    <FeatureCard
                        icon="G"
                        title="Graph Analysis"
                        description="Structural density, critical cycle detection, isolated role detection — all in int64 fixed-point."
                    />
                    <FeatureCard
                        icon="T"
                        title="Industry Templates"
                        description="Generate realistic orgs for SaaS, FinTech, E-Commerce, HealthTech, EdTech — across 4 growth stages."
                    />
                    <FeatureCard
                        icon="P"
                        title="Projection Layer"
                        description="Deterministic clustering, semantic labeling, and drift detection between structure and declared semantics."
                    />
                    <FeatureCard
                        icon="V"
                        title="3-Level Visualization"
                        description="World Map, Department Graph, and Role-Level views — powered by ReactFlow with dagre auto-layout."
                    />
                    <FeatureCard
                        icon="D"
                        title="Drift Detection"
                        description="Compare declared department labels vs emergent structural clusters. Find phantom departments and hidden couplings."
                    />
                </div>
            </section>

            {/* ── Architecture stack ── */}
            <section className="about-section">
                <h2 className="about-section-title">Architecture</h2>
                <div className="about-arch-stack">
                    <ArchLayer
                        label="Frontend"
                        items={["Next.js 14", "React 18", "ReactFlow", "dagre", "TypeScript"]}
                        accent="#3b82f6"
                    />
                    <ArchLayer
                        label="Backend"
                        items={["FastAPI", "Uvicorn", "Pydantic", "pg8000"]}
                        accent="#8b5cf6"
                    />
                    <ArchLayer
                        label="Kernel"
                        items={["OrgState", "Events", "Transitions", "Invariants", "Hashing", "Snapshots"]}
                        accent="#10b981"
                    />
                    <ArchLayer
                        label="Projection"
                        items={["Clustering", "Semantic Labeler", "Drift Detection", "Topology Tracker"]}
                        accent="#f59e0b"
                    />
                    <ArchLayer
                        label="Generator"
                        items={["Industry Templates", "7-Step Compiler", "Deterministic RNG", "Replay Verification"]}
                        accent="#ef4444"
                    />
                    <ArchLayer
                        label="Persistence"
                        items={["Supabase (PostgreSQL)", "Event Store", "Stream Metadata", "Snapshots"]}
                        accent="#06b6d4"
                    />
                </div>
            </section>

            {/* ── How it works ── */}
            <section className="about-section">
                <h2 className="about-section-title">How It Works</h2>
                <div className="about-steps">
                    <div className="about-step">
                        <div className="about-step-num">1</div>
                        <div>
                            <h3>Generate</h3>
                            <p>Pick an industry and growth stage. The generator compiles a deterministic event stream from realistic templates.</p>
                        </div>
                    </div>
                    <div className="about-step">
                        <div className="about-step-num">2</div>
                        <div>
                            <h3>Simulate</h3>
                            <p>Apply events — shocks, constraints, differentiations, compressions. Watch the structure evolve in real-time.</p>
                        </div>
                    </div>
                    <div className="about-step">
                        <div className="about-step-num">3</div>
                        <div>
                            <h3>Analyze</h3>
                            <p>Inspect structural density, debt accumulation, drift between declared and emergent departments.</p>
                        </div>
                    </div>
                    <div className="about-step">
                        <div className="about-step-num">4</div>
                        <div>
                            <h3>Verify</h3>
                            <p>Replay the full event stream. Compare SHA-256 hashes. Confirm byte-identical determinism across environments.</p>
                        </div>
                    </div>
                </div>
            </section>

            {/* ── Principles ── */}
            <section className="about-section">
                <h2 className="about-section-title">Design Philosophy</h2>
                <div className="about-principles">
                    <div className="about-principle">
                        <span className="about-principle-marker" />
                        Structure is truth. Semantics are overlays.
                    </div>
                    <div className="about-principle">
                        <span className="about-principle-marker" />
                        Events are the only source of change.
                    </div>
                    <div className="about-principle">
                        <span className="about-principle-marker" />
                        Replay is the only source of reconstruction.
                    </div>
                    <div className="about-principle">
                        <span className="about-principle-marker" />
                        Determinism is non-negotiable.
                    </div>
                    <div className="about-principle">
                        <span className="about-principle-marker" />
                        No floats. No silent repairs. No implicit mutation.
                    </div>
                </div>
            </section>

            {/* ── CTA footer ── */}
            <section className="about-footer-cta">
                <h2>Ready to model your first organization?</h2>
                <Link href="/dashboard" className="btn btn-primary about-cta" style={{ fontSize: 15 }}>
                    Enter Control Center
                </Link>
            </section>

            {/* ── Footer ── */}
            <footer className="about-footer">
                <div className="about-footer-inner">
                    <span>SimOrg — Deterministic Organizational Simulation Engine</span>
                    <span className="about-footer-sep">|</span>
                    <span>Built with precision for the systems thinking community</span>
                </div>
            </footer>
        </div>
    );
}
