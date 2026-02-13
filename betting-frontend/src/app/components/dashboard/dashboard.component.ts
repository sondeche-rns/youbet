import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../services/api.service';
import { DashboardStats, Match, RecentResult } from '../../models/betting.models';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="page-header">
      <h1 class="page-title">Dashboard</h1>
      <p class="page-subtitle">Overview of your betting performance and predictions</p>
    </div>

    <!-- Stats Grid -->
    <div class="stats-grid mb-4">
      <div class="stat-card">
        <div class="stat-value">{{ stats?.overallAccuracy | number:'1.1-1' }}%</div>
        <div class="stat-label">Accuracy</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" [class.text-success]="(stats?.roi || 0) > 0" [class.text-danger]="(stats?.roi || 0) < 0">
          {{ stats?.roi | number:'1.1-1' }}%
        </div>
        <div class="stat-label">ROI</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats?.totalPredictions }}</div>
        <div class="stat-label">Total Predictions</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats?.winStreak }}</div>
        <div class="stat-label">Win Streak</div>
      </div>
    </div>

    <div class="grid-2 gap-3">
      <!-- Upcoming Predictions -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Today's Predictions</h3>
        </div>
        @if (upcomingMatches.length === 0) {
          <div class="empty-state">
            <div class="empty-icon">🎯</div>
            <p class="empty-description">No upcoming matches</p>
          </div>
        } @else {
          @for (match of upcomingMatches; track match.id) {
            <div class="match-card" (click)="selectMatch(match)">
              <div class="match-header">
                <div class="match-teams">
                  <span class="team home">{{ match.homeTeam }}</span>
                  <span class="vs">vs</span>
                  <span class="team away">{{ match.awayTeam }}</span>
                </div>
                <div class="match-date">{{ formatDate(match.kickoff) }}</div>
              </div>
              <div class="match-prediction">
                <span class="badge" [ngClass]="getRecommendationClass(match.prediction?.recommendation)">
                  {{ match.prediction?.recommendation || 'Analyzing...' }}
                </span>
                <span class="confidence">{{ (match.prediction?.confidence || 0) * 100 | number:'1.0-0' }}% conf.</span>
              </div>
              <div class="prob-bars">
                <div class="prob-bar">
                  <div class="prob-fill home" [style.width.%]="(match.prediction?.homeProb || 0) * 100"></div>
                </div>
                <div class="prob-labels">
                  <span>H {{ (match.prediction?.homeProb || 0) * 100 | number:'1.0-0' }}%</span>
                  <span>D {{ (match.prediction?.drawProb || 0) * 100 | number:'1.0-0' }}%</span>
                  <span>A {{ (match.prediction?.awayProb || 0) * 100 | number:'1.0-0' }}%</span>
                </div>
              </div>
            </div>
          }
        }
      </div>

      <!-- Recent Results -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Recent Results</h3>
        </div>
        @if (recentResults.length === 0) {
          <div class="empty-state">
            <div class="empty-icon">📊</div>
            <p class="empty-description">No recent results</p>
          </div>
        } @else {
          <div class="results-list">
            @for (result of recentResults; track result.date + result.match) {
              <div class="result-item" [class.won]="result.won" [class.lost]="!result.won">
                <div class="result-content">
                  <div class="result-match">
                    <span class="match-name">{{ result.match }}</span>
                    <span class="result-score">{{ result.result }}</span>
                  </div>
                  <div class="result-date">{{ formatResultDate(result.date) }}</div>
                </div>
                <div class="result-meta">
                  <span class="prediction">{{ result.prediction }}</span>
                  <span class="pnl" [class.text-success]="result.pnl > 0" [class.text-danger]="result.pnl < 0">
                    {{ result.pnl > 0 ? '+' : '' }}{{ result.pnl | number:'1.2-2' }}
                  </span>
                </div>
              </div>
            }
          </div>
        }
      </div>
    </div>
  `,
  styles: [`
    .match-card {
      padding: 1rem;
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      margin-bottom: 0.75rem;
      cursor: pointer;
      transition: all 0.2s;
      &:hover { border-color: var(--primary); background: var(--bg-card-hover); }
    }
    .match-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.75rem;
      gap: 0.75rem;
    }
    .match-teams {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      flex: 1 1 auto;

      .team {
        font-weight: 600;
        font-size: 0.875rem;
        line-height: 1.2;
      }

      .vs {
        color: var(--text-muted);
        font-size: 0.75rem;
        padding: 0 0.25rem;
      }
    }
    .match-date {
      font-size: 0.75rem;
      color: var(--text-muted);
      white-space: nowrap;
      flex-shrink: 0;
    }
    .match-prediction {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.75rem;
      .confidence { font-size: 0.75rem; color: var(--text-muted); }
    }
    .prob-bars { .prob-bar { height: 6px; background: var(--bg); border-radius: 3px; overflow: hidden; }
      .prob-fill { height: 100%; background: linear-gradient(90deg, var(--primary), var(--secondary)); }
      .prob-labels { display: flex; justify-content: space-between; font-size: 0.7rem; color: var(--text-muted); margin-top: 0.25rem; }
    }
    .results-list { .result-item {
        display: flex; justify-content: space-between; align-items: center;
        padding: 0.75rem; border-radius: var(--radius-sm); margin-bottom: 0.5rem;
        border-left: 3px solid var(--border);
        &.won { border-left-color: var(--success); background: rgba(16, 185, 129, 0.05); }
        &.lost { border-left-color: var(--danger); background: rgba(239, 68, 68, 0.05); }
      }
      .result-content { flex: 1; }
      .result-match { margin-bottom: 0.25rem; }
      .match-name { font-weight: 500; font-size: 0.875rem; }
      .result-score { font-size: 0.75rem; color: var(--text-muted); margin-left: 0.5rem; }
      .result-date { font-size: 0.7rem; color: var(--text-muted); }
      .result-meta { text-align: right; .prediction { font-size: 0.75rem; color: var(--text-muted); display: block; }
        .pnl { font-weight: 600; font-size: 0.875rem; }
      }
    }
  `]
})
export class DashboardComponent implements OnInit {
  stats: DashboardStats | null = null;
  upcomingMatches: Match[] = [];
  recentResults: RecentResult[] = [];

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    this.api.getDashboardStats().subscribe(stats => this.stats = stats);
    this.api.getUpcomingMatches().subscribe(matches => {
      console.log('Raw upcoming matches data:', matches);
      console.log('First match:', matches[0]);
      this.upcomingMatches = matches;
      console.log('upcomingMatches assigned:', this.upcomingMatches);
    });
    this.api.getRecentResults().subscribe(results => this.recentResults = results);
  }

  selectMatch(match: Match) {
    console.log('Selected match:', match);
  }

  getRecommendationClass(rec?: string): string {
    if (!rec) return 'badge-info';
    if (rec.includes('Strong')) return 'badge-success';
    if (rec.includes('Value')) return 'badge-primary';
    if (rec.includes('No Bet')) return 'badge-warning';
    return 'badge-info';
  }

  formatDate(kickoff: string): string {
    if (!kickoff) return '';

    const matchDate = new Date(kickoff);
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const matchDay = new Date(matchDate.getFullYear(), matchDate.getMonth(), matchDate.getDate());

    const timeStr = matchDate.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });

    if (matchDay.getTime() === today.getTime()) {
      return `Today at ${timeStr}`;
    } else if (matchDay.getTime() === tomorrow.getTime()) {
      return `Tomorrow at ${timeStr}`;
    } else {
      const dateStr = matchDate.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric'
      });
      return `${dateStr} at ${timeStr}`;
    }
  }

  formatResultDate(dateStr: string): string {
    if (!dateStr) return '';

    const resultDate = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - resultDate.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return 'Today';
    } else if (diffDays === 1) {
      return 'Yesterday';
    } else if (diffDays < 7) {
      return `${diffDays} days ago`;
    } else {
      // Always include year for clarity
      return resultDate.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
    }
  }
}
