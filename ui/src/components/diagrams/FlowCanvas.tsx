// React Flow wrapper for the System Architecture Canvas / Repository Intelligence templates.
import type { JSX } from "react";
import ReactFlow, { Background, Controls, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";

export interface FlowCanvasProps {
  nodes: Node[];
  edges: Edge[];
}

export function FlowCanvas({ nodes, edges }: FlowCanvasProps): JSX.Element {
  return (
    <div style={{ height: 480 }}>
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
