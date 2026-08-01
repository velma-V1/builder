// Structure-only placeholder — not installed, not run in this repository state.
// Apache ECharts wrapper. `series`/`xAxis` are backend-sourced (TanStack Query) — never invented here.
import ReactECharts from "echarts-for-react";

export interface EChartLineProps {
  xAxis: string[];
  series: Array<{ name: string; data: number[] }>;
}

export function EChartLine({ xAxis, series }: EChartLineProps): JSX.Element {
  const option = {
    xAxis: { type: "category", data: xAxis },
    yAxis: { type: "value" },
    series: series.map((s) => ({ name: s.name, type: "line", data: s.data })),
    tooltip: { trigger: "axis" },
  };
  return <ReactECharts option={option} style={{ height: 320 }} />;
}
