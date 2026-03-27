/**
 * Job matching utility.
 * Compares job requirements against user profile skills and preferences
 * to produce a match score (0-100).
 */
export class JobMatcher {
  constructor(profile) {
    this.profile = profile;
    this.allSkills = this.buildSkillSet();
  }

  /**
   * Build a normalized set of all user skills from the profile.
   */
  buildSkillSet() {
    const skills = new Set();
    const { languages = [], frameworks = [], tools = [], certifications = [] } =
      this.profile.skills || {};

    for (const list of [languages, frameworks, tools, certifications]) {
      for (const skill of list) {
        // Normalize: lowercase, split compound entries like "JavaScript/TypeScript"
        const parts = skill.split(/[\/,]/).map((s) => s.trim().toLowerCase());
        for (const part of parts) {
          if (part) skills.add(part);
        }
      }
    }

    return skills;
  }

  /**
   * Quick score (0-100) for sorting/filtering.
   */
  score(job) {
    return this.scoreDetailed(job).score;
  }

  /**
   * Detailed scoring with breakdown.
   * @param {object} job - Job object with title, company, location, salary, description, requirements
   * @returns {object} { score, matchingSkills, missingSkills, breakdown }
   */
  scoreDetailed(job) {
    const breakdown = {
      skillMatch: 0,
      locationMatch: false,
      salaryMatch: false,
      roleMatch: false,
    };

    const matchingSkills = [];
    const missingSkills = [];

    // 1. Skill matching (60% weight)
    const jobSkills = this.extractSkillsFromJob(job);
    let skillHits = 0;

    for (const skill of jobSkills) {
      if (this.hasSkill(skill)) {
        skillHits++;
        matchingSkills.push(skill);
      } else {
        missingSkills.push(skill);
      }
    }

    breakdown.skillMatch =
      jobSkills.length > 0 ? Math.round((skillHits / jobSkills.length) * 100) : 50;

    // 2. Location matching (15% weight)
    breakdown.locationMatch = this.matchesLocation(job.location);

    // 3. Salary matching (10% weight)
    breakdown.salaryMatch = this.matchesSalary(job.salary);

    // 4. Role title matching (15% weight)
    breakdown.roleMatch = this.matchesRole(job.title);

    // Calculate composite score
    const score = Math.round(
      breakdown.skillMatch * 0.6 +
        (breakdown.locationMatch ? 100 : 0) * 0.15 +
        (breakdown.salaryMatch ? 100 : 30) * 0.1 + // Give partial credit if salary unknown
        (breakdown.roleMatch ? 100 : 0) * 0.15
    );

    return {
      score: Math.min(100, Math.max(0, score)),
      matchingSkills,
      missingSkills,
      breakdown,
    };
  }

  /**
   * Check if the user has a particular skill (fuzzy matching).
   */
  hasSkill(skill) {
    const normalized = skill.toLowerCase().trim();
    if (this.allSkills.has(normalized)) return true;

    // Fuzzy matching: check if any user skill contains the job skill or vice versa
    for (const userSkill of this.allSkills) {
      if (userSkill.includes(normalized) || normalized.includes(userSkill)) {
        return true;
      }
    }

    // Common aliases
    const aliases = {
      js: 'javascript',
      ts: 'typescript',
      py: 'python',
      'node.js': 'node',
      nodejs: 'node',
      react: 'react',
      'react.js': 'react',
      reactjs: 'react',
      postgres: 'postgresql',
      mongo: 'mongodb',
      aws: 'amazon web services',
      gcp: 'google cloud',
      k8s: 'kubernetes',
      ci: 'github actions',
      'ci/cd': 'github actions',
    };

    const alias = aliases[normalized];
    if (alias && this.allSkills.has(alias)) return true;

    // Reverse alias check
    for (const [key, value] of Object.entries(aliases)) {
      if (value === normalized && this.allSkills.has(key)) return true;
    }

    return false;
  }

