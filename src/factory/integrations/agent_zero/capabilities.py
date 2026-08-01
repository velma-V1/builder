"""Tool-grant discovery — unknown/ungranted tool is DENIED (fail closed).

Agent Zero may use only the tools a specific
:class:`~factory.integrations.agent_zero.models.WorkOrder` explicitly granted. There is no ambient
tool access: a tool absent from the grant set is denied, full stop, regardless of whether Agent Zero
"knows how" to use it.
"""

from __future__ import annotations

from dataclasses import dataclass

from factory.integrations.agent_zero.errors import AgentZeroError, AgentZeroErrorCode


@dataclass(frozen=True, slots=True)
class CapabilitySet:
    work_order_id: str
    granted_tools: frozenset[str]

    def supports(self, tool_name: str) -> bool:
        return tool_name in self.granted_tools


def require_tool(capabilities: CapabilitySet, tool_name: str) -> None:
    """Raise ``TOOL_DENIED`` unless ``tool_name`` was explicitly granted for this work order."""
    if not capabilities.supports(tool_name):
        raise AgentZeroError(
            AgentZeroErrorCode.TOOL_DENIED,
            f"tool {tool_name!r} not granted for work order {capabilities.work_order_id!r}",
        )
