declare module '@babel/standalone' {
  export interface TransformResult {
    code?: string | null;
  }

  export interface TransformOptions {
    filename?: string;
    sourceType?: 'module' | 'script';
    presets?: Array<string | [string, Record<string, unknown>]>;
    plugins?: string[];
    compact?: boolean;
  }

  export function transform(code: string, options: TransformOptions): TransformResult;
}