  /**
   * Extract mentioned skills/technologies from a job posting.
   */
  extractSkillsFromJob(job) {
    const text = [
      job.title || '',
      job.description || '',
      ...(job.requirements || []),
    ]
      .join(' ')
      .toLowerCase();

    // Common tech keywords to look for
    const techKeywords = [
      'javascript', 'typescript', 'python', 'java', 'rust', 'go', 'golang',
      'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin', 'scala', 'elixir',
      'react', 'angular', 'vue', 'svelte', 'next.js', 'nuxt',
      'node.js', 'nodejs', 'express', 'fastify', 'nestjs', 'django', 'flask',
      'spring', 'rails', 'laravel',
      'sql', 'mysql', 'postgresql', 'postgres', 'mongodb', 'redis', 'elasticsearch',
      'dynamodb', 'cassandra', 'sqlite',
      'docker', 'kubernetes', 'k8s', 'terraform', 'ansible',
      'aws', 'azure', 'gcp', 'google cloud',
      'git', 'github', 'gitlab', 'bitbucket',
      'ci/cd', 'github actions', 'jenkins', 'circleci',
      'graphql', 'rest', 'grpc', 'websocket',
      'html', 'css', 'sass', 'tailwind',
      'linux', 'unix', 'bash',
      'agile', 'scrum',
      'machine learning', 'deep learning', 'ai', 'nlp',
      'microservices', 'serverless', 'distributed systems',
    ];

    const found = new Set();
    for (const keyword of techKeywords) {
      // Use word boundary matching
      const pattern = new RegExp(`\\b${keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i');
      if (pattern.test(text)) {
        found.add(keyword);
      }
    }

    return Array.from(found);
  }

  /**
   * Check if the job location matches user preferences.
   */
  matchesLocation(jobLocation) {
    if (!jobLocation) return false;

    const loc = jobLocation.toLowerCase();
    const preferredLocations = (this.profile.preferences?.locations || []).map((l) =>
      l.toLowerCase()
    );

    for (const preferred of preferredLocations) {
      if (loc.includes(preferred) || preferred.includes(loc)) return true;
      if (preferred === 'remote' && /remote|work from home|wfh|anywhere/i.test(loc)) return true;
      if (preferred === 'united states' && /\b(us|usa|united states)\b/i.test(loc)) return true;
    }

    return false;
  }

  /**
   * Check if the job salary falls within user preferences.
   * Returns true if salary is unknown (benefit of the doubt).
   */
  matchesSalary(salaryStr) {
    if (!salaryStr) return false; // Unknown means no match (different from N/A in scoring)

    const { min, max } = this.profile.preferences?.salary_range || {};
    if (!min && !max) return true; // No preference set

    // Extract numbers from salary string
    const numbers = salaryStr.match(/[\d,]+/g);
    if (!numbers || numbers.length === 0) return false;

    const salaryValues = numbers.map((n) => parseInt(n.replace(/,/g, ''), 10));

    // Determine if the values are hourly (typically < 500) or annual
    const isHourly = salaryValues.every((v) => v < 500);
    const annualized = isHourly
      ? salaryValues.map((v) => v * 2080) // 40hrs * 52 weeks
      : salaryValues;

    const jobMin = Math.min(...annualized);
    const jobMax = Math.max(...annualized);

    // Check overlap between ranges
    if (min && jobMax < min) return false;
    if (max && jobMin > max) return false;

    return true;
  }

  /**
   * Check if the job title matches user preferred roles.
   */
  matchesRole(title) {
    if (!title) return false;

    const normalizedTitle = title.toLowerCase();
    const preferredRoles = (this.profile.preferences?.roles || []).map((r) => r.toLowerCase());

    for (const role of preferredRoles) {
      // Check if the job title contains key words from the preferred role
      const roleWords = role.split(/\s+/);
      const matchCount = roleWords.filter((word) => normalizedTitle.includes(word)).length;
      if (matchCount >= roleWords.length * 0.5) return true;
    }

    // Check for excluded companies
    // (not directly role-related but good to check here for filtering)
    return false;
  }

  /**
   * Check if the company is in the excluded list.
   */
  isExcludedCompany(company) {
    if (!company) return false;
    const excluded = (this.profile.preferences?.excluded_companies || []).map((c) =>
      c.toLowerCase()
    );
    return excluded.some((ex) => company.toLowerCase().includes(ex));
  }

  /**
   * Filter and sort a list of jobs by match score.
   * @param {Array} jobs - List of job objects
   * @param {object} options - Filter options
   * @param {number} options.minScore - Minimum match score (0-100)
   * @returns {Array} Filtered and sorted jobs with matchScore added
   */
  filterAndSort(jobs, { minScore = 0 } = {}) {
    return jobs
      .filter((job) => !this.isExcludedCompany(job.company))
      .map((job) => ({
        ...job,
        matchScore: this.score(job),
      }))
      .filter((job) => job.matchScore >= minScore)
      .sort((a, b) => b.matchScore - a.matchScore);
  }
}
