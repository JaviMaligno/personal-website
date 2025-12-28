export interface Project {
  slug: string;
  key: string;
  category: 'agentPipelines' | 'mcp' | 'compliance';
  tags: string[];
  github: string | null;
  hasDiagram: boolean;
}

export const projects: Project[] = [
  {
    slug: 'devops-agent',
    key: 'devopsAgent',
    category: 'agentPipelines',
    tags: ['TypeScript', 'Multi-Agent', 'GitHub API'],
    github: 'https://github.com/JaviMaligno/oss-agent',
    hasDiagram: true
  },
  {
    slug: 'compliance-classifier',
    key: 'complianceClassifier',
    category: 'compliance',
    tags: ['Python', 'LangChain', 'Risk Assessment'],
    github: null,
    hasDiagram: true
  },
  {
    slug: 'data-source-automator',
    key: 'dataSourceAutomator',
    category: 'agentPipelines',
    tags: ['Python', 'Multi-Agent', 'HITL'],
    github: null,
    hasDiagram: true
  },
  {
    slug: 'mcp-bitbucket',
    key: 'mcpBitbucket',
    category: 'mcp',
    tags: ['TypeScript', 'Python', 'Bitbucket API'],
    github: 'https://github.com/JaviMaligno/mcp-server-bitbucket',
    hasDiagram: true
  },
  {
    slug: 'mcp-postgres',
    key: 'mcpPostgres',
    category: 'mcp',
    tags: ['Python', 'TypeScript', 'PostgreSQL'],
    github: 'https://github.com/JaviMaligno/postgres_mcp',
    hasDiagram: true
  },
  {
    slug: 'mcp-langfuse',
    key: 'mcpLangfuse',
    category: 'mcp',
    tags: ['TypeScript', 'Langfuse', 'Observability'],
    github: 'https://github.com/JaviMaligno/langfuse-mcp-server',
    hasDiagram: true
  },
  {
    slug: 'application-automator',
    key: 'applicationAutomator',
    category: 'agentPipelines',
    tags: ['Python', 'TypeScript', 'Automation'],
    github: 'https://github.com/JaviMaligno/job-hunter-api',
    hasDiagram: false
  },
  {
    slug: 'medical-doc-parser',
    key: 'medicalDocParser',
    category: 'compliance',
    tags: ['TypeScript', 'NLP', 'ICD-10'],
    github: null,
    hasDiagram: true
  }
];

export function getProjectBySlug(slug: string): Project | undefined {
  return projects.find(p => p.slug === slug);
}

export function getProjectByKey(key: string): Project | undefined {
  return projects.find(p => p.key === key);
}

export function getAllProjectSlugs(): string[] {
  return projects.map(p => p.slug);
}
