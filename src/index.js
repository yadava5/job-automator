#!/usr/bin/env node

import { Command } from 'commander';
import chalk from 'chalk';
import inquirer from 'inquirer';
import dotenv from 'dotenv';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import YAML from 'yaml';

import { LinkedInScraper } from './scrapers/linkedin.js';
import { IndeedScraper } from './scrapers/indeed.js';
import { JobMatcher } from './utils/matcher.js';
import { CoverLetterGenerator } from './utils/cover-letter.js';
import { ApplicationTracker } from './utils/tracker.js';
import { GitHubAnalyzer } from './utils/github-analyzer.js';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT_DIR = join(__dirname, '..');

// Load configuration files
function loadProfile() {
  const profilePath = join(ROOT_DIR, 'config', 'profile.yaml');
  const content = readFileSync(profilePath, 'utf-8');
  return YAML.parse(content);
}

function loadJobBoards() {
  const boardsPath = join(ROOT_DIR, 'config', 'job-boards.yaml');
  const content = readFileSync(boardsPath, 'utf-8');
  return YAML.parse(content);
}

function loadResume() {
  const resumePath = process.env.DEFAULT_RESUME_PATH
    ? join(ROOT_DIR, process.env.DEFAULT_RESUME_PATH)
    : join(ROOT_DIR, 'resume', 'resume.json');
  const content = readFileSync(resumePath, 'utf-8');
  return JSON.parse(content);
}

// Scraper registry
const SCRAPERS = {
  linkedin: LinkedInScraper,
  indeed: IndeedScraper,
};

function getScraperForUrl(url) {
  if (url.includes('linkedin.com')) return new LinkedInScraper();
  if (url.includes('indeed.com')) return new IndeedScraper();
  if (url.includes('greenhouse.io')) return null; // TODO: implement
  if (url.includes('lever.co')) return null; // TODO: implement
  return null;
}

// CLI Setup
const program = new Command();

program
  .name('job-automator')
  .description('Automate job applications using browser automation')
  .version('1.0.0');

// ── search command ──────────────────────────────────────────────────────────

program
  .command('search')
  .description('Search for jobs across configured boards')
  .option('-b, --board <board>', 'Job board to search (linkedin, indeed)', 'all')
  .option('-q, --query <query>', 'Job title or keywords')
  .option('-l, --location <location>', 'Job location')
  .option('--headless', 'Run browser in headless mode')
  .option('--limit <number>', 'Max number of results', '20')
  .action(async (options) => {
    const profile = loadProfile();
    const boards = loadJobBoards();

    let query = options.query;
    let location = options.location;

    if (!query || !location) {
      const answers = await inquirer.prompt([
        {
          type: 'input',
          name: 'query',
          message: 'Job title or keywords:',
          default: profile.preferences.roles[0],
          when: !query,
        },
        {
          type: 'input',
          name: 'location',
          message: 'Location:',
          default: profile.preferences.locations[0],
          when: !location,
        },
      ]);
      query = query || answers.query;
      location = location || answers.location;
    }

    console.log(chalk.blue(`\nSearching for "${query}" in "${location}"...\n`));

    const boardsToSearch = options.board === 'all'
      ? Object.keys(SCRAPERS)
      : [options.board];

    const matcher = new JobMatcher(profile);
    const allResults = [];

    for (const boardName of boardsToSearch) {
      const ScraperClass = SCRAPERS[boardName];
      if (!ScraperClass) {
        console.log(chalk.yellow(`Scraper for "${boardName}" not available, skipping.`));
        continue;
      }

      const boardConfig = boards.boards[boardName];
      if (!boardConfig) {
        console.log(chalk.yellow(`No config for "${boardName}", skipping.`));
        continue;
      }

      console.log(chalk.cyan(`Searching ${boardConfig.name}...`));
      const scraper = new ScraperClass({ headless: options.headless });

      try {
        await scraper.launch();

        if (boardConfig.requires_auth) {
          await scraper.login();
        }

        const results = await scraper.search({
          query,
          location,
          limit: parseInt(options.limit, 10),
        });

        for (const job of results) {
          job.board = boardName;
          job.matchScore = matcher.score(job);
          allResults.push(job);
        }

        console.log(chalk.green(`  Found ${results.length} jobs on ${boardConfig.name}`));
      } catch (err) {
        console.error(chalk.red(`  Error searching ${boardConfig.name}: ${err.message}`));
      } finally {
        await scraper.close();
      }
    }

    // Sort by match score
    allResults.sort((a, b) => b.matchScore - a.matchScore);

    console.log(chalk.bold(`\n${'='.repeat(60)}`));
    console.log(chalk.bold(`  Found ${allResults.length} jobs total`));
    console.log(chalk.bold(`${'='.repeat(60)}\n`));

    for (const job of allResults) {
      const scoreColor = job.matchScore >= 70
        ? chalk.green
        : job.matchScore >= 40
          ? chalk.yellow
          : chalk.red;

      console.log(
        `${scoreColor(`[${job.matchScore}%]`)} ${chalk.bold(job.title)} at ${chalk.cyan(job.company)}`
      );
      console.log(`  ${chalk.dim(job.location || 'Location not specified')} | ${chalk.dim(job.board)}`);
      if (job.salary) console.log(`  ${chalk.green(job.salary)}`);
      if (job.url) console.log(`  ${chalk.dim(job.url)}`);
      console.log();
    }
  });

