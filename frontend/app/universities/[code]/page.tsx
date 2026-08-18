import type { Metadata } from "next";
import { UniversityDetail } from "@/components/university-detail";

const universities: Record<string, string> = {
  uitm: "Universiti Teknologi MARA",
  unimap: "Universiti Malaysia Perlis",
  uum: "Universiti Utara Malaysia",
  um: "Universiti Malaya",
  ukm: "Universiti Kebangsaan Malaysia",
};

export async function generateMetadata({ params }: { params: Promise<{ code: string }> }): Promise<Metadata> {
  const { code } = await params;
  const name = universities[code] ?? "Universiti";
  const title = `${name} — UniDate`;
  const description = `Kalendar akademik ${name} yang telah disemak, dengan pautan kepada sumber asal.`;
  return {
    title,
    description,
    openGraph: { title, description, images: [] },
    twitter: { title, description, images: [] },
  };
}

export default async function UniversityPage({ params }: { params: Promise<{ code: string }> }) {
  const { code } = await params;
  return <UniversityDetail code={code} />;
}
