# Job Automator - Claude Code Instructions

## Project Overview

Job Automator is a Node.js CLI tool that uses Playwright for browser automation to help streamline job applications. It can search job boards, auto-fill applications, generate cover letters, and track application status.

## Project Structure

```
job-automator/
  config/
    profile.yaml        # User profile, skills, and job preferences
    job-boards.yaml     # Supported job board configurations
  resume/
    resume.json         # JSON Resume standard format
  src/
    index.js            # CLI entry point (commander)
    scrapers/
      base.js           # Base scraper class with Playwright setup
      linkedin.js       # LinkedIn scraper (login, search, Easy Apply)
      indeed.js         # Indeed scraper (search, extract)
    utils/
      matcher.js        # Job-to-profile matching and scoring
      cover-letter.js   # Cover letter generation (template-based)
      tracker.js        # Application tracking (JSON + CSV export)
      github-analyzer.js # GitHub profile analysis
  applications/         # Tracked applications (tracker.json)
  cover-letters/        # Generated cover letters (Markdown)
  screenshots/          # Browser screenshots for debugging
```

## Key Commands

```bash
# Install dependencies (also installs Playwright Chromium)
npm install

# Search for jobs across configured boards
node src/index.js search

# Apply to a specific job URL
node src/index.js apply <url>

# View application tracker
node src/index.js track

# Generate a cover letter for a job posting
node src/index.js generate-cover-letter <url>

# Analyze a job posting and show match score
node src/index.js analyze <url>

# Show application statistics dashboard
node src/index.js dashboard
```

## Environment Setup

Copy `.env.example` to `.env` and fill in credentials:
```bash
cp .env.example .env
```

Edit `config/profile.yaml` to set your personal info, skills, and preferences.

## Adding a New Job Board Scraper

1. Add the board config to `config/job-boards.yaml` with `name`, `base_url`, `search_url`, `requires_auth`, and `supported_actions`.

2. Create a new file in `src/scrapers/` (e.g., `glassdoor.js`):
   ```js
   import { BaseScraper } from './base.js';

   export class GlassdoorScraper extends BaseScraper {
     constructor(options = {}) {
       super({ boardName: 'glassdoor', ...options });
     }

     async search(query) {
       // Implement search logic
     }

     async extractJobDetails(url) {
       // Implement job detail extraction
     }
   }
   ```

3. Register the scraper in `src/index.js` by importing it and adding it to the scraper map.

4. The base class provides: `launch()`, `navigate(url)`, `screenshot(name)`, `extractText(selector)`, `close()`, and cookie/session management.

## Design Decisions

- ES modules throughout (`"type": "module"` in package.json).
- Playwright is used in headed mode by default for debugging; pass `--headless` for CI.
- Application data is stored locally in JSON (no database dependency).
- Cover letters are generated from templates with placeholder substitution; optional OpenAI integration for AI-generated letters.
- The matcher scores jobs 0-100 based on skill overlap, location match, and salary range.

## Testing

Run Playwright tests:
```bash
npx playwright test
```

## Common Issues

- If Playwright browsers are not installed, run `npx playwright install chromium`.
- LinkedIn may require CAPTCHA solving -- the tool will pause and prompt when detected.
- Rate limiting: the scrapers include delays between requests to avoid blocks.
