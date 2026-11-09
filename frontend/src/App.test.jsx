import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import App from './App.jsx';

function jsonResponse(body, headers = {}) {
  return {
    ok: true,
    status: 200,
    json: async () => body,
    headers: { get: (name) => headers[name] ?? null },
  };
}

describe('App', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('shows notes returned by the API and the cache status', async () => {
    fetch.mockResolvedValueOnce(
      jsonResponse([{ id: 1, title: 'Buy milk', content: '2 litres' }], { 'X-Cache': 'HIT' })
    );
    render(<App />);
    expect(await screen.findByText('Buy milk')).toBeInTheDocument();
    expect(screen.getByTestId('cache-badge')).toHaveTextContent('cache: HIT');
  });

  it('shows an empty state', async () => {
    fetch.mockResolvedValueOnce(jsonResponse([], { 'X-Cache': 'MISS' }));
    render(<App />);
    expect(await screen.findByText(/No notes yet/)).toBeInTheDocument();
  });

  it('sends a POST and reloads when a note is added', async () => {
    fetch
      .mockResolvedValueOnce(jsonResponse([], { 'X-Cache': 'MISS' }))
      .mockResolvedValueOnce(jsonResponse({ id: 2, title: 'New', content: '' }))
      .mockResolvedValueOnce(jsonResponse([{ id: 2, title: 'New', content: '' }], { 'X-Cache': 'MISS' }));
    render(<App />);
    await screen.findByText(/No notes yet/);

    await userEvent.type(screen.getByLabelText('Title'), 'New');
    await userEvent.click(screen.getByRole('button', { name: 'Add note' }));

    await waitFor(() => expect(screen.getByText('New')).toBeInTheDocument());
    const post = fetch.mock.calls.find(([, options]) => options?.method === 'POST');
    expect(post[0]).toBe('/api/notes');
    expect(JSON.parse(post[1].body)).toEqual({ title: 'New', content: '' });
  });

  it('shows an error when the backend is unreachable', async () => {
    fetch.mockRejectedValueOnce(new Error('network'));
    render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent(/Could not load notes/);
  });
});
