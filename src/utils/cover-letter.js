import { existsSync, mkdirSync, writeFileSync } from 'fs';
import { join } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';
import { marked } from 'marked';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT_DIR = join(__dirname, '..', '..');

/**
 * Cover letter generator.
 * Creates personalized cover letters from templates using resume data and job details.
 */
export class CoverLetterGenerator {
  constructor() {
    this.outputDir = join(ROOT_DIR, 'cover-letters');
    if (!existsSync(this.outputDir)) {
      mkdirSync(this.outputDir, { recursive: true });
    }
  }

  /**
   * Generate a cover letter for a specific job.
   * @param {object} options
   * @param {object} options.job - Job details (title, company, description, requirements)
   * @param {object} options.profile - User profile from config/profile.yaml
   * @param {object} options.resume - Resume data from resume/resume.json
   * @param {string} options.tone - Tone: professional, casual, technical
   * @returns {string} Path to the generated cover letter file
   */
  async generate({ job, profile, resume, tone = 'professional' }) {
    const content = this.buildFromTemplate({ job, profile, resume, tone });
    const filename = this.generateFilename(job);
    const filepath = join(this.outputDir, filename);

    writeFileSync(filepath, content, 'utf-8');
    return filepath;
  }

  /**
   * Build a cover letter from template.
   */
  buildFromTemplate({ job, profile, resume, tone }) {
    const name = profile.personal?.name || resume.basics?.name || 'Applicant';
    const email = profile.personal?.email || resume.basics?.email || '';
    const phone = profile.personal?.phone || resume.basics?.phone || '';
    const location = profile.personal?.location || resume.basics?.location?.city || '';
    const linkedin = profile.personal?.linkedin || '';
    const github = profile.personal?.github || '';
    const portfolio = profile.personal?.portfolio || '';

    const company = job.company || 'the company';
    const role = job.title || 'the position';
    const today = new Date().toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });

    // Pick relevant skills that match the job
    const relevantSkills = this.findRelevantSkills(job, profile, resume);
    const experience = this.summarizeExperience(resume);

    const templates = {
      professional: this.professionalTemplate,
      casual: this.casualTemplate,
      technical: this.technicalTemplate,
    };

    const templateFn = templates[tone] || templates.professional;

    return templateFn.call(this, {
      name,
      email,
      phone,
      location,
      linkedin,
      github,
      portfolio,
      company,
      role,
      today,
      relevantSkills,
      experience,
      job,
    });
  }

  /**
   * Professional tone template.
   */
  professionalTemplate({ name, email, phone, location, company, role, today, relevantSkills, experience, job }) {
    const skillsList = relevantSkills.slice(0, 5).join(', ');
    const contactLine = [email, phone, location].filter(Boolean).join(' | ');

    return `# Cover Letter

**${name}**
${contactLine}

${today}

**Re: ${role} at ${company}**

---

Dear Hiring Manager,

I am writing to express my strong interest in the ${role} position at ${company}. With my background in software engineering and hands-on experience with ${skillsList}, I am confident in my ability to make meaningful contributions to your team.

${experience ? `In my recent experience, ${experience}` : 'Throughout my career, I have developed a strong foundation in building scalable, reliable software solutions.'} I am particularly drawn to this opportunity because it aligns with my passion for building impactful technology and my expertise in the tools and frameworks your team relies on.

${relevantSkills.length > 0 ? `My technical toolkit includes ${relevantSkills.join(', ')}, which directly aligns with the requirements outlined in this role.` : 'I bring a diverse technical skill set that I am eager to apply to the challenges your team faces.'}

${job.description ? this.extractCompanyHighlight(job.description, company) : `I am excited about the mission of ${company} and the opportunity to contribute to its continued growth.`}

I would welcome the opportunity to discuss how my skills and experience align with your team's needs. Thank you for considering my application.

Sincerely,
${name}
`;
  }

  /**
   * Casual tone template.
   */
  casualTemplate({ name, email, company, role, today, relevantSkills, experience }) {
    const skillsList = relevantSkills.slice(0, 4).join(', ');

    return `# Cover Letter

**${name}** | ${email}

${today}

**Re: ${role} at ${company}**

---

Hi there!

I came across the ${role} position at ${company} and got genuinely excited. This is the kind of role I have been looking for -- one where I can put my ${skillsList} skills to work on problems that matter.

${experience ? `Most recently, ${experience}` : 'I have been building software professionally and love tackling challenging technical problems.'} I am the kind of engineer who dives deep into problems, writes clean code, and cares about the end-user experience.

What drew me to ${company} specifically is the chance to work with a team that values quality engineering. I am someone who thrives in collaborative environments and loves learning from others while sharing what I know.

I would love to chat more about how I can contribute to the team. Looking forward to hearing from you!

Best,
${name}
`;
  }

  /**
   * Technical tone template.
   */
  technicalTemplate({ name, email, github, company, role, today, relevantSkills, experience, job }) {
    const contactInfo = [email, github].filter(Boolean).join(' | ');

    return `# Cover Letter

**${name}**
${contactInfo}

${today}

**Re: ${role} at ${company}**

---

Dear Engineering Team,

I am applying for the ${role} position at ${company}. Below is a brief overview of my technical qualifications and how they map to this role.

## Technical Alignment

${relevantSkills.length > 0 ? relevantSkills.map((s) => `- **${s}**: Production experience`).join('\n') : '- Broad full-stack development experience'}

## Relevant Experience

${experience || 'Experience building and maintaining production-grade software systems, with a focus on reliability, performance, and clean architecture.'}

## Key Strengths

- **Architecture**: Designing scalable systems with clear separation of concerns
- **Code Quality**: Strong advocate for testing, code review, and documentation
- **Collaboration**: Effective communication in cross-functional teams
- **Problem Solving**: Systematic approach to debugging and optimization

${job.requirements?.length > 0 ? `## Requirements Mapping\n\n${job.requirements.slice(0, 5).map((req) => `- ${req}: **Qualified**`).join('\n')}` : ''}

I would be happy to discuss technical details, walk through my code, or complete any technical assessment. My code is available on GitHub for review.

Regards,
${name}
`;
  }

  /**
   * Find skills from the profile that are relevant to the job.
   */
  findRelevantSkills(job, profile, resume) {
    const jobText = [
      job.title || '',
      job.description || '',
      ...(job.requirements || []),
    ]
      .join(' ')
      .toLowerCase();

    const allSkills = [
      ...(profile.skills?.languages || []),
      ...(profile.skills?.frameworks || []),
      ...(profile.skills?.tools || []),
    ];

    // Also pull from resume
    if (resume.skills) {
      for (const skillGroup of resume.skills) {
        if (skillGroup.keywords) {
          allSkills.push(...skillGroup.keywords);
        }
      }
    }

    // Deduplicate
    const uniqueSkills = [...new Set(allSkills)];

    // Filter to skills mentioned in the job
    const relevant = uniqueSkills.filter((skill) => {
      const parts = skill.split(/[\/,]/).map((s) => s.trim().toLowerCase());
      return parts.some((part) => jobText.includes(part));
    });

    // If not many matches, return top skills anyway
    return relevant.length >= 3 ? relevant : uniqueSkills.slice(0, 6);
  }

  /**
   * Summarize the most relevant work experience from the resume.
   */
  summarizeExperience(resume) {
    const work = resume.work;
    if (!work || work.length === 0) return '';

    const recent = work[0];
    const parts = [];

    if (recent.position && recent.name) {
      parts.push(`as a ${recent.position} at ${recent.name}`);
    }

    if (recent.summary) {
      parts.push(recent.summary.toLowerCase());
    }

    if (recent.highlights && recent.highlights.length > 0) {
      parts.push(
        `Key accomplishments include: ${recent.highlights.slice(0, 2).join('; ')}.`
      );
    }

    return parts.join(', ');
  }

  /**
   * Extract a brief highlight about the company from the job description.
   */
  extractCompanyHighlight(description, company) {
    // Look for sentences about the company
    const sentences = description.split(/[.!]\s+/);
    const aboutCompany = sentences.find(
      (s) =>
        s.toLowerCase().includes(company.toLowerCase()) ||
        s.toLowerCase().includes('our mission') ||
        s.toLowerCase().includes('we are') ||
        s.toLowerCase().includes('our team')
    );

    if (aboutCompany) {
      return `I am particularly impressed by your team's focus: "${aboutCompany.trim()}."`;
    }

    return `I am excited about the opportunity to contribute to ${company}'s engineering efforts.`;
  }

  /**
   * Convert the markdown cover letter to HTML.
   */
  toHtml(markdown) {
    return marked(markdown);
  }

  /**
   * Generate a filename for the cover letter.
   */
  generateFilename(job) {
    const company = (job.company || 'unknown')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
    const role = (job.title || 'position')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
    const date = new Date().toISOString().split('T')[0];
    return `${date}-${company}-${role}.md`;
  }
}
