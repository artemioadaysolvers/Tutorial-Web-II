import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import './globals.css';
export const metadata: Metadata = { title: 'Recados · Tu espacio personal', description: 'Tus notas y pendientes, siempre contigo. Accede con GitHub.' };
export default function Layout({ children }: Readonly<{ children: ReactNode }>) {
  return <html lang="es"><body>{children}</body></html>;
}
