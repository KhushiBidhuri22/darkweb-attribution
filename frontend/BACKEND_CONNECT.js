/*
 * BACKEND TEAMMATE — START HERE
 *
 * This is the one file for connecting the existing frontend.
 * 1. SERVER: fill the real server address and API paths.
 * 2. RESPONSE: say where each response contains its data.
 * 3. FIELDS: match the backend's field names to the screen's field names.
 * 4. REQUESTS: adjust HTTP methods/query/body only if your API needs it.
 *
 * UI, CSS, animations and rendering are already connected to this file.
 */

// 1 — SERVER ADDRESS AND ENDPOINT PATHS
export const apiConfig = {
  baseUrl: 'http://localhost:8000', // Actual backend origin
  credentials: 'include', // Cookie session. Backend authorizes requests.
  timeoutMs: 15000,
  endpoints: {
    suggestions: '/api/suggestions', // "Try" dropdown
    search: '/api/search',           // Search results popup
    actor: '/api/actors/:id',        // Selected account: profile, graph and all six sections
    export: '/api/export/:id',       // CSV / JSON download
    session: '/api/auth/session',    // Check the signed-in personnel account
    login: '/api/auth/login',        // Sign in
    logout: '/api/auth/logout',      // Sign out
  },
};

// 2 — WHERE IS THE DATA INSIDE THE JSON RESPONSE?
export const responsePaths = {
  suggestions: 'items', // Array for the Try dropdown
  search: 'items',      // Array of matching accounts
  actor: 'actor',       // Selected account object
  session: 'user',      // User object, or null when signed out
  login: 'user',        // User object returned by sign-in
};

// 3 — FIELD NAMES
const recordFields = {
  id: 'id',
  title: 'title',
  detail: 'detail',
  source: 'source',
  date: 'date',
  confidence: 'confidence',
  nodeId: 'nodeId',
  url: 'url',
};

export const fields = {
  actor: {
    id: 'id',
    handle: 'handle',
    description: 'description',
    priority: 'priority',
    confidence: 'confidence',
    firstSeen: 'firstSeen',
    lastSeen: 'lastSeen',
    aliases: 'aliases',
    keys: 'keys',
    wallets: 'wallets',
    evidence: 'evidence',
    sources: 'sources',
    events: 'events',
    graph: 'graph',
  },
  alias: {
    id: 'id',
    handle: 'handle',
    detail: 'detail',
    confidence: 'confidence',
    nodeId: 'nodeId',
  },
  key: { ...recordFields, value: 'value', algorithm: 'algorithm' },
  wallet: { ...recordFields, value: 'value', network: 'network' },
  evidence: { ...recordFields, method: 'method' },
  source: { ...recordFields, name: 'name', observedAt: 'observedAt' },
  event: { ...recordFields, label: 'label' },
  graph: { nodes: 'nodes', edges: 'edges' },
  node: {
    id: 'id',
    name: 'name',
    type: 'type',
    identifier: 'identifier',
    relation: 'relation',
    detail: 'detail',
    confidence: 'confidence',
    observedAt: 'observedAt',
    recordId: 'recordId',
    position: 'position',
  },
  edge: {
    id: 'id',
    from: 'from',
    to: 'to',
    kind: 'kind',
    confidence: 'confidence',
    observedAt: 'observedAt',
  },
  suggestion: { label: 'label', value: 'value', type: 'type' },
  user: { id: 'id', name: 'name', role: 'role' },
};

// 4 — REQUESTS SENT TO THE BACKEND
export const backendCalls = {
  suggestions: (request, {signal}) =>
    request('suggestions', {signal}),

  search: (request, {q, type, signal}) =>
    request('search', {query: {q, type}, signal}),

  actor: (request, {id, signal}) =>
    request('actor', {id, signal}),

  session: (request, {signal}) =>
    request('session', {signal}),

  login: (request, {username, password, signal}) =>
    request('login', {method: 'POST', body: {username, password}, signal}),

  logout: (request, {signal}) =>
    request('logout', {method: 'POST', signal}),

  export: (request, {id, format, signal}) =>
    request('export', {id, query: {format}, file: true, signal}),
};

export async function getRequestHeaders() {
  return {};
}
