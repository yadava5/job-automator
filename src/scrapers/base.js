import { chromium } from 'playwright';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'fs';
import { join } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT_DIR = join(__dirname, '..', '..');

/**
 * Base scraper class providing common Playwright browser functionality.
 * All job board scrapers should extend this class.
 */
export class BaseScraper {
  constructor(options = {}) {
    this.boardName = options.boardName || 'unknown';
    this.headless = options.headless ?? (process.env.HEADLESS === 'true');
    this.slowMo = parseInt(process.env.SLOW_MO || '50', 10);
    this.requestDelay = parseInt(process.env.REQUEST_DELAY || '2000', 10);
    this.browser = null;
    this.context = null;
    this.page = null;
    this.requiresAuth = false;

    this.screenshotsDir = join(ROOT_DIR, 'screenshots');
    this.authStateDir = join(ROOT_DIR, 'auth-state');

    if (!existsSync(this.screenshotsDir)) {
      mkdirSync(this.screenshotsDir, { recursive: true });
    }
    if (!existsSync(this.authStateDir)) {
      mkdirSync(this.authStateDir, { recursive: true });
    }
  }

  /**
   * Launch the browser and create a new context/page.
   */
  async launch() {
    this.browser = await chromium.launch({
      headless: this.headless,
      slowMo: this.slowMo,
    });

    const storageStatePath = join(this.authStateDir, `${this.boardName}-state.json`);
    const contextOptions = {
      viewport: { width: 1280, height: 720 },
      userAgent:
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    };

    // Restore session if available
    if (existsSync(storageStatePath)) {
      try {
        const storageState = JSON.parse(readFileSync(storageStatePath, 'utf-8'));
        contextOptions.storageState = storageState;
      } catch {
        // Ignore invalid state files
      }
    }

    this.context = await this.browser.newContext(contextOptions);
    this.page = await this.context.newPage();

    // Set default timeout
    this.page.setDefaultTimeout(30000);
    this.page.setDefaultNavigationTimeout(60000);

    return this.page;
  }

  /**
   * Navigate to a URL with retry logic.
   */
  async navigate(url, options = {}) {
    const maxRetries = options.retries || 3;
    let lastError;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        await this.page.goto(url, {
          waitUntil: options.waitUntil || 'domcontentloaded',
          timeout: options.timeout || 60000,
        });
        return;
      } catch (err) {
        lastError = err;
        if (attempt < maxRetries) {
          await this.delay(2000 * attempt);
        }
      }
    }

    throw new Error(`Failed to navigate to ${url} after ${maxRetries} attempts: ${lastError.message}`);
  }

  /**
   * Extract text content from an element, returns empty string if not found.
   */
  async extractText(selector, options = {}) {
    try {
      const element = await this.page.waitForSelector(selector, {
        timeout: options.timeout || 5000,
      });
      if (element) {
        return (await element.textContent()).trim();
      }
    } catch {
      // Element not found
    }
    return '';
  }

  /**
   * Extract text content from multiple elements matching a selector.
   */
  async extractAllText(selector) {
    try {
      const elements = await this.page.$$(selector);
      const texts = [];
      for (const el of elements) {
        const text = await el.textContent();
        if (text?.trim()) {
          texts.push(text.trim());
        }
      }
      return texts;
    } catch {
      return [];
    }
  }

  /**
   * Extract job details from the current page (override in subclasses).
   */
  async extractJobDetails(url) {
    if (url) {
      await this.navigate(url);
    }

    return {
      title: '',
      company: '',
      location: '',
      salary: '',
      description: '',
      requirements: [],
      url: url || this.page.url(),
      postedDate: '',
      board: this.boardName,
    };
  }

  /**
   * Take a screenshot and save it to the screenshots directory.
   */
  async screenshot(name) {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `${this.boardName}-${name}-${timestamp}.png`;
    const filepath = join(this.screenshotsDir, filename);

    await this.page.screenshot({ path: filepath, fullPage: false });
    return filepath;
  }

  /**
   * Save the current browser storage state (cookies, localStorage).
   */
  async saveSession() {
    const storageStatePath = join(this.authStateDir, `${this.boardName}-state.json`);
    const state = await this.context.storageState();
    writeFileSync(storageStatePath, JSON.stringify(state, null, 2));
  }

  /**
   * Wait for a specified amount of time.
   */
  async delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms || this.requestDelay));
  }

  /**
   * Check if an element exists on the page.
   */
  async exists(selector, timeout = 3000) {
    try {
      await this.page.waitForSelector(selector, { timeout });
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Safely click an element if it exists.
   */
  async safeClick(selector, options = {}) {
    try {
      await this.page.waitForSelector(selector, { timeout: options.timeout || 5000 });
      await this.page.click(selector);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Fill an input field if it exists.
   */
  async safeFill(selector, value, options = {}) {
    try {
      await this.page.waitForSelector(selector, { timeout: options.timeout || 5000 });
      await this.page.fill(selector, value);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Close the browser and clean up.
   */
  async close() {
    try {
      if (this.context) {
        await this.saveSession();
      }
    } catch {
      // Ignore session save errors on close
    }

    try {
      if (this.browser) {
        await this.browser.close();
      }
    } catch {
      // Ignore close errors
    }

    this.browser = null;
    this.context = null;
    this.page = null;
  }
}
