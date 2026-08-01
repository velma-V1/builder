// Monaco wrapper used by the Repository Intelligence / Admin Dashboard templates for read-mostly
// code display. `onChange` is wired to a pending optimistic command, never applied as authoritative
// until the backend confirms it (see realtime/client.ts).
import type { JSX } from "react";
import Editor, { type OnChange } from "@monaco-editor/react";

export interface CodeEditorProps {
  language: string;
  value: string;
  readOnly?: boolean;
  onChange?: OnChange;
}

export function CodeEditor({ language, value, readOnly = true, onChange }: CodeEditorProps): JSX.Element {
  return (
    <Editor
      height="480px"
      language={language}
      value={value}
      options={{ readOnly, minimap: { enabled: false } }}
      {...(onChange ? { onChange } : {})}
    />
  );
}
