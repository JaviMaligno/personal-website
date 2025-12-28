export interface DiagramLegendItem {
  key: 'agent' | 'process' | 'review';
  color: string;
  borderColor: string;
}

export interface DiagramConfig {
  projectKey: string;
  getMermaidCode: (translations: {
    phases: Record<string, string>;
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

// DevOps Agent (Meridian) diagram
const devopsAgentDiagram: DiagramConfig = {
  projectKey: 'devopsAgent',
  getMermaidCode: (t) => `%%{init: {'theme': 'dark', 'themeVariables': { 'fontFamily': 'Inter', 'secondaryColor': '#1e293b', 'primaryColor': '#3b82f6', 'primaryBorderColor': '#60a5fa' }}}%%
graph TB
    subgraph Discovery ["${t.phases.discovery}"]
        A["${t.nodes.taskSources}<br/>(GitHub/Jira/Linear)"] --> B["${t.nodes.parallelRunner}"]
    end

    subgraph Execution ["${t.phases.execution}"]
        B --> C1["${t.nodes.agent} 1"]
        B --> C2["${t.nodes.agent} 2"]
        B --> C3["${t.nodes.agent} 3"]
        C1 --> W1["${t.nodes.worktree}"]
        C2 --> W2["${t.nodes.worktree}"]
        C3 --> W3["${t.nodes.worktree}"]
        W1 --> PR1["${t.nodes.pr} 1"]
        W2 --> PR2["${t.nodes.pr} 2"]
        W3 --> PR3["${t.nodes.pr} 3"]
    end

    subgraph Feedback ["${t.phases.feedback}"]
        PR1 --> D["${t.nodes.streamMonitor}"]
        PR2 --> D
        PR3 --> D
        D --> E["${t.nodes.sessionResume}"]
        E --> F["${t.nodes.prReview}"]
        F --> G["${t.nodes.autoMerge}"]
    end

    classDef default fill:#0f172a,stroke:#334155,color:#fff,stroke-width:1px;
    classDef agent fill:#0f172a,stroke:#3b82f6,color:#fff;
    classDef process fill:#0f172a,stroke:#334155,color:#fff;

    class C1,C2,C3,F agent;
    class B,D,E,G process;`,
  legend: [
    { key: 'agent', color: '#0f172a', borderColor: '#3b82f6' },
    { key: 'process', color: '#0f172a', borderColor: '#334155' }
  ]
};

// Industry Classifier diagram
const complianceClassifierDiagram: DiagramConfig = {
  projectKey: 'complianceClassifier',
  getMermaidCode: (t) => `%%{init: {'theme': 'dark', 'themeVariables': { 'fontFamily': 'Inter', 'secondaryColor': '#1e293b', 'primaryColor': '#3b82f6', 'primaryBorderColor': '#60a5fa' }}}%%
graph TB
    subgraph Input ["${t.phases.input}"]
        A["Company Data"]
    end

    subgraph Processing ["${t.phases.processing}"]
        A --> B["${t.nodes.webSearch}"]
        A --> C["${t.nodes.registry}"]
        B --> D["${t.nodes.grounding}"]
        C --> D
        D --> E["${t.nodes.llmClassify}"]
        E --> F["${t.nodes.riskAssess}"]
    end

    subgraph Output ["${t.phases.output}"]
        F --> G["${t.nodes.result}<br/>+ Risk Level"]
    end

    classDef default fill:#0f172a,stroke:#334155,color:#fff,stroke-width:1px;
    classDef agent fill:#0f172a,stroke:#3b82f6,color:#fff;
    classDef process fill:#0f172a,stroke:#334155,color:#fff;

    class E,F agent;
    class B,C,D process;`,
  legend: [
    { key: 'agent', color: '#0f172a', borderColor: '#3b82f6' },
    { key: 'process', color: '#0f172a', borderColor: '#334155' }
  ]
};

// Medical Doc Parser diagram
const medicalDocParserDiagram: DiagramConfig = {
  projectKey: 'medicalDocParser',
  getMermaidCode: (t) => `%%{init: {'theme': 'dark', 'themeVariables': { 'fontFamily': 'Inter', 'secondaryColor': '#1e293b', 'primaryColor': '#3b82f6', 'primaryBorderColor': '#60a5fa' }}}%%
graph TB
    subgraph Input ["${t.phases.input}"]
        A["Medical Document<br/>(PDF/scan)"]
    end

    subgraph Processing ["${t.phases.processing}"]
        A --> B["${t.nodes.ocr}<br/>>95% accuracy"]
        B --> C["${t.nodes.docClass}"]
        C --> D["${t.nodes.diagnosis}<br/>(NLP multilingual)"]
        D --> E["${t.nodes.icd10}<br/>>90% accuracy"]
        E --> F["${t.nodes.anonymize}<br/>100% verified"]
    end

    subgraph Output ["${t.phases.output}"]
        F --> G["Structured Data<br/>+ ICD-10 Codes"]
    end

    classDef default fill:#0f172a,stroke:#334155,color:#fff,stroke-width:1px;
    classDef agent fill:#0f172a,stroke:#3b82f6,color:#fff;
    classDef process fill:#0f172a,stroke:#334155,color:#fff;

    class D,E agent;
    class B,C,F process;`,
  legend: [
    { key: 'agent', color: '#0f172a', borderColor: '#3b82f6' },
    { key: 'process', color: '#0f172a', borderColor: '#334155' }
  ]
};

// MCP Server diagram (generic for all MCP projects)
const mcpServerDiagram: DiagramConfig = {
  projectKey: 'mcpServer',
  getMermaidCode: (t) => `%%{init: {'theme': 'dark', 'themeVariables': { 'fontFamily': 'Inter', 'secondaryColor': '#1e293b', 'primaryColor': '#3b82f6', 'primaryBorderColor': '#60a5fa' }}}%%
graph LR
    subgraph Client ["Client"]
        A["${t.nodes.llm}<br/>(Claude/GPT)"]
    end

    subgraph Protocol ["MCP Protocol"]
        A <-->|"JSON-RPC"| B["${t.nodes.mcpServer}"]
    end

    subgraph Backend ["Backend"]
        B <--> C["${t.nodes.api}"]
        B --> D["${t.nodes.tools}"]
    end

    classDef default fill:#0f172a,stroke:#334155,color:#fff,stroke-width:1px;
    classDef agent fill:#0f172a,stroke:#3b82f6,color:#fff;
    classDef process fill:#0f172a,stroke:#334155,color:#fff;

    class A agent;
    class B,C,D process;`,
  legend: [
    { key: 'agent', color: '#0f172a', borderColor: '#3b82f6' },
    { key: 'process', color: '#0f172a', borderColor: '#334155' }
  ]
};

// Registry of all diagrams
export const diagrams: Record<string, DiagramConfig> = {
  dataSourceAutomator: dataSourceAutomatorDiagram,
  devopsAgent: devopsAgentDiagram,
  complianceClassifier: complianceClassifierDiagram,
  medicalDocParser: medicalDocParserDiagram,
  mcpBitbucket: { ...mcpServerDiagram, projectKey: 'mcpBitbucket' },
  mcpPostgres: { ...mcpServerDiagram, projectKey: 'mcpPostgres' },
  mcpLangfuse: { ...mcpServerDiagram, projectKey: 'mcpLangfuse' }
};

export function getDiagram(projectKey: string): DiagramConfig | undefined {
  return diagrams[projectKey];
}

export function hasDiagram(projectKey: string): boolean {
  return projectKey in diagrams;
}
