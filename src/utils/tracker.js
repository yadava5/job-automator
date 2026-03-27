import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'fs';
import { join } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT_DIR = join(__dirname, '..', '..');

const VALID_STATUSES = ['saved', 'applied', 'interview', 'offer', 'rejected', 'withdrawn'];

/**
 * Application tracker.
 * Stores and manages job application records in a local JSON file.
 */
export class ApplicationTracker {
  constructor() {
    this.dataDir = join(ROOT_DIR, 'applications');
    this.dataFile = join(this.dataDir, 'tracker.json');

    if (!existsSync(this.dataDir)) {
      mkdirSync(this.dataDir, { recursive: true });
    }

    this.data = this.load();
  }

  /**
   * Load the tracker data from disk.
   */
  load() {
    if (!existsSync(this.dataFile)) {
      return { applications: [] };
    }

    try {
      const content = readFileSync(this.dataFile, 'utf-8');
      return JSON.parse(content);
    } catch {
      return { applications: [] };
    }
  }

  /**
   * Save the tracker data to disk.
   */
  save() {
    writeFileSync(this.dataFile, JSON.stringify(this.data, null, 2), 'utf-8');
  }

  /**
   * Add a new application entry.
   * @param {object} entry
   * @param {string} entry.company - Company name
   * @param {string} entry.role - Job title/role
   * @param {string} entry.url - Job posting URL
   * @param {string} entry.status - Application status
   * @param {string} entry.notes - Additional notes
   * @param {string} entry.coverLetterPath - Path to cover letter file
   * @returns {object} The created application entry
   */
  add({ company, role, url, status = 'saved', notes = '', coverLetterPath = null }) {
    if (!VALID_STATUSES.includes(status)) {
      throw new Error(`Invalid status: ${status}. Must be one of: ${VALID_STATUSES.join(', ')}`);
    }

    const entry = {
      id: this.generateId(),
      company,
      role,
      url,
      date_applied: new Date().toISOString().split('T')[0],
      status,
      notes,
      cover_letter_path: coverLetterPath,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    this.data.applications.push(entry);
    this.save();

    return entry;
  }

  /**
   * Update an existing application by ID.
   * @param {string} id - Application ID
   * @param {object} updates - Fields to update
   * @returns {object|null} Updated entry or null if not found
   */
  update(id, updates) {
    const index = this.data.applications.findIndex((app) => app.id === id);
    if (index === -1) return null;

    if (updates.status && !VALID_STATUSES.includes(updates.status)) {
      throw new Error(`Invalid status: ${updates.status}. Must be one of: ${VALID_STATUSES.join(', ')}`);
    }

    this.data.applications[index] = {
      ...this.data.applications[index],
      ...updates,
      updated_at: new Date().toISOString(),
    };

    this.save();
    return this.data.applications[index];
  }

  /**
   * Remove an application by ID.
   */
  remove(id) {
    const before = this.data.applications.length;
    this.data.applications = this.data.applications.filter((app) => app.id !== id);
    this.save();
    return this.data.applications.length < before;
  }

  /**
   * List applications, optionally filtered by status.
   * @param {string} status - Filter by status (optional)
   * @returns {Array} List of applications
   */
  list(status) {
    let apps = [...this.data.applications];

    if (status) {
      apps = apps.filter((app) => app.status === status);
    }

    // Sort by date (most recent first)
    apps.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    return apps;
  }

  /**
   * Find an application by URL.
   */
  findByUrl(url) {
    return this.data.applications.find((app) => app.url === url) || null;
  }

  /**
   * Get aggregate statistics.
   */
  getStats() {
    const apps = this.data.applications;

    const byStatus = {};
    for (const app of apps) {
      byStatus[app.status] = (byStatus[app.status] || 0) + 1;
    }

    // Count by company
    const byCompany = {};
    for (const app of apps) {
      const company = app.company || 'Unknown';
      byCompany[company] = (byCompany[company] || 0) + 1;
    }

    const topCompanies = Object.entries(byCompany)
      .sort((a, b) => b[1] - a[1]);

    // Recent applications (sorted by date)
    const recentApplications = [...apps]
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      .slice(0, 10);

    // Applications by week
    const byWeek = {};
    for (const app of apps) {
      const date = new Date(app.date_applied);
      const weekStart = new Date(date);
      weekStart.setDate(date.getDate() - date.getDay());
      const weekKey = weekStart.toISOString().split('T')[0];
      byWeek[weekKey] = (byWeek[weekKey] || 0) + 1;
    }

    return {
      total: apps.length,
      byStatus,
      topCompanies,
      recentApplications,
      byWeek,
    };
  }

  /**
   * Export applications to CSV format.
   * @param {string} format - Export format ('csv' or 'json')
   * @returns {string} Path to the exported file
   */
  export(format = 'csv') {
    const timestamp = new Date().toISOString().split('T')[0];

    if (format === 'csv') {
      return this.exportCsv(timestamp);
    }

    return this.exportJson(timestamp);
  }

  /**
   * Export to CSV.
   */
  exportCsv(timestamp) {
    const headers = ['ID', 'Company', 'Role', 'URL', 'Date Applied', 'Status', 'Notes'];
    const rows = this.data.applications.map((app) => [
      app.id,
      this.escapeCsvField(app.company),
      this.escapeCsvField(app.role),
      app.url,
      app.date_applied,
      app.status,
      this.escapeCsvField(app.notes || ''),
    ]);

    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const filepath = join(this.dataDir, `applications-export-${timestamp}.csv`);
    writeFileSync(filepath, csv, 'utf-8');

    return filepath;
  }

  /**
   * Export to JSON.
   */
  exportJson(timestamp) {
    const filepath = join(this.dataDir, `applications-export-${timestamp}.json`);
    writeFileSync(filepath, JSON.stringify(this.data.applications, null, 2), 'utf-8');
    return filepath;
  }

  /**
   * Escape a field for CSV output.
   */
  escapeCsvField(value) {
    if (!value) return '';
    const str = String(value);
    if (str.includes(',') || str.includes('"') || str.includes('\n')) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
  }

  /**
   * Generate a short unique ID.
   */
  generateId() {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substring(2, 6);
    return `${timestamp}-${random}`;
  }
}
