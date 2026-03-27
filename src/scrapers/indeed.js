import { BaseScraper } from './base.js';
import chalk from 'chalk';

/**
 * Indeed job scraper.
 * Handles job search, detail extraction, and saving results.
 * Indeed does not require authentication for basic searching.
 */
export class IndeedScraper extends BaseScraper {
  constructor(options = {}) {
    super({ boardName: 'indeed', ...options });
    this.requiresAuth = false;
  }

  /**
   * Indeed does not require login for job searches.
   */
  async login() {
    // No-op: Indeed does not require authentication for searching
    console.log(chalk.dim('  Indeed does not require login for search.'));
  }

  /**
   * Search for jobs on Indeed.
   * @param {object} options - Search options
   * @param {string} options.query - Job title or keywords
   * @param {string} options.location - Location filter
   * @param {number} options.limit - Maximum results to return
   * @param {string} options.datePosted - Date filter: 1, 3, 7, 14 (days)
   * @param {string} options.jobType - fulltime, parttime, contract, temporary, internship
   * @param {string} options.salaryMin - Minimum salary filter
   * @returns {Array} List of job objects
   */
  async search({ query, location, limit = 20, datePosted, jobType, salaryMin } = {}) {
    const params = new URLSearchParams();
    if (query) params.set('q', query);
    if (location) params.set('l', location);

    // Date posted filter
    if (datePosted) {
      params.set('fromage', datePosted);
    }

    // Job type filter
    if (jobType) {
      const typeMap = {
        fulltime: 'fulltime',
        parttime: 'parttime',
        contract: 'contract',
        temporary: 'temporary',
        internship: 'internship',
      };
      if (typeMap[jobType]) {
        params.set('jt', typeMap[jobType]);
      }
    }

    // Salary filter
    if (salaryMin) {
      params.set('salary', salaryMin);
    }

    const searchUrl = `https://www.indeed.com/jobs?${params.toString()}`;
    await this.navigate(searchUrl);
    await this.delay(2000);

    const jobs = [];
    let pageNum = 0;
    const resultsPerPage = 15;
    const maxPages = Math.ceil(limit / resultsPerPage);

    while (jobs.length < limit && pageNum < maxPages) {
      // Extract job cards from the current page
      const jobCards = await this.page.$$(
        '.job_seen_beacon, .jobsearch-ResultsList > li, .resultContent'
      );

      for (const card of jobCards) {
        if (jobs.length >= limit) break;

        try {
          const title = await card.$eval(
            '.jobTitle a, h2.jobTitle span, .jcs-JobTitle span',
            (el) => el.textContent.trim()
          ).catch(() => '');

          const company = await card.$eval(
            '.companyName, [data-testid="company-name"], .company_location .companyName',
            (el) => el.textContent.trim()
          ).catch(() => '');

          const jobLocation = await card.$eval(
            '.companyLocation, [data-testid="text-location"]',
            (el) => el.textContent.trim()
          ).catch(() => '');

          const salary = await card.$eval(
            '.salary-snippet-container, .metadata.salary-snippet-container, .salaryOnly',
            (el) => el.textContent.trim()
          ).catch(() => '');

          const snippet = await card.$eval(
            '.job-snippet, .underShelfFooter .tapItem-snippet',
            (el) => el.textContent.trim()
          ).catch(() => '');

          const link = await card.$eval(
            'a[href*="/viewjob"], a[href*="/rc/clk"], h2.jobTitle a',
            (el) => el.href
          ).catch(() => '');

          const jobId = link.match(/jk=([a-f0-9]+)/)?.[1] || `indeed-${jobs.length}`;

          if (title && !jobs.some((j) => j.id === jobId)) {
            jobs.push({
              id: jobId,
              title,
              company,
              location: jobLocation,
              salary,
              description: snippet,
              requirements: [],
              url: link.startsWith('http') ? link : `https://www.indeed.com${link}`,
            });
          }
        } catch {
          // Skip malformed cards
        }
      }

      // Go to the next page if we need more results
      if (jobs.length < limit) {
        pageNum++;
        const nextPageClicked = await this.safeClick(
          'a[data-testid="pagination-page-next"], a[aria-label="Next Page"]',
          { timeout: 3000 }
        );

        if (!nextPageClicked) break;
        await this.delay(2000);
      }
    }

    return jobs.slice(0, limit);
  }

