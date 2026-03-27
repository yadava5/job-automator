import { BaseScraper } from './base.js';
import chalk from 'chalk';

/**
 * LinkedIn job scraper.
 * Handles login, job search, detail extraction, Easy Apply, and saving jobs.
 */
export class LinkedInScraper extends BaseScraper {
  constructor(options = {}) {
    super({ boardName: 'linkedin', ...options });
    this.requiresAuth = true;
    this.email = process.env.LINKEDIN_EMAIL || '';
    this.password = process.env.LINKEDIN_PASSWORD || '';
  }

  /**
   * Log in to LinkedIn using stored credentials.
   */
  async login() {
    if (!this.email || !this.password) {
      throw new Error(
        'LinkedIn credentials not set. Add LINKEDIN_EMAIL and LINKEDIN_PASSWORD to your .env file.'
      );
    }

    // Check if already logged in via saved session
    await this.navigate('https://www.linkedin.com/feed/');
    await this.delay(2000);

    const currentUrl = this.page.url();
    if (currentUrl.includes('/feed') || currentUrl.includes('/mynetwork')) {
      console.log(chalk.green('  Already logged in to LinkedIn (session restored).'));
      return;
    }

    // Navigate to login page
    await this.navigate('https://www.linkedin.com/login');
    await this.delay(1000);

    // Fill credentials
    await this.safeFill('#username', this.email);
    await this.safeFill('#password', this.password);
    await this.delay(500);

    // Click sign in
    await this.safeClick('button[type="submit"]');
    await this.delay(3000);

    // Check for CAPTCHA or security challenge
    const pageUrl = this.page.url();
    if (pageUrl.includes('challenge') || pageUrl.includes('checkpoint')) {
      console.log(chalk.yellow('\n  Security challenge detected. Please complete it in the browser.'));
      console.log(chalk.yellow('  Waiting up to 120 seconds for manual resolution...\n'));

      await this.page.waitForURL('**/feed/**', { timeout: 120000 }).catch(() => {
        throw new Error('Login failed: security challenge was not resolved in time.');
      });
    }

    // Verify login
    const loggedInUrl = this.page.url();
    if (!loggedInUrl.includes('/feed') && !loggedInUrl.includes('/mynetwork')) {
      await this.screenshot('login-failed');
      throw new Error(`Login failed. Current URL: ${loggedInUrl}`);
    }

    await this.saveSession();
    console.log(chalk.green('  Successfully logged in to LinkedIn.'));
  }

  /**
   * Search for jobs with filters.
   * @param {object} options - Search options
   * @param {string} options.query - Job title or keywords
   * @param {string} options.location - Location filter
   * @param {number} options.limit - Maximum results to return
   * @param {string} options.datePosted - Date filter: past-24h, past-week, past-month
   * @param {string} options.experienceLevel - Experience: 1=internship, 2=entry, 3=associate, 4=mid-senior
   * @returns {Array} List of job objects
   */
  async search({ query, location, limit = 20, datePosted, experienceLevel } = {}) {
    const params = new URLSearchParams();
    if (query) params.set('keywords', query);
    if (location) params.set('location', location);

    // Date posted filter
    if (datePosted) {
      const dateFilters = {
        'past-24h': 'r86400',
        'past-week': 'r604800',
        'past-month': 'r2592000',
      };
      if (dateFilters[datePosted]) {
        params.set('f_TPR', dateFilters[datePosted]);
      }
    }

    // Experience level filter
    if (experienceLevel) {
      params.set('f_E', experienceLevel);
    }

    const searchUrl = `https://www.linkedin.com/jobs/search/?${params.toString()}`;
    await this.navigate(searchUrl);
    await this.delay(2000);

    const jobs = [];
    let scrollAttempts = 0;
    const maxScrolls = Math.ceil(limit / 25); // ~25 jobs per page load

    while (jobs.length < limit && scrollAttempts < maxScrolls) {
      // Extract job cards from the current view
      const jobCards = await this.page.$$('.jobs-search-results__list-item, .job-card-container');

      for (const card of jobCards) {
        if (jobs.length >= limit) break;

        try {
          const title = await card.$eval(
            '.job-card-list__title, .job-card-container__link',
            (el) => el.textContent.trim()
          ).catch(() => '');

          const company = await card.$eval(
            '.job-card-container__primary-description, .job-card-container__company-name',
            (el) => el.textContent.trim()
          ).catch(() => '');

          const location = await card.$eval(
            '.job-card-container__metadata-item, .job-card-container__metadata-wrapper',
            (el) => el.textContent.trim()
          ).catch(() => '');

          const link = await card.$eval('a[href*="/jobs/view/"]', (el) => el.href).catch(() => '');

          const jobId = link.match(/\/jobs\/view\/(\d+)/)?.[1] || '';

          if (title && !jobs.some((j) => j.id === jobId)) {
            jobs.push({
              id: jobId,
              title,
              company,
              location,
              url: link,
              salary: '',
              description: '',
              requirements: [],
            });
          }
        } catch {
          // Skip malformed cards
        }
      }

      // Scroll to load more results
      await this.page.evaluate(() => {
        const list = document.querySelector('.jobs-search-results-list');
        if (list) list.scrollTop = list.scrollHeight;
      });
      await this.delay(2000);
      scrollAttempts++;
    }

    return jobs.slice(0, limit);
  }

