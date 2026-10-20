import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import './globals.css';
export const metadata: Metadata = { title: 'Typewriter · Un espacio para escribir', description: 'Tu máquina de escribir personal. Escribe con sonido de teclas y guarda tus textos con tu cuenta de GitHub.' };
export default function Layout({ children }: Readonly<{ children: ReactNode }>) {
  return <html lang="es"><body>{children}</body></html>;
}
