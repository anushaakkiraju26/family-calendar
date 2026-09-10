import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Kinday — Family activity planner',
  description: 'A calmer shared calendar for busy families.',
  openGraph: {
    title: 'Kinday — Family activity planner',
    description: 'A calmer week starts here.',
    images: [{ url: '/og.png', width: 1731, height: 909, alt: 'Kinday — A calmer week starts here.' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Kinday — Family activity planner',
    description: 'A calmer week starts here.',
    images: ['/og.png'],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