// ── apply command ───────────────────────────────────────────────────────────

program
  .command('apply')
  .description('Apply to a specific job by URL')
  .argument('<url>', 'Job posting URL')
  .option('--headless', 'Run browser in headless mode')
  .option('--cover-letter', 'Generate and attach a cover letter')
  .action(async (url, options) => {
    console.log(chalk.blue(`\nPreparing to apply: ${url}\n`));

    const scraper = getScraperForUrl(url);
    if (!scraper) {
      console.error(chalk.red('No scraper available for this URL. Supported: LinkedIn, Indeed.'));
      process.exit(1);
    }

    const profile = loadProfile();
    const resume = loadResume();
    const tracker = new ApplicationTracker();

    try {
      await scraper.launch();
      await scraper.login();

      const jobDetails = await scraper.extractJobDetails(url);
      console.log(chalk.bold(`  Title:   ${jobDetails.title}`));
      console.log(chalk.bold(`  Company: ${jobDetails.company}`));

      const matcher = new JobMatcher(profile);
      const matchResult = matcher.scoreDetailed(jobDetails);

      console.log(chalk.bold(`  Match:   ${matchResult.score}%`));
      if (matchResult.matchingSkills.length > 0) {
        console.log(chalk.green(`  Matching: ${matchResult.matchingSkills.join(', ')}`));
      }
      if (matchResult.missingSkills.length > 0) {
        console.log(chalk.yellow(`  Missing:  ${matchResult.missingSkills.join(', ')}`));
      }

      const { confirm } = await inquirer.prompt([
        {
          type: 'confirm',
          name: 'confirm',
          message: 'Proceed with application?',
          default: true,
        },
      ]);

      if (!confirm) {
        console.log(chalk.dim('Application cancelled.'));
        return;
      }

      let coverLetterPath = null;
      if (options.coverLetter) {
        const generator = new CoverLetterGenerator();
        coverLetterPath = await generator.generate({
          job: jobDetails,
          profile,
          resume,
          tone: 'professional',
        });
        console.log(chalk.green(`  Cover letter saved: ${coverLetterPath}`));
      }

      await scraper.apply(url, { resume, profile });

      tracker.add({
        company: jobDetails.company,
        role: jobDetails.title,
        url,
        status: 'applied',
        coverLetterPath,
        notes: `Match score: ${matchResult.score}%`,
      });

      console.log(chalk.green('\nApplication submitted successfully!'));
      await scraper.screenshot('application-confirmation');
    } catch (err) {
      console.error(chalk.red(`\nApplication failed: ${err.message}`));
      tracker.add({
        company: 'Unknown',
        role: 'Unknown',
        url,
        status: 'saved',
        notes: `Failed to apply: ${err.message}`,
      });
    } finally {
      await scraper.close();
    }
  });

// ── track command ───────────────────────────────────────────────────────────

