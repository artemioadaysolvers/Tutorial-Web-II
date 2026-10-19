"use client";
import { useEffect, useRef, useState } from 'react';

function MicrosoftIcon() {
  return <svg width="19" height="19" viewBox="0 0 20 20" aria-hidden="true"><path fill="#f25022" d="M0 0h9v9H0z"/><path fill="#7fba00" d="M11 0h9v9h-9z"/><path fill="#00a4ef" d="M0 11h9v9H0z"/><path fill="#ffb900" d="M11 11h9v9h-9z"/></svg>;
}

export default function Home() {
  const [account, setAccount] = useState(null);
  const [ready, setReady] = useState(false);
  const [notes, setNotes] = useState([]);
  const [body, setBody] = useState('');
  const [status, setStatus] = useState('Conectando con tu espacio…');
  const [failed, setFailed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(null);
  const csrf = useRef('');
  const field = useRef(null);

  async function api(url, options = {}) {
    const response = await fetch(url, { ...options, credentials: 'same-origin', cache: 'no-store', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf.current } });
    if (response.status === 401) {
      setAccount(null); setNotes([]); setBody('');
      throw new Error('Tu sesión venció. Vuelve a iniciar sesión.');
    }
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || 'No se pudo completar la operación. Intenta nuevamente.');
    }
    return response.status === 204 ? null : response.json();
  }

  async function load() {
    setFailed(false); setStatus('Cargando…');
    try {
      const data = await api('/api/session');
      csrf.current = data.csrf; setAccount(data.user); setReady(true);
      if (data.user) {
        const result = await api('/api/recados'); setNotes(result.recados);
      } else { setNotes([]); }
      setStatus('');
    } catch (error) { setReady(true); setStatus(error.message || 'Revisa tu conexión.'); setFailed(true); }
  }
  useEffect(() => { load(); }, []);

  async function save(event) {
    event.preventDefault();
    if (!body.trim() || saving) return;
    setSaving(true); setStatus('');
    try {
      const result = await api('/api/recados', { method: 'POST', body: JSON.stringify({ body }) });
      setNotes(previous => [result.recado, ...previous]); setBody('');
      setStatus('Recado guardado.'); field.current?.focus();
    } catch (error) { setStatus(error.message || 'No se pudo guardar. Intenta nuevamente.'); }
    finally { setSaving(false); }
  }

  async function remove(note) {
    if (!window.confirm('¿Borrar este recado?')) return;
    setDeleting(note.id); setStatus('');
    try {
      await api(`/api/recados/${note.id}`, { method: 'DELETE' });
      setNotes(previous => previous.filter(item => item.id !== note.id)); setStatus('Recado borrado.');
    } catch (error) { setStatus(error.message || 'No se pudo borrar. Intenta nuevamente.'); }
    finally { setDeleting(null); }
  }

  return <>
    <header><a className="brand" href="/" aria-label="Recados, inicio"><span className="brand-mark">r.</span>recados</a><span className="tag">UN ESPACIO PARA RECORDAR</span>{account && <form action="/auth/logout" method="post"><input type="hidden" name="csrf" value={csrf.current}/><button className="secondary">Cerrar sesión ↗</button></form>}</header>
    <main>
      {!ready ? <section className="loading"><span className="eyebrow">TU LIBRETA PERSONAL</span><h1>Un momento…</h1><p role="status">{status}</p></section> : !account ? <section className="welcome">
        <div><p className="eyebrow"><span className="dot"/> MENOS COSAS EN TU CABEZA</p><h1>Un lugar para<br/>tus próximos<br/><em>recados.</em></h1><p className="intro">Una idea, un pendiente, algo importante.<br/>Guárdalo aquí y sigue con tu día.</p><a className="login" href="/auth/login"><MicrosoftIcon/>Continuar con Microsoft <span>↗</span></a><small>Tu cuenta personal, de trabajo o de estudios.</small><div className="benefits"><span>✓ Solo tú ves tus notas</span><span>✓ Disponibles cuando vuelvas</span></div></div>
        <aside className="preview" aria-label="Ejemplo ilustrativo de un recado"><div className="paper"><span className="pin"/><span className="number">UNA COSA MENOS QUE RECORDAR</span><p>Las buenas ideas<br/>merecen un lugar<br/>donde quedarse.</p><span className="paper-rule"/><span className="sample-foot">ANOTA. GUARDA. RESPIRA.</span></div><span className="preview-caption">Tu memoria, con un poco más de espacio.</span></aside>
      </section> : <>
        <section className="heading"><p className="eyebrow">TU LIBRETA PERSONAL</p><h1>Hola, {account.name}.</h1><p>Deja aquí lo que no quieres olvidar.</p></section>
        <div className="workspace"><section className="compose"><span className="number">01 / ESCRIBE</span><h2>Un nuevo recado</h2><form onSubmit={save}><label htmlFor="body">¿Qué quieres recordar?</label><textarea ref={field} id="body" maxLength={2000} rows={8} placeholder="Una idea, un pendiente, algo importante…" value={body} onChange={event => setBody(event.target.value)} disabled={saving} required/><div className="form-footer"><small>{body.length} / 2000</small><button type="submit" disabled={saving || !body.trim()}>{saving ? 'Guardando…' : 'Guardar recado +'}</button></div></form><p className="hint">Guardado en tu cuenta. Solo tú puedes verlo.</p></section>
        <section className="collection"><div className="list-heading"><span className="number">02 / RECUERDA</span><span className="count">{notes.length} {notes.length === 1 ? 'recado' : 'recados'}</span></div><h2>Mis recados</h2>{!notes.length && !failed && <div className="empty"><span className="empty-icon" aria-hidden="true">✎</span><h3>Tu espacio está listo.</h3><p>Escribe tu primer recado.<br/>Lo encontrarás aquí cuando vuelvas.</p></div>}<div className="notes">{notes.map(note => <article className="note" key={note.id}><p>{note.body}</p><div className="note-footer"><time dateTime={note.created}>{new Date(note.created).toLocaleString('es', { dateStyle: 'medium', timeStyle: 'short' })}</time><button className="delete" aria-label={`Borrar recado: ${note.body.slice(0,60)}`} disabled={deleting !== null} onClick={() => remove(note)}>{deleting === note.id ? 'Borrando…' : 'Borrar'}</button></div></article>)}</div></section></div>
      </>}
      <div className="feedback"><p role="status" aria-live="polite">{ready ? status : ''}</p>{failed && <button className="secondary" onClick={load}>Volver a cargar</button>}</div>
    </main><footer><span>RECADOS / UN POCO MÁS DE ESPACIO.</span><span>Hecho para tus ideas de todos los días.</span></footer>
  </>;
}
