// Positions below arrange actual backend nodes; they create no data or links.
export function layoutGraph(nodes) {
  const others = nodes.filter(node => node.type !== 'actor');
  return nodes.map(node => {
    if (node.position) return node;
    if (node.type === 'actor') return {...node,position:[0,0,0]};
    const i = others.indexOf(node), angle = -Math.PI / 2 + i * Math.PI * 2 / Math.max(1,others.length);
    const radius = i % 2 ? 185 : 210;
    return {...node, position:[Math.cos(angle)*radius, Math.sin(angle)*radius*.65, Math.sin(angle*2)*85]};
  });
}
export function filteredGraph(actor, {step=null,threshold=0,types=new Set(['alias','key','wallet','source'])} = {}) {
  if (!actor?.graph) return {nodes:[],edges:[]};
  const date = step === null ? null : actor.events?.[step]?.date;
  // Unknown observation dates are never asserted to exist at a historical moment.
  const visibleAtTime = item => step === null || (date && item.observedAt && Date.parse(item.observedAt) <= Date.parse(date));
  const nodes = actor.graph.nodes.filter(n => (n.type === 'actor' || types.has(n.type)) && visibleAtTime(n));
  const ids = new Set(nodes.map(n => n.id));
  const edges = actor.graph.edges.filter(e => ids.has(e.from) && ids.has(e.to) && visibleAtTime(e) && (threshold === 0 || (e.confidence !== null && e.confidence >= threshold)));
  const used = new Set(edges.flatMap(e => [e.from,e.to]));
  return {nodes:threshold > 0 ? nodes.filter(n => n.type === 'actor' || used.has(n.id)) : nodes, edges};
}
