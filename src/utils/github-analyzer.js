/**
 * GitHub profile analyzer.
 * Fetches public repo data, calculates contribution stats,
 * and generates a summary suitable for job applications.
 */
export class GitHubAnalyzer {
  constructor(username) {
    this.username = username || process.env.GITHUB_USERNAME || '';
    this.apiBase = 'https://api.github.com';
  }

  /**
   * Fetch all public repositories for the user.
   * @returns {Array} List of repository objects
   */
  async fetchRepos() {
    if (!this.username) {
      throw new Error('GitHub username not set. Set GITHUB_USERNAME in your .env file.');
    }

    const repos = [];
    let page = 1;
    const perPage = 100;

    while (true) {
      const url = `${this.apiBase}/users/${this.username}/repos?per_page=${perPage}&page=${page}&sort=updated&type=owner`;
      const response = await fetch(url, {
        headers: {
          Accept: 'application/vnd.github.v3+json',
          'User-Agent': 'job-automator',
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error(`GitHub user "${this.username}" not found.`);
        }
        throw new Error(`GitHub API error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      if (data.length === 0) break;

      repos.push(...data);
      if (data.length < perPage) break;
      page++;
    }

    return repos;
  }

  /**
   * Fetch user profile information.
   * @returns {object} GitHub user profile
   */
  async fetchProfile() {
    const url = `${this.apiBase}/users/${this.username}`;
    const response = await fetch(url, {
      headers: {
        Accept: 'application/vnd.github.v3+json',
        'User-Agent': 'job-automator',
      },
    });

    if (!response.ok) {
      throw new Error(`GitHub API error: ${response.status}`);
    }

    return response.json();
  }

  /**
   * Analyze the user's GitHub profile and repos.
   * @returns {object} Analysis results
   */
  async analyze() {
    const [profile, repos] = await Promise.all([
      this.fetchProfile(),
      this.fetchRepos(),
    ]);

    const languages = this.calculateLanguages(repos);
    const stats = this.calculateStats(repos);
    const topRepos = this.getTopRepos(repos);

    return {
      profile: {
        name: profile.name,
        bio: profile.bio,
        publicRepos: profile.public_repos,
        followers: profile.followers,
        following: profile.following,
        createdAt: profile.created_at,
        url: profile.html_url,
      },
      languages,
      stats,
      topRepos,
      summary: this.generateSummary({ profile, languages, stats, topRepos }),
    };
  }

  /**
   * Calculate language distribution across repos.
   * @returns {Array} Sorted list of [language, repoCount] pairs
   */
  calculateLanguages(repos) {
    const langCount = {};
    for (const repo of repos) {
      if (repo.language) {
        langCount[repo.language] = (langCount[repo.language] || 0) + 1;
      }
    }

    return Object.entries(langCount).sort((a, b) => b[1] - a[1]);
  }

  /**
   * Calculate aggregate stats from repos.
   */
  calculateStats(repos) {
    const totalStars = repos.reduce((sum, r) => sum + (r.stargazers_count || 0), 0);
    const totalForks = repos.reduce((sum, r) => sum + (r.forks_count || 0), 0);
    const totalSize = repos.reduce((sum, r) => sum + (r.size || 0), 0);

    const nonForked = repos.filter((r) => !r.fork);
    const forked = repos.filter((r) => r.fork);

    // Repos with descriptions (indicates documentation care)
    const withDescription = repos.filter((r) => r.description).length;

    // Repos with topics
    const withTopics = repos.filter((r) => r.topics && r.topics.length > 0).length;

    // Recent activity (repos updated in the last 90 days)
    const ninetyDaysAgo = new Date();
    ninetyDaysAgo.setDate(ninetyDaysAgo.getDate() - 90);
    const recentlyActive = repos.filter(
      (r) => new Date(r.updated_at) > ninetyDaysAgo
    ).length;

    return {
      totalRepos: repos.length,
      originalRepos: nonForked.length,
      forkedRepos: forked.length,
      totalStars,
      totalForks,
      totalSizeKb: totalSize,
      withDescription,
      withTopics,
      recentlyActive,
    };
  }

  /**
   * Get the top repos by stars.
   */
  getTopRepos(repos, limit = 5) {
    return repos
      .filter((r) => !r.fork)
      .sort((a, b) => b.stargazers_count - a.stargazers_count)
      .slice(0, limit)
      .map((r) => ({
        name: r.name,
        description: r.description,
        language: r.language,
        stars: r.stargazers_count,
        forks: r.forks_count,
        url: r.html_url,
        updatedAt: r.updated_at,
      }));
  }

  /**
   * Generate a human-readable summary suitable for job applications.
   */
  generateSummary({ profile, languages, stats, topRepos }) {
    const lines = [];

    lines.push(`## GitHub Highlights for ${profile.name || this.username}`);
    lines.push('');

    // Overview
    lines.push(`- **${stats.originalRepos}** original repositories, **${stats.totalStars}** total stars`);
    lines.push(`- **${stats.recentlyActive}** repos actively maintained (updated in last 90 days)`);

    if (profile.followers > 0) {
      lines.push(`- **${profile.followers}** followers on GitHub`);
    }

    lines.push('');

    // Top languages
    if (languages.length > 0) {
      lines.push('### Top Languages');
      for (const [lang, count] of languages.slice(0, 6)) {
        const bar = '█'.repeat(Math.min(count, 20));
        lines.push(`- ${lang}: ${bar} (${count} repos)`);
      }
      lines.push('');
    }

    // Top repos
    if (topRepos.length > 0) {
      lines.push('### Notable Projects');
      for (const repo of topRepos) {
        const stars = repo.stars > 0 ? ` (${repo.stars} stars)` : '';
        lines.push(`- **[${repo.name}](${repo.url})**${stars}`);
        if (repo.description) {
          lines.push(`  ${repo.description}`);
        }
        if (repo.language) {
          lines.push(`  *${repo.language}*`);
        }
      }
      lines.push('');
    }

    // Activity indicator
    const activityLevel =
      stats.recentlyActive > 10
        ? 'Very Active'
        : stats.recentlyActive > 5
          ? 'Active'
          : stats.recentlyActive > 0
            ? 'Moderately Active'
            : 'Low Activity';

    lines.push(`### Activity Level: ${activityLevel}`);
    lines.push('');

    return lines.join('\n');
  }
}
