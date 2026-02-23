"use client";

import OrgCanvas from "@/components/OrgCanvas";
import { useParams } from "next/navigation";

export default function SessionPage() {
    const params = useParams();
    const id = params?.id as string;

    if (!id) return null;

    return <OrgCanvas projectId={id} />;
}
