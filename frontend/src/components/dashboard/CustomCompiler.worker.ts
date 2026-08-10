import { transform } from '@babel/standalone';

self.onmessage = (event: MessageEvent<{ source: string }>) => {
  try {
    const result = transform(event.data.source, {
      filename: 'autoprism-panel.tsx',
      sourceType: 'module',
      presets: [
        ['typescript', { isTSX: true, allExtensions: true }],
        ['react', { runtime: 'classic' }],
      ],
      plugins: ['transform-modules-commonjs'],
      compact: true,
    });
    self.postMessage({ ok: true, code: result.code ?? null });
  } catch (reason) {
    self.postMessage({
      ok: false,
      error: reason instanceof Error ? reason.message.slice(0, 240) : 'compile failed',
    });
  }
};
