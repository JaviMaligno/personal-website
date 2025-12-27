export interface DiagramLegendItem {
  key: 'agent' | 'process' | 'review';
  color: string;
  borderColor: string;
}

export interface DiagramConfig {
  projectKey: string;
  getMermaidCode: (translations: {
    phases: { research: string; spec: string; impl: string };
    nodes: Record<string, string>;
  }) => string;
  legend: DiagramLegendItem[];
}

// Data Source Automator diagram
const dataSourceAutomatorDiagram: DiagramConfig = {
  projectKey: 'dataSourceAutomator',
  getMermaidCode: (t) => `%%{init: {'theme': 'dark', 'themeVariables': { 'fontFamily': 'Inter', 'secondaryColor': '#1e293b', 'primaryColor': '#3b82f6', 'primaryBorderColor': '#60a5fa' }}}%%
graph TB
    subgraph Research ["${t.phases.research}"]
        A["${t.nodes.supervisor}"] --> B["${t.nodes.researcher}"]
        A --> B2["${t.nodes.downloader}"]
        A --> C["${t.nodes.analyst}"]
        B --> D["${t.nodes.selector}"]
        B2 --> D
        C --> D
    end

    subgraph Spec ["${t.phases.spec}"]
        D --> E["${t.nodes.generator}"]
        E --> F["${t.nodes.writer}"]
        F --> G["${t.nodes.review}"]
    end

    subgraph Impl ["${t.phases.impl}"]
        G --> H["${t.nodes.techSpec}"]
        H --> I["${t.nodes.coder}"]
        I --> J["${t.nodes.tester}"]
        J --> K["${t.nodes.review}"]
    end

    classDef default fill:#0f172a,stroke:#334155,color:#fff,stroke-width:1px;
    classDef review fill:#3b0764,stroke:#a855f7,stroke-width:2px;
    classDef agent fill:#0f172a,stroke:#3b82f6,color:#fff;

    class G,K review;
    class A,B,B2,C,H,I,J agent;`,
  legend: [
    { key: 'agent', color: '#0f172a', borderColor: '#3b82f6' },
    { key: 'process', color: '#0f172a', borderColor: '#334155' },
    { key: 'review', color: '#3b0764', borderColor: '#a855f7' }
  ]
};

// Registry of all diagrams
export const diagrams: Record<string, DiagramConfig> = {
  dataSourceAutomator: dataSourceAutomatorDiagram
};

export function getDiagram(projectKey: string): DiagramConfig | undefined {
  return diagrams[projectKey];
}

export function hasDiagram(projectKey: string): boolean {
  return projectKey in diagrams;
}
