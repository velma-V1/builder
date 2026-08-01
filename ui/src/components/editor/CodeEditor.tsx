// Structure-only placeholder — not installed, not run in this repository state.
// Monaco wrapper used by the Repository Intelligence / Admin Dashboard templates for read-mostly
// code display. `onChange` is wired to a pending optimistic command, never applied as authoritative
// until the backend confirms it (see realtime/client.ts).
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
      onChange={onChange}
      options={{ readOnly, minimap: { enabled: false } }}
    />
  );
}
