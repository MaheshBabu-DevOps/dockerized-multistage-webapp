// All calls go to /api. Nginx (in Docker) or the Vite dev proxy forwards them to the backend.

async function request(path, options) {
  const response = await fetch(path, options);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response;
}

export async function listNotes() {
  const response = await request('/api/notes');
  return { notes: await response.json(), cache: response.headers.get('X-Cache') };
}

export async function createNote(title, content) {
  const response = await request('/api/notes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, content }),
  });
  return response.json();
}

export async function deleteNote(id) {
  await request(`/api/notes/${id}`, { method: 'DELETE' });
}