  /**
   * Extract full job details from an Indeed job listing page.
   */
  async extractJobDetails(url) {
    await this.navigate(url);
    await this.delay(2000);

    const title = await this.extractText(
      '.jobsearch-JobInfoHeader-title, h1.jobsearch-JobInfoHeader-title, [data-testid="jobsearch-JobInfoHeader-title"]'
    );

    const company = await this.extractText(
      '.jobsearch-InlineCompanyRating-companyHeader, [data-testid="inlineHeader-companyName"] a, .jobsearch-CompanyInfoContainer a'
    );

    const location = await this.extractText(
      '.jobsearch-JobInfoHeader-subtitle .jobsearch-JobInfoHeader-subtitle--location, [data-testid="job-location"], [data-testid="inlineHeader-companyLocation"]'
    );

    const salary = await this.extractText(
      '#salaryInfoAndJobType span, .jobsearch-JobMetadataHeader-item, [data-testid="attribute_snippet_testid"]'
    );

    const description = await this.extractText(
      '#jobDescriptionText, .jobsearch-jobDescriptionText'
    );

    // Extract requirements from the description
    const requirements = this.extractRequirements(description);

    return {
      title,
      company,
      location,
      salary,
      description,
      requirements,
      url,
      postedDate: '',
      board: 'indeed',
    };
  }

  /**
   * Parse requirements from job description text.
   */
  extractRequirements(description) {
    if (!description) return [];

    const requirements = [];
    const lines = description.split('\n');
    let inRequirements = false;

    for (const line of lines) {
      const trimmed = line.trim();

      if (/requirements|qualifications|what you('ll)? need|must have|skills|you have/i.test(trimmed)) {
        inRequirements = true;
        continue;
      }

      if (inRequirements) {
        if (/responsibilities|about (us|the)|benefits|perks|what we offer|nice to have/i.test(trimmed)) {
          break;
        }
        const bullet = trimmed.replace(/^[-*+]\s*/, '').replace(/^\d+[.)]\s*/, '');
        if (bullet.length > 5 && bullet.length < 200) {
          requirements.push(bullet);
        }
      }
    }

    return requirements;
  }

  /**
   * Apply to a job on Indeed (opens the application page).
   * Most Indeed applications redirect to the company's site,
   * so full automation is not possible for all listings.
   */
  async apply(url) {
    await this.navigate(url);
    await this.delay(2000);

    // Click "Apply now" button
    const applyClicked = await this.safeClick(
      '#indeedApplyButton, .jobsearch-IndeedApplyButton-newDesign, button[id*="apply"], a:has-text("Apply now")'
    );

    if (!applyClicked) {
      console.log(
        chalk.yellow('  Direct apply not available. The job may redirect to an external site.')
      );
      // Try to find external apply link
      const externalLink = await this.page.$eval(
        'a[href*="apply"], button:has-text("Apply on company site")',
        (el) => el.href || el.closest('a')?.href
      ).catch(() => null);

      if (externalLink) {
        console.log(chalk.blue(`  External application link: ${externalLink}`));
        await this.navigate(externalLink);
      } else {
        throw new Error('Apply button not found on this listing.');
      }
    }

    await this.delay(2000);
    await this.screenshot('indeed-apply');

    console.log(chalk.yellow('  Indeed application page opened. Manual completion may be required.'));
  }

  /**
   * Save search results to a local JSON file (Indeed does not have a save feature without login).
   */
  async saveResults(jobs, filename = 'indeed-results.json') {
    const { writeFileSync } = await import('fs');
    const { join } = await import('path');
    const outputPath = join(process.cwd(), 'applications', filename);
    writeFileSync(outputPath, JSON.stringify(jobs, null, 2));
    console.log(chalk.green(`  Results saved to: ${outputPath}`));
    return outputPath;
  }
}
