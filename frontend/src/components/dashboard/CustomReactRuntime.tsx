import { useEffect, useRef, useState } from 'react';
import { Box, ShieldCheck } from 'lucide-react';

import type { PanelView } from '../../lib/v2-api';
import { Status } from '../ui';

export const CUSTOM_RUNTIME_VERSION = 'custom-react-sandbox-v1';

const MAX_SOURCE_BYTES = 50_000;
// Babel's isolated worker is a lazily downloaded 3 MB asset. Cold parsing can
// take several seconds on constrained devices; this budget is separate from
// the untrusted component execution limit, which remains 250 ms below.
const COMPILE_TIMEOUT_MS = 8_000;
const PARENT_TIMEOUT_MS = 1_500;
const FORBIDDEN_DEPENDENCY = /(^|\n)\s*import(?:\s|["'])|\bimport\s*\(|\brequire\s*\(/m;

type RuntimeNode =
  | { kind: 'text'; value: string }
  | { kind: 'element'; tag: string; children: RuntimeNode[] };

type RuntimeMessage = {
  channel: 'autoprism-custom-runtime-v1';
  requestId: string;
  ok: boolean;
  tree?: RuntimeNode | null;
  error?: string;
};

declare function __loadComponent(React: unknown): unknown;

function sandboxBootstrap() {
  const channel = 'autoprism-custom-runtime-v1';

  function workerRuntime() {
    const emit = globalThis.postMessage.bind(globalThis);
    const maxDepth = 18;
    const maxNodes = 500;
    const maxTextLength = 8_000;
    const allowedTags = new Set([
      'div', 'span', 'strong', 'em', 'small', 'p', 'h3', 'h4', 'ul', 'ol', 'li',
      'table', 'thead', 'tbody', 'tr', 'th', 'td', 'dl', 'dt', 'dd', 'code', 'pre',
    ]);
    const isArray = Array.isArray.bind(Array);
    const isAllowedTag = Set.prototype.has.bind(allowedTags);
    let nodeCount = 0;

    const deny = () => {
      throw new Error('network and nested runtime APIs are disabled');
    };
    for (const name of [
      'fetch', 'XMLHttpRequest', 'WebSocket', 'EventSource', 'importScripts',
      'Worker', 'SharedWorker', 'BroadcastChannel',
    ]) {
      try {
        Object.defineProperty(globalThis, name, {
          value: deny,
          configurable: false,
          writable: false,
        });
      } catch {
        // Missing worker globals are already unavailable.
      }
    }
    Object.defineProperty(globalThis, 'postMessage', {
      value: undefined,
      configurable: false,
      writable: false,
    });

    const fragment = '__AUTOPRISM_FRAGMENT__';
    const React = Object.freeze({
      Fragment: fragment,
      createElement(type: unknown, props: unknown, ...children: unknown[]) {
        return { __autoprismElement: true, type, props: props ?? {}, children };
      },
    });

    function sanitize(value: unknown, depth = 0): RuntimeNode | null {
      if (depth > maxDepth) throw new Error('component output exceeds depth limit');
      if (value === null || value === undefined || value === false || value === true) {
        return null;
      }
      if (typeof value === 'string' || typeof value === 'number') {
        nodeCount += 1;
        if (nodeCount > maxNodes) throw new Error('component output exceeds node limit');
        const text = String(value);
        if (text.length > maxTextLength) throw new Error('component text exceeds limit');
        return { kind: 'text', value: text };
      }
      if (isArray(value)) {
        const children = value
          .map((item) => sanitize(item, depth + 1))
          .filter((item): item is RuntimeNode => item !== null);
        return { kind: 'element', tag: 'div', children };
      }
      if (typeof value !== 'object') throw new Error('component returned an unsupported value');
      const element = value as {
        __autoprismElement?: boolean;
        type?: unknown;
        props?: Record<string, unknown>;
        children?: unknown[];
      };
      if (element.__autoprismElement !== true) {
        throw new Error('component must return React elements or text');
      }
      if (typeof element.type === 'function') {
        const componentProps = Object.freeze({
          ...(element.props ?? {}),
          children: element.children ?? [],
        });
        return sanitize(element.type(componentProps), depth + 1);
      }
      const children = (element.children ?? [])
        .flat(Infinity)
        .map((item) => sanitize(item, depth + 1))
        .filter((item): item is RuntimeNode => item !== null);
      if (element.type === fragment) {
        return { kind: 'element', tag: 'div', children };
      }
      if (typeof element.type !== 'string' || !isAllowedTag(element.type)) {
        throw new Error('component used a non-allowlisted element');
      }
      nodeCount += 1;
      if (nodeCount > maxNodes) throw new Error('component output exceeds node limit');
      return { kind: 'element', tag: element.type, children };
    }

    globalThis.onmessage = (event: MessageEvent) => {
      try {
        const Component = __loadComponent(React);
        if (typeof Component !== 'function') {
          throw new Error('default export must be a component function');
        }
        const output = Component(Object.freeze(event.data));
        if (output && typeof output.then === 'function') {
          throw new Error('async components are not supported');
        }
        emit({ ok: true, tree: sanitize(output) });
      } catch (reason) {
        emit({
          ok: false,
          error: reason instanceof Error ? reason.message.slice(0, 240) : 'runtime failed',
        });
      }
    };
  }

  window.addEventListener('message', (event) => {
    if (event.source !== parent) return;
    const message = event.data;
    if (
      !message
      || message.channel !== channel
      || typeof message.requestId !== 'string'
      || typeof message.compiled !== 'string'
    ) return;

    const workerSource = [
      '"use strict";',
      'function __loadComponent(React) {',
      '  const module = { exports: {} };',
      '  const exports = module.exports;',
      message.compiled,
      '  return module.exports.default || exports.default;',
      '}',
      `(${workerRuntime.toString()})();`,
    ].join('\n');
    const workerUrl = URL.createObjectURL(new Blob([workerSource], { type: 'text/javascript' }));
    const worker = new Worker(workerUrl);
    let settled = false;
    const finish = (payload: { ok: boolean; tree?: unknown; error?: string }) => {
      if (settled) return;
      settled = true;
      worker.terminate();
      URL.revokeObjectURL(workerUrl);
      parent.postMessage({ channel, requestId: message.requestId, ...payload }, '*');
    };
    const timeout = window.setTimeout(
      () => finish({ ok: false, error: 'component exceeded 250 ms execution limit' }),
      250,
    );
    worker.onmessage = (workerEvent) => {
      window.clearTimeout(timeout);
      finish(workerEvent.data);
    };
    worker.onerror = () => {
      window.clearTimeout(timeout);
      finish({ ok: false, error: 'isolated worker failed' });
    };
    worker.postMessage(message.props);
  });
}

const SANDBOX_DOCUMENT = `<!doctype html>
<html><head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline' blob:; worker-src blob:; connect-src 'none'; img-src 'none'; style-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'">
</head><body><script>(${sandboxBootstrap.toString()})();</script></body></html>`;

async function sha256(value: string) {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
}

async function compileSource(source: string) {
  if (new TextEncoder().encode(source).byteLength > MAX_SOURCE_BYTES) {
    throw new Error('源码超过 50 KB 运行上限');
  }
  if (!/\bexport\s+default\b/.test(source)) {
    throw new Error('源码必须包含 export default 组件');
  }
  if (FORBIDDEN_DEPENDENCY.test(source)) {
    throw new Error('隔离运行时 v1 不允许 import、dynamic import 或 require');
  }
  const result = await new Promise<string>((resolve, reject) => {
    const compiler = new Worker(
      new URL('./CustomCompiler.worker.ts', import.meta.url),
      { type: 'module' },
    );
    const timeout = window.setTimeout(() => {
      compiler.terminate();
      reject(new Error('隔离编译器冷启动超过 8000 ms 上限'));
    }, COMPILE_TIMEOUT_MS);
    compiler.onmessage = (event: MessageEvent<{ ok: boolean; code?: string; error?: string }>) => {
      window.clearTimeout(timeout);
      compiler.terminate();
      if (!event.data.ok || !event.data.code) {
        reject(new Error(event.data.error || '组件编译失败'));
        return;
      }
      resolve(event.data.code);
    };
    compiler.onerror = () => {
      window.clearTimeout(timeout);
      compiler.terminate();
      reject(new Error('隔离编译工作线程失败'));
    };
    compiler.postMessage({ source });
  });
  if (/\brequire\s*\(/.test(result)) {
    throw new Error('源码编译结果包含未允许依赖');
  }
  return result;
}

function RuntimeTree({ node }: { node: RuntimeNode }) {
  if (node.kind === 'text') return node.value;
  const Tag = node.tag as keyof JSX.IntrinsicElements;
  return (
    <Tag>
      {node.children.map((child, index) => <RuntimeTree key={index} node={child} />)}
    </Tag>
  );
}

export function CustomReactRuntime({ panel }: { panel: PanelView }) {
  const frameRef = useRef<HTMLIFrameElement>(null);
  const [frameReady, setFrameReady] = useState(false);
  const [compiled, setCompiled] = useState<string>();
  const [tree, setTree] = useState<RuntimeNode | null>();
  const [error, setError] = useState('');
  const inputLabel = panel.data_state === 'unverified'
    ? 'UNVERIFIED INPUT'
    : panel.data_state === 'invalid'
      ? 'INVALID INPUT BLOCKED'
      : 'NO EXTRACTION INPUT';

  useEffect(() => {
    let cancelled = false;
    setCompiled(undefined);
    setTree(undefined);
    setError('');
    const prepare = async () => {
      const contract = panel.visualization_contract;
      if (
        contract.runtime !== CUSTOM_RUNTIME_VERSION
        || !Array.isArray(contract.dependencies)
        || contract.dependencies.length !== 0
      ) {
        throw new Error('该版本没有冻结 custom-react-sandbox-v1 空依赖契约');
      }
      if (!panel.component_code || !panel.component_code_sha256) {
        throw new Error('该版本缺少冻结组件源码或 SHA-256');
      }
      const actualHash = await sha256(panel.component_code);
      if (actualHash !== panel.component_code_sha256) {
        throw new Error('组件源码哈希不匹配，运行已阻止');
      }
      const output = await compileSource(panel.component_code);
      if (!cancelled) setCompiled(output);
    };
    void prepare().catch((reason) => {
      if (!cancelled) setError(reason instanceof Error ? reason.message : '组件准备失败');
    });
    return () => {
      cancelled = true;
    };
  }, [panel.component_code, panel.component_code_sha256, panel.visualization_contract]);

  useEffect(() => {
    if (!compiled || !frameReady || !frameRef.current?.contentWindow) return undefined;
    const requestId = crypto.randomUUID();
    const targetWindow = frameRef.current.contentWindow;
    const timeout = window.setTimeout(() => {
      setError('隔离运行时没有在期限内返回');
      setTree(undefined);
    }, PARENT_TIMEOUT_MS);
    const handleMessage = (event: MessageEvent<RuntimeMessage>) => {
      if (
        event.source !== targetWindow
        || event.data?.channel !== 'autoprism-custom-runtime-v1'
        || event.data.requestId !== requestId
      ) return;
      window.clearTimeout(timeout);
      if (!event.data.ok) {
        setError(event.data.error || '组件运行失败');
        setTree(undefined);
        return;
      }
      setError('');
      setTree(event.data.tree ?? null);
    };
    window.addEventListener('message', handleMessage);
    targetWindow.postMessage({
      channel: 'autoprism-custom-runtime-v1',
      requestId,
      compiled,
      props: {
        data: panel.data,
        panel: { key: panel.key, title: panel.title, description: panel.description },
        evidence: panel.evidence.map((item) => ({
          source_url: item.source_url,
          artifact_sha256: item.artifact_sha256,
          retrieved_at: item.retrieved_at,
        })),
      },
    }, '*');
    return () => {
      window.clearTimeout(timeout);
      window.removeEventListener('message', handleMessage);
    };
  }, [compiled, frameReady, panel]);

  return (
    <section className="custom-runtime-shell" aria-label="隔离自定义组件">
      <iframe
        ref={frameRef}
        className="custom-runtime-sandbox"
        sandbox="allow-scripts"
        srcDoc={SANDBOX_DOCUMENT}
        title={`${panel.title} 隔离运行时`}
        onLoad={() => setFrameReady(true)}
      />
      <header>
        <span><ShieldCheck size={14} /> ISOLATED CUSTOM RUNTIME</span>
        <Status tone={error ? 'danger' : tree !== undefined ? 'ok' : 'neutral'}>
          {error ? 'BLOCKED' : tree !== undefined ? 'READY' : 'CHECKING'}
        </Status>
      </header>
      <div className="custom-runtime-input-state">
        <Status tone={panel.data_state === 'unverified' ? 'warning' : 'neutral'}>
          {inputLabel}
        </Status>
        <span>自定义组件仅负责展示，不能提升数据可信状态。</span>
      </div>
      {error ? (
        <div className="custom-runtime-error">{error}</div>
      ) : tree === undefined ? (
        <div className="custom-runtime-loading"><Box size={16} /> 校验哈希并启动隔离组件…</div>
      ) : tree === null ? (
        <div className="panel-empty">组件返回空内容；系统不会补充演示值。</div>
      ) : (
        <div className="custom-runtime-output"><RuntimeTree node={tree} /></div>
      )}
      <footer>PRESENTATION ONLY · OPAQUE ORIGIN · NO NETWORK · NO IMPORTS · 250 MS</footer>
    </section>
  );
}
