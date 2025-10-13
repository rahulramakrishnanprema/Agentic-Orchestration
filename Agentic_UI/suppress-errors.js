// Aggressive console override to suppress all proxy errors
// This must run at the very start

// Store original methods
const originalError = console.error.bind(console);
const originalWarn = console.warn.bind(console);
const originalLog = console.log.bind(console);

const shouldSuppress = (args) => {
  const str = args.map(a => {
    if (a instanceof Error) return a.message + (a.stack || '');
    if (typeof a === 'object' && a !== null) {
      try { return JSON.stringify(a); } catch { return String(a); }
    }
    return String(a);
  }).join(' ');

  return str.includes('proxy error') ||
    str.includes('ECONNREFUSED') ||
    str.includes('AggregateError') ||
    str.includes('internalConnectMultiple') ||
    str.includes('afterConnectMultiple') ||
    str.includes('createConnectionError') ||
    str.includes('Proxy error') ||
    str.includes('[vite] http proxy error') ||
    str.includes('::1:8080') ||
    str.includes('127.0.0.1:8080') ||
    str.includes('errno: -4078');
};

console.error = function(...args) {
  if (shouldSuppress(args)) return;
  originalError(...args);
};

console.warn = function(...args) {
  if (shouldSuppress(args)) return;
  originalWarn(...args);
};

console.log = function(...args) {
  if (shouldSuppress(args)) return;
  originalLog(...args);
};

// Also override process.stderr.write to catch low-level writes
const originalStderrWrite = process.stderr.write.bind(process.stderr);
process.stderr.write = function(chunk, encoding, callback) {
  const str = String(chunk);
  if (shouldSuppress([str])) {
    if (typeof encoding === 'function') {
      encoding();
    } else if (typeof callback === 'function') {
      callback();
    }
    return true;
  }
  return originalStderrWrite(chunk, encoding, callback);
};

// Override process.stdout.write as well
const originalStdoutWrite = process.stdout.write.bind(process.stdout);
process.stdout.write = function(chunk, encoding, callback) {
  const str = String(chunk);
  if (shouldSuppress([str])) {
    if (typeof encoding === 'function') {
      encoding();
    } else if (typeof callback === 'function') {
      callback();
    }
    return true;
  }
  return originalStdoutWrite(chunk, encoding, callback);
};

export {};
