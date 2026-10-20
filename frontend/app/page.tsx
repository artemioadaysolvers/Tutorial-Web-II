"use client";
import type { FormEvent, KeyboardEvent, MouseEvent } from 'react';
import { useEffect, useRef, useState } from 'react';

type Account = { name: string };
type Note = { id: string; body: string; created: string };
type SessionResponse = { user: Account | null; csrf: string };
type NotesResponse = { recados: Note[] };
type SaveResponse = { recado: Note };
type Sound = 'boton' | 'teclado';

class ApiError extends Error {
  constructor(message: string, readonly status: number) { super(message); }
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

function TypewriterIcon() {
  return <svg viewBox="0 0 40 36" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M12 15V2h17v13M15 6h11M15 10h11M7 16h27l3 15H3l4-15ZM9 31v3h22v-3M4 12v7M1 12h7M9 21h3m3 0h3m3 0h3m3 0h3M10 25h3m3 0h3m3 0h3m3 0h3M14 28h12"/><path d="M10 15v-3h21v3"/></svg>;
}

export default function Home() {
  const [account, setAccount] = useState<Account | null>(null);
  const [ready, setReady] = useState(false);
  const [notes, setNotes] = useState<Note[]>([]);
  const [body, setBody] = useState('');
  const [status, setStatus] = useState('Conectando con tu espacio…');
  const [failed, setFailed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [sound, setSound] = useState(true);
  const [savedBody, setSavedBody] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const csrf = useRef('');
  const field = useRef<HTMLTextAreaElement | null>(null);
  const form = useRef<HTMLFormElement | null>(null);
  const audio = useRef<Record<Sound, HTMLAudioElement[]>>({ boton: [], teclado: [] });
  const audioIndex = useRef<Record<Sound, number>>({ boton: 0, teclado: 0 });
  const leaving = useRef(false);
  const logoutBusy = useRef(false);
  const hasChanges = body.length > 0 && body !== savedBody;
  const words = body.trim() ? body.trim().split(/\s+/u).length : 0;

  useEffect(() => {
    for (const name of ['boton', 'teclado'] as const) {
      audio.current[name] = Array.from({ length: name === 'teclado' ? 12 : 4 }, () => {
        const clip = new Audio(`/static/sounds/${name}.wav`);
        clip.preload = 'auto';
        clip.volume = name === 'teclado' ? 0.55 : 0.65;
        return clip;
      });
    }
    try { setSound(localStorage.getItem('typewriter-sound') !== 'off'); } catch { /* Audio works without browser storage. */ }
    return () => { Object.values(audio.current).flat().forEach(clip => { clip.pause(); clip.removeAttribute('src'); clip.load(); }); };
  }, []);

  function play(name: Sound, enabled = sound) {
    if (!enabled) return;
    const clips = audio.current[name];
    if (!clips.length) return;
    const clip = clips[audioIndex.current[name]++ % clips.length];
    clip.currentTime = 0;
    void clip.play().catch(() => { /* A blocked sound must never interrupt writing. */ });
  }

  function buttonSound(event: MouseEvent<HTMLDivElement>) {
    const target = event.target;
    if (target instanceof Element && target.closest('button, a')) play('boton');
  }

  function toggleSound() {
    if (!sound) play('boton', true);
    setSound(!sound);
    try { localStorage.setItem('typewriter-sound', sound ? 'off' : 'on'); } catch { /* Preference is optional. */ }
  }

  async function api<T>(url: string, options: RequestInit = {}): Promise<T> {
    const response = await fetch(url, { ...options, credentials: 'same-origin', cache: 'no-store', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf.current } });
    if (response.status === 401) {
      setAccount(null); setNotes([]);
      throw new ApiError('Tu sesión venció. Tu texto sigue aquí; vuelve a iniciar sesión para guardarlo.', 401);
    }
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new ApiError(data.error || 'No se pudo completar la operación. Intenta nuevamente.', response.status);
    }
    return (response.status === 204 ? null : await response.json()) as T;
  }

  async function load() {
    setFailed(false); setStatus('Conectando con tu espacio…');
    try {
      const data = await api<SessionResponse>('/api/session');
      csrf.current = data.csrf; setAccount(data.user);
      let restored = false;
      try {
        const draft = sessionStorage.getItem('typewriter-pending');
        if (draft) { setBody(draft.slice(0, 2000)); restored = true; sessionStorage.removeItem('typewriter-pending'); }
      } catch { /* Writing does not depend on browser storage. */ }
      if (data.user) {
        const result = await api<NotesResponse>('/api/recados'); setNotes(result.recados);
      } else { setNotes([]); }
      setStatus(restored ? (data.user ? 'Borrador recuperado. Revisa la cuenta y pulsa Guardar texto para guardarlo.' : 'Borrador recuperado. Inicia sesión para guardarlo.') : '');
    } catch (error) { setStatus(errorMessage(error, 'Revisa tu conexión.')); setFailed(true); }
    finally { setReady(true); }
  }
  useEffect(() => { void load(); }, []);