program
  .command('track')
  .description('View and manage application tracker')
  .option('--status <status>', 'Filter by status (saved, applied, interview, offer, rejected, withdrawn)')
  .option('--export <format>', 'Export to format (csv, json)')
  .action(async (options) => {
    const tracker = new ApplicationTracker();
    const applications = tracker.list(options.status);

    if (options.export) {
      const outputPath = tracker.export(options.export);
      console.log(chalk.green(`Exported to: ${outputPath}`));
      return;
    }

    if (applications.length === 0) {
      console.log(chalk.dim('\nNo applications tracked yet.\n'));
      return;
    }

    console.log(chalk.bold(`\n${'='.repeat(60)}`));
    console.log(chalk.bold(`  Application Tracker (${applications.length} total)`));
    console.log(chalk.bold(`${'='.repeat(60)}\n`));

    const statusColors = {
      saved: chalk.dim,
      applied: chalk.blue,
      interview: chalk.cyan,
      offer: chalk.green,
      rejected: chalk.red,
      withdrawn: chalk.yellow,
    };

    for (const app of applications) {
      const colorFn = statusColors[app.status] || chalk.white;
      console.log(
        `${colorFn(`[${app.status.toUpperCase()}]`)} ${chalk.bold(app.role)} at ${chalk.cyan(app.company)}`
      );
      console.log(`  Applied: ${app.date_applied} | ${chalk.dim(app.url)}`);
      if (app.notes) console.log(`  Notes: ${app.notes}`);
      console.log();
    }
  });

// ── generate-cover-letter command ───────────────────────────────────────────

program
  .command('generate-cover-letter')
  .description('Generate a cover letter for a job posting')
  .argument('<url>', 'Job posting URL')
  .option('-t, --tone <tone>', 'Tone: professional, casual, technical', 'professional')
  .option('--headless', 'Run browser in headless mode')
  .action(async (url, options) => {
    console.log(chalk.blue(`\nFetching job details from: ${url}\n`));

    const scraper = getScraperForUrl(url);
    if (!scraper) {
      console.error(chalk.red('No scraper available for this URL.'));
      process.exit(1);
    }

    const profile = loadProfile();
    const resume = loadResume();

    try {
      await scraper.launch();

      if (scraper.requiresAuth) {
        await scraper.login();
      }

      const jobDetails = await scraper.extractJobDetails(url);

      console.log(chalk.bold(`  Title:   ${jobDetails.title}`));
      console.log(chalk.bold(`  Company: ${jobDetails.company}\n`));

      const generator = new CoverLetterGenerator();
      const outputPath = await generator.generate({
        job: jobDetails,
        profile,
        resume,
        tone: options.tone,
      });

      console.log(chalk.green(`\nCover letter saved to: ${outputPath}`));
    } catch (err) {
      console.error(chalk.red(`Error: ${err.message}`));
    } finally {
      await scraper.close();
    }
  });

// ── analyze command ─────────────────────────────────────────────────────────