  /**
   * Extract full job details from a job listing page.
   */
  async extractJobDetails(url) {
    await this.navigate(url);
    await this.delay(2000);

    const title = await this.extractText(
      '.job-details-jobs-unified-top-card__job-title, .jobs-unified-top-card__job-title'
    );

    const company = await this.extractText(
      '.job-details-jobs-unified-top-card__company-name, .jobs-unified-top-card__company-name'
    );

    const location = await this.extractText(
      '.job-details-jobs-unified-top-card__bullet, .jobs-unified-top-card__bullet'
    );

    const description = await this.extractText(
      '.jobs-description__content, .jobs-description-content__text'
    );

    // Try to extract salary
    const salary = await this.extractText(
      '.job-details-jobs-unified-top-card__job-insight span, .salary-main-rail__data-body'
    );

    // Extract requirements from description
    const requirements = await this.extractRequirements(description);

    return {
      title,
      company,
      location,
      salary,
      description,
      requirements,
      url,
      postedDate: '',
      board: 'linkedin',
    };
  }

  /**
   * Parse requirements/skills from a job description text.
   */
  extractRequirements(description) {
    if (!description) return [];

    const requirements = [];
    const lines = description.split('\n');
    let inRequirements = false;

    for (const line of lines) {
      const trimmed = line.trim();
      if (
        /requirements|qualifications|what you('ll)? need|must have|skills/i.test(trimmed)
      ) {
        inRequirements = true;
        continue;
      }

      if (inRequirements) {
        if (/responsibilities|about|benefits|perks|what we offer/i.test(trimmed)) {
          break;
        }
        // Capture bullet points
        const bullet = trimmed.replace(/^[-*+]\s*/, '').replace(/^\d+[.)]\s*/, '');
        if (bullet.length > 5 && bullet.length < 200) {
          requirements.push(bullet);
        }
      }
    }

    return requirements;
  }

  /**
   * Use LinkedIn Easy Apply for a job.
   */
  async easyApply(url, { resume, profile } = {}) {
    await this.navigate(url);
    await this.delay(2000);

    // Click Easy Apply button
    const easyApplyClicked = await this.safeClick(
      '.jobs-apply-button, button[aria-label*="Easy Apply"]'
    );

    if (!easyApplyClicked) {
      throw new Error('Easy Apply button not found. This job may not support Easy Apply.');
    }

    await this.delay(2000);

    // Handle multi-step Easy Apply modal
    let stepCount = 0;
    const maxSteps = 10;

    while (stepCount < maxSteps) {
      stepCount++;

      // Check if we are done (success/confirmation)
      const submitted = await this.exists(
        '.jpac-modal-header:has-text("submitted"), [data-test-modal-id="post-apply-modal"]',
        2000
      );
      if (submitted) {
        console.log(chalk.green('  Application submitted via Easy Apply!'));
        return true;
      }

      // Fill phone number if asked
      await this.safeFill(
        'input[name*="phone"], input[aria-label*="phone"]',
        profile?.personal?.phone || '',
        { timeout: 1000 }
      );

      // Upload resume if file input exists
      const fileInput = await this.page.$('input[type="file"]');
      if (fileInput && resume) {
        const resumePath = process.env.DEFAULT_RESUME_PATH || './resume/resume.json';
        try {
          await fileInput.setInputFiles(resumePath);
        } catch {
          // File upload may fail if path is invalid
        }
      }

      // Try to click "Next" or "Review" or "Submit" buttons
      const nextClicked = await this.safeClick(
        'button[aria-label="Continue to next step"], button[aria-label="Review your application"], button[aria-label="Submit application"]',
        { timeout: 2000 }
      );

      if (!nextClicked) {
        // Try generic next/submit buttons
        await this.safeClick('button:has-text("Next"), button:has-text("Review"), button:has-text("Submit")', {
          timeout: 2000,
        });
      }

      await this.delay(1500);
    }

    throw new Error('Easy Apply process exceeded maximum steps. Please complete manually.');
  }

  /**
   * Apply to a job (delegates to Easy Apply).
   */
  async apply(url, options = {}) {
    return this.easyApply(url, options);
  }

  /**
   * Save a job to LinkedIn's saved jobs.
   */
  async saveJob(url) {
    await this.navigate(url);
    await this.delay(2000);

    const saved = await this.safeClick(
      'button[aria-label*="Save"], button:has-text("Save")'
    );

    if (!saved) {
      throw new Error('Save button not found on this job listing.');
    }

    console.log(chalk.green('  Job saved to LinkedIn.'));
  }
}
