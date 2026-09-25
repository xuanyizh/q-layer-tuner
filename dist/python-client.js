// UI transport only: use the same Python core locally or in a browser worker.
export class PythonClient {
  constructor() { this.counter = 0; this.pending = new Map(); this.mode = null; }
  async initialize() {
    // The local server identifies its API. Static deployments return 404 here.
    try {
      const response = await fetch('./api/health', {signal: AbortSignal.timeout(1800)});
      const health = response.ok ? await response.json() : null;
      if (health?.service === 'q-layer-python' && health?.version === '2.1.0') this.mode = 'local';
    } catch { /* Static hosting: use bundled browser Python. */ }
    if (!this.mode) {
      this.mode = 'browser';
      this.worker = new Worker(new URL('./engine-worker.mjs', import.meta.url), {type: 'module'});
      this.worker.onmessage = ({data}) => {
        const item = this.pending.get(data.id);
        if (!item) return;
        clearTimeout(item.timeout); this.pending.delete(data.id);
        if (data.error) item.reject(new Error(data.error)); else item.resolve(data.result);
      };
      this.worker.onerror = () => this.fail(new Error('Unable to start browser Python. Reload, or use the included local Python launcher.'));
      this.worker.onmessageerror = () => this.fail(new Error('Unable to read a Python calculation result.'));
    }
    return this.request({action: 'metadata'});
  }
  fail(error) {
    for (const item of this.pending.values()) { clearTimeout(item.timeout); item.reject(error); }
    this.pending.clear();
  }
  async request(payload) {
    if (this.mode === 'local') {
      const response = await fetch('./api/compute', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload), signal: AbortSignal.timeout(30000)});
      const body = await response.json();
      if (!response.ok || body.error) throw new Error(body.error || 'Calculation failed.');
      return body.result;
    }
    const id = ++this.counter;
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => { this.pending.delete(id); reject(new Error('Python is taking too long to respond. Reload, or use the local Python launcher.')); }, 90000);
      this.pending.set(id, {resolve, reject, timeout});
      this.worker.postMessage({id, payload});
    });
  }
}
