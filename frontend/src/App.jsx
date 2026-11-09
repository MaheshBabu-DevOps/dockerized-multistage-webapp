import { useCallback, useEffect, useState } from 'react';

import { createNote, deleteNote, listNotes } from './api.js';

export default function App() {
  const [notes, setNotes] = useState([]);
  const [cache, setCache] = useState(null);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    try {
      const result = await listNotes();
      setNotes(result.notes);
      setCache(result.cache);
      setError('');
    } catch {
      setError('Could not load notes. Is the backend running?');
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!title.trim()) return;
    try {
      await createNote(title.trim(), content.trim());
      setTitle('');
      setContent('');
      await refresh();
    } catch {
      setError('Could not save the note.');
    }
  }

  async function handleDelete(id) {
    try {
      await deleteNote(id);
      await refresh();
    } catch {
      setError('Could not delete the note.');
    }
  }

  return (
    <main className="container">
      <header>
        <h1>Notes</h1>
        <p className="subtitle">
          React frontend, FastAPI backend, PostgreSQL and a Redis cache, all running in Docker.
        </p>
        {cache && (
          <span className={`badge badge-${cache.toLowerCase()}`} data-testid="cache-badge">
            cache: {cache}
          </span>
        )}
      </header>

      <form onSubmit={handleSubmit} className="card">
        <input
          aria-label="Title"
          placeholder="Title"
          value={title}
          maxLength={100}
          onChange={(e) => setTitle(e.target.value)}
        />
        <textarea
          aria-label="Content"
          placeholder="Write something..."
          value={content}
          maxLength={2000}
          onChange={(e) => setContent(e.target.value)}
        />
        <button type="submit">Add note</button>
      </form>

      {error && <p role="alert" className="error">{error}</p>}

      <ul className="notes">
        {notes.map((note) => (
          <li key={note.id} className="card">
            <div>
              <h2>{note.title}</h2>
              {note.content && <p>{note.content}</p>}
            </div>
            <button
              className="danger"
              aria-label={`Delete ${note.title}`}
              onClick={() => handleDelete(note.id)}
            >
              Delete
            </button>
          </li>
        ))}
        {notes.length === 0 && !error && <li className="empty">No notes yet. Add the first one.</li>}
      </ul>
    </main>
  );
}
