export interface Project {
  slug: string;
  key: string;
  category: 'automation' | 'assistants' | 'mcp' | 'domainSystems';
  tags: string[];
  github: string | null;
  hasDiagram: boolean;
  featured?: boolean;
}

export const projects: Project[] = [
  // AI Automation
  {
    slug: 'devops-agent',
    key: 'devopsAgent',
    category: 'automation',
    tags: ['TypeScript', 'Multi-Agent', 'GitHub API'],
    github: 'https://github.com/JaviMaligno/oss-agent',
    hasDiagram: true
  },
  {
    slug: 'data-source-automator',
    key: 'dataSourceAutomator',
    category: 'automation',
    tags: ['Python', 'Multi-Agent', 'HITL'],
    github: null,
    hasDiagram: true,
    featured: true
  },
  {
    slug: 'application-automator',
    key: 'applicationAutomator',
    category: 'automation',
    tags: ['Python', 'TypeScript', 'Automation'],
    github: 'https://github.com/JaviMaligno/job-hunter-api',
    hasDiagram: false
  },
  // AI Assistants
  {
    slug: 'devops-slack-bot',
    key: 'devopsSlackBot',
    category: 'assistants',
    tags: ['Python', 'Azure OpenAI', 'Slack', 'Kubernetes'],
    github: null,
    hasDiagram: false,
    featured: true
  },
  {
    slug: 'compliance-assistant',
    key: 'complianceAssistant',
    category: 'assistants',
    tags: ['TypeScript', 'Azure OpenAI', 'Next.js', 'pgvector'],
    github: null,
    hasDiagram: false
  },
  // MCP & Connectors
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
  // Domain Systems
  {
    slug: 'steel-pricing-platform',
    key: 'steelPricing',
    category: 'domainSystems',
    tags: ['Next.js', 'Python', 'Azure OpenAI', 'OCR'],
    github: null,
    hasDiagram: false
  },
  {
    slug: 'purchasing-management-platform',
    key: 'purchasingPlatform',
    category: 'domainSystems',
    tags: ['Next.js', 'TypeScript', 'Azure OpenAI', 'BOM'],
    github: null,
    hasDiagram: false
  },
  {
    slug: 'compliance-classifier',
    key: 'complianceClassifier',
    category: 'domainSystems',
    tags: ['Python', 'Web Search', 'Data Enrichment', 'Risk Assessment', 'Multi-Registry'],
    github: null,
    hasDiagram: true,
    featured: true
  },
  {
    slug: 'medical-doc-parser',
    key: 'medicalDocParser',
    category: 'domainSystems',
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

export function getFeaturedProjects(): Project[] {
  return projects.filter(p => p.featured);
}