program
  .command('analyze')
  .description('Analyze a job posting and show match score')
  .argument('<url>', 'Job posting URL')
  .option('--headless', 'Run browser in headless mode')
  .action(async (url, options) => {
    console.log(chalk.blue(`\nAnalyzing job posting: ${url}\n`));

    const scraper = getScraperForUrl(url);
    if (!scraper) {
      console.error(chalk.red('No scraper available for this URL.'));
      process.exit(1);
    }

    const profile = loadProfile();

    try {
      await scraper.launch();

      if (scraper.requiresAuth) {
        await scraper.login();
      }

      const jobDetails = await scraper.extractJobDetails(url);
      const matcher = new JobMatcher(profile);
      const result = matcher.scoreDetailed(jobDetails);

      console.log(chalk.bold(`${'='.repeat(60)}`));
      console.log(chalk.bold(`  Job Analysis`));
      console.log(chalk.bold(`${'='.repeat(60)}\n`));

      console.log(`  ${chalk.bold('Title:')}    ${jobDetails.title}`);
      console.log(`  ${chalk.bold('Company:')}  ${jobDetails.company}`);
      console.log(`  ${chalk.bold('Location:')} ${jobDetails.location || 'Not specified'}`);
      if (jobDetails.salary) {
        console.log(`  ${chalk.bold('Salary:')}   ${jobDetails.salary}`);
      }

      console.log();

      const scoreColor = result.score >= 70
        ? chalk.green.bold
        : result.score >= 40
          ? chalk.yellow.bold
          : chalk.red.bold;

      console.log(`  ${chalk.bold('Match Score:')} ${scoreColor(`${result.score}%`)}`);
      console.log();

      if (result.matchingSkills.length > 0) {
        console.log(chalk.green('  Matching Skills:'));
        for (const skill of result.matchingSkills) {
          console.log(chalk.green(`    + ${skill}`));
        }
      }

      if (result.missingSkills.length > 0) {
        console.log(chalk.yellow('\n  Missing Skills:'));
        for (const skill of result.missingSkills) {
          console.log(chalk.yellow(`    - ${skill}`));
        }
      }

      console.log(chalk.bold(`\n  Breakdown:`));
      console.log(`    Skill Match:    ${result.breakdown.skillMatch}%`);
      console.log(`    Location Match: ${result.breakdown.locationMatch ? 'Yes' : 'No'}`);
      console.log(`    Salary Match:   ${result.breakdown.salaryMatch ? 'Yes' : 'N/A'}`);
      console.log(`    Role Match:     ${result.breakdown.roleMatch ? 'Yes' : 'No'}`);

      if (jobDetails.description) {
        console.log(chalk.bold('\n  Description Preview:'));
        const preview = jobDetails.description.substring(0, 300);
        console.log(`    ${chalk.dim(preview)}${jobDetails.description.length > 300 ? '...' : ''}`);
      }

      console.log();
    } catch (err) {
      console.error(chalk.red(`Error: ${err.message}`));
    } finally {
      await scraper.close();
    }
  });

// ── dashboard command ───────────────────────────────────────────────────────

program
  .command('dashboard')
  .description('Show application statistics dashboard')
  .action(async () => {
    const tracker = new ApplicationTracker();
    const stats = tracker.getStats();

    console.log(chalk.bold(`\n${'='.repeat(60)}`));
    console.log(chalk.bold(`  Application Dashboard`));
    console.log(chalk.bold(`${'='.repeat(60)}\n`));

    console.log(`  ${chalk.bold('Total Applications:')} ${stats.total}`);
    console.log();

    console.log(chalk.bold('  Status Breakdown:'));
    console.log(`    ${chalk.dim('Saved:     ')} ${stats.byStatus.saved || 0}`);
    console.log(`    ${chalk.blue('Applied:   ')} ${stats.byStatus.applied || 0}`);
    console.log(`    ${chalk.cyan('Interview: ')} ${stats.byStatus.interview || 0}`);
    console.log(`    ${chalk.green('Offer:     ')} ${stats.byStatus.offer || 0}`);
    console.log(`    ${chalk.red('Rejected:  ')} ${stats.byStatus.rejected || 0}`);
    console.log(`    ${chalk.yellow('Withdrawn: ')} ${stats.byStatus.withdrawn || 0}`);
    console.log();

    if (stats.total > 0) {
      const responseRate = stats.byStatus.interview
        ? Math.round(((stats.byStatus.interview + (stats.byStatus.offer || 0)) / stats.total) * 100)
        : 0;
      console.log(`  ${chalk.bold('Response Rate:')} ${responseRate}%`);
    }

    if (stats.recentApplications.length > 0) {
      console.log(chalk.bold('\n  Recent Applications:'));
      for (const app of stats.recentApplications.slice(0, 5)) {
        const statusColors = {
          saved: chalk.dim,
          applied: chalk.blue,
          interview: chalk.cyan,
          offer: chalk.green,
          rejected: chalk.red,
          withdrawn: chalk.yellow,
        };
        const colorFn = statusColors[app.status] || chalk.white;
        console.log(
          `    ${colorFn(`[${app.status}]`)} ${app.role} at ${app.company} (${app.date_applied})`
        );
      }
    }

    if (stats.topCompanies.length > 0) {
      console.log(chalk.bold('\n  Top Companies Applied To:'));
      for (const [company, count] of stats.topCompanies.slice(0, 5)) {
        console.log(`    ${company}: ${count} application(s)`);
      }
    }

    console.log();
  });

program.parse();