  useEffect(() => {
    function beforeUnload(event: BeforeUnloadEvent) {
      if (hasChanges && !leaving.current) { event.preventDefault(); }
    }
    window.addEventListener('beforeunload', beforeUnload);
    return () => window.removeEventListener('beforeunload', beforeUnload);
  }, [hasChanges]);

  function login() {
    try { sessionStorage.setItem('typewriter-pending', body); }
    catch {
      if (body && !window.confirm('El navegador no permite conservar el borrador durante el acceso. Descarga el texto antes de continuar o acepta para salir.')) return;
    }
    // The draft is carried through the existing GitHub OAuth redirect.
    leaving.current = true;
    window.location.assign('/auth/login');
  }

  async function logout(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (logoutBusy.current) return;
    if (hasChanges && !window.confirm('Tienes cambios sin guardar. ¿Quieres cerrar sesión?')) return;
    logoutBusy.current = true;
    setLoggingOut(true); setStatus('Cerrando sesión…');
    try {
      const endSession = () => fetch('/auth/logout', { method: 'POST', credentials: 'same-origin', cache: 'no-store', headers: { 'Accept': 'application/json', 'X-CSRF-Token': csrf.current } });
      let response = await endSession();
      if (response.status === 403) {
        // Another tab may have changed the session. Refresh CSRF once within
        // this same click; never require the user to press Logout again.
        const current = await api<SessionResponse>('/api/session');
        csrf.current = current.csrf;
        response = await endSession();
      }
      if (!response.ok) throw new Error('No se pudo cerrar la sesión. Vuelve a intentarlo.');
      try { sessionStorage.removeItem('typewriter-pending'); } catch { /* Storage is optional. */ }
      csrf.current = '';
      setAccount(null); setNotes([]); setBody(''); setSavedBody(null); setSelected(null);
      setFailed(false); setStatus('Sesión cerrada. Puedes entrar con otra cuenta de GitHub.');
    } catch (error) {
      setStatus(errorMessage(error, 'No se pudo cerrar la sesión. Tu texto sigue aquí.'));
    } finally {
      logoutBusy.current = false;
      setLoggingOut(false);
    }
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!body.trim() || saving || loggingOut || !ready || failed) return;
    if (!account) { login(); return; }
    setSaving(true); setStatus('');
    const submittedBody = body;
    try {
      const result = await api<SaveResponse>('/api/recados', { method: 'POST', body: JSON.stringify({ body: submittedBody }) });
      setNotes(previous => [result.recado, ...previous]); setSavedBody(submittedBody); setSelected(result.recado.id);
      setStatus('Texto guardado en tu cuenta.'); field.current?.focus();
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) { login(); }
      else { setStatus(errorMessage(error, 'No se pudo guardar. Tu texto sigue aquí.')); }
    }
    finally { setSaving(false); }
  }

  function newPage() {
    if (hasChanges && !window.confirm('Este texto tiene cambios sin guardar. ¿Quieres empezar una nueva hoja?')) return;
    setBody(''); setSavedBody(null); setSelected(null); setStatus('Nueva hoja lista.'); field.current?.focus();
  }

  function open(note: Note) {
    if (hasChanges && !window.confirm('Este texto tiene cambios sin guardar. ¿Quieres abrir otro texto?')) return;
    setBody(note.body); setSavedBody(note.body); setSelected(note.id); setStatus('Texto abierto. Los cambios se guardarán como una copia nueva.'); field.current?.focus();
  }

  function download() {
    const blob = new Blob([body], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a'); link.href = url; link.download = 'mi-texto.txt'; link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    setStatus('Texto descargado como archivo .txt.');
  }

  async function remove(note: Note) {
    if (!window.confirm('¿Borrar este texto guardado? Esta acción no se puede deshacer.')) return;
    setDeleting(note.id); setStatus('');
    try {
      await api<null>(`/api/recados/${note.id}`, { method: 'DELETE' });
      setNotes(previous => previous.filter(item => item.id !== note.id));
      if (selected === note.id) { setSelected(null); setSavedBody(null); }
      setStatus('Texto borrado de tu colección.');
    } catch (error) { setStatus(errorMessage(error, 'No se pudo borrar. Intenta nuevamente.')); }
    finally { setDeleting(null); }
  }

  function keySound(event: KeyboardEvent<HTMLTextAreaElement>) {
    play('teclado');
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
      event.preventDefault(); play('boton'); form.current?.requestSubmit();
    }
  }

  return <div className="app" onClickCapture={buttonSound}>
    <header>
      <a className="brand" href="/" aria-label="Typewriter, inicio"><span className="brand-mark"><TypewriterIcon/></span><span>typewriter<span className="brand-period">.</span></span></a>
      <span className="tag">ESCRITURA Y ARCHIVO PERSONAL</span>
      <div className="header-actions"><button className="sound-toggle" aria-pressed={sound} onClick={toggleSound} title={sound ? 'Desactivar sonidos' : 'Activar sonidos'}><span aria-hidden="true">{sound ? '◖))' : '◖×'}</span><span>Sonido {sound ? 'activado' : 'desactivado'}</span></button>{ready && (account ? <form action="/auth/logout" method="post" onSubmit={logout}><input type="hidden" name="csrf" value={csrf.current}/><button className="secondary" disabled={loggingOut || saving}>{loggingOut ? 'Cerrando sesión…' : 'Cerrar sesión'}</button></form> : <button className="secondary" onClick={login}>Entrar con GitHub</button>)}</div>
    </header>
    <main>
      <section className="heading"><div><p className="eyebrow">MODELAMIENTO MATEMÁTICO</p><h1>Máquina de Escribir<br/>para apuntes de Ingeniería Civil</h1><p className="intro">Redacta las ideas de modelamiento matemático que utilizarás en tu tesis.</p></div><div className="heading-note"><p>{account ? <>Sesión iniciada<br/><strong>{account.name}</strong></> : <>Acceso con GitHub<br/>Elige tu cuenta al entrar.</>}</p></div></section>
      <div className="workspace">
        <section className="compose" aria-label="Máquina de escribir">
          <div className="machine-toolbar"><span className="number" aria-hidden="true"/><button className="text-button" onClick={newPage} disabled={saving}>+ Nueva hoja</button></div>
          <form ref={form} onSubmit={save}>
            <div className="paper"><div className="paper-heading"><label htmlFor="body">{selected ? 'TEXTO DE TU COLECCIÓN' : 'NUEVO TEXTO'}</label><span>NO. {String(selected ? Math.max(1, notes.findIndex(note => note.id === selected) + 1) : notes.length + 1).padStart(3, '0')}</span></div><textarea ref={field} id="body" maxLength={2000} rows={14} placeholder="Escribe tu texto aquí…" value={body} onChange={event => setBody(event.target.value)} onKeyDown={keySound} spellCheck lang="es" aria-describedby="editor-hint character-count"/><div className="paper-bottom"><span>{words} {words === 1 ? 'palabra' : 'palabras'}</span><span id="character-count">{body.length} / 2000 caracteres</span></div></div>
            <div className="form-footer"><div className="save-state"><span className={body && body === savedBody ? 'dot saved' : 'dot'}/>{body && body === savedBody ? 'Guardado en tu cuenta' : hasChanges ? 'Cambios sin guardar' : 'Lista para tus ideas'}</div><div className="editor-actions"><button className="secondary" type="button" disabled={!body.length} onClick={download} aria-label="Descargar texto como archivo TXT">Descargar .txt ↓</button><button className="primary" type="submit" disabled={!ready || failed || saving || loggingOut || !body.trim() || body === savedBody}>{saving ? 'Guardando…' : !account ? 'Entrar y guardar ↗' : selected ? 'Guardar copia +' : 'Guardar texto +'}</button></div></div>
          </form>
          <p className="hint" id="editor-hint">{account ? 'Tus textos se guardan en tu cuenta. Solo tú puedes verlos.' : 'Al guardar, GitHub te permitirá elegir una cuenta. Tu borrador se conservará en esta pestaña.'}<span>Ctrl / ⌘ + S para guardar</span></p>
        </section>
        <aside className="collection" aria-labelledby="collection-title"><div className="list-heading"><span className="number" aria-hidden="true"/><span className="count">{notes.length.toString().padStart(2, '0')}</span></div><h2 id="collection-title">Mis textos</h2><p className="collection-intro">Tu archivo personal.</p>
          {!ready ? <div className="empty"><span className="empty-icon"><TypewriterIcon/></span><h3>Preparando tu espacio…</h3></div> : !notes.length && <div className="empty"><span className="empty-icon"><TypewriterIcon/></span><h3>{account ? 'Sin textos guardados.' : 'Inicia sesión para ver tu archivo.'}</h3><p>{account ? <>Los textos que guardes<br/>aparecerán aquí.</> : <>Accede con tu cuenta de GitHub<br/>para consultar y guardar textos.</>}</p></div>}
          <div className="notes">{notes.map((note, index) => <article className={`note${selected === note.id ? ' selected' : ''}`} key={note.id}><button className="note-open" onClick={() => open(note)} aria-label={`Abrir texto: ${note.body.slice(0, 60)}`}><span className="note-number">TEXTO {String(notes.length - index).padStart(3, '0')} <span aria-hidden="true">↗</span></span><p>{note.body}</p></button><div className="note-footer"><time dateTime={note.created}>{new Date(note.created).toLocaleString('es', { dateStyle: 'medium', timeStyle: 'short' })}</time><button className="delete" aria-label={`Borrar texto: ${note.body.slice(0,60)}`} disabled={deleting !== null} onClick={() => remove(note)}>{deleting === note.id ? 'Borrando…' : 'Borrar'}</button></div></article>)}</div>
          <div className="archive-foot"><p>Archivo privado.<br/>Vinculado a tu cuenta de GitHub.</p></div>
        </aside>
      </div>
      <div className={`feedback${failed ? ' error' : ''}`}><p role="status" aria-live="polite">{status}</p>{failed && <button className="secondary" onClick={() => { void load(); }}>Volver a conectar</button>}</div>
    </main>
    <footer><span>TYPEWRITER / ESCRITURA Y ARCHIVO PERSONAL</span><span>Redacta. Revisa. Guarda.</span></footer>
  </div>;
}
