import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { Prediction } from '../../models/betting.models';
import { interval, Subscription } from 'rxjs';
import { switchMap } from 'rxjs/operators';

interface Fixture {
  id: string;
  home_team: string;
  away_team: string;
  commence_time: string;
  home_odds?: number;
  draw_odds?: number;
  away_odds?: number;
  bookmakers?: number;
  sport?: string;
}

@Component({
  selector: 'app-predictions',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page-header">
      <div>
        <h1 class="page-title">Match Predictions</h1>
        <p class="page-subtitle">AI-powered predictions for upcoming matches</p>
      </div>
      <div class="header-actions">
        <button class="btn btn-secondary btn-sm" (click)="loadFixtures()">
          🔄 Refresh
        </button>
        <select class="form-select" [(ngModel)]="selectedSport" (change)="loadFixtures()" style="width: auto;">
          <option value="soccer_epl">Premier League</option>
          <option value="soccer_spain_la_liga">La Liga</option>
          <option value="soccer_germany_bundesliga">Bundesliga</option>
          <option value="soccer_italy_serie_a">Serie A</option>
          <option value="soccer_france_ligue_one">Ligue 1</option>
        </select>
      </div>
    </div>

    <!-- API Quota Info -->
    @if (quota) {
      <div class="quota-banner">
        <span>📊 API Requests: {{ quota.requests_used || 0 }} / {{ quota.requests_limit || 500 }}</span>
        <span class="quota-remaining">{{ quota.requests_remaining || 0 }} remaining</span>
      </div>
    }

    <div class="grid-2 gap-3">
      <!-- Upcoming Fixtures -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Upcoming Fixtures</h3>
          <span class="badge badge-info">{{ fixtures.length }} matches</span>
        </div>

        @if (loadingFixtures) {
          <div class="loading-container">
            <div class="spinner"></div>
            <p>Loading fixtures...</p>
          </div>
        } @else if (fixtures.length === 0) {
          <div class="empty-state">
            <div class="empty-icon">⚽</div>
            <p class="empty-description">No upcoming fixtures available</p>
            <button class="btn btn-primary" (click)="loadFixtures()">Load Fixtures</button>
          </div>
        } @else {
          <div class="fixtures-list">
            @for (fixture of fixtures; track fixture.id) {
              <div class="fixture-card"
                   [class.selected]="selectedFixture?.id === fixture.id"
                   (click)="selectFixture(fixture)">
                <div class="fixture-time">
                  {{ formatMatchTime(fixture.commence_time) }}
                </div>
                <div class="fixture-teams">
                  <div class="team">{{ fixture.home_team }}</div>
                  <div class="vs">vs</div>
                  <div class="team">{{ fixture.away_team }}</div>
                </div>
                <div class="fixture-odds">
                  @if (fixture.home_odds) {
                    <span class="odd">H: {{ fixture.home_odds | number:'1.2-2' }}</span>
                    <span class="odd">D: {{ fixture.draw_odds | number:'1.2-2' }}</span>
                    <span class="odd">A: {{ fixture.away_odds | number:'1.2-2' }}</span>
                  } @else {
                    <span class="no-odds">No odds available</span>
                  }
                </div>
                @if (fixture.bookmakers) {
                  <div class="bookmaker-count">{{ fixture.bookmakers }} bookmakers</div>
                }
              </div>
            }
          </div>
        }
      </div>

      <!-- Prediction Panel -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">
            @if (selectedFixture) {
              Prediction Result
            } @else {
              Manual Prediction
            }
          </h3>
          @if (selectedFixture) {
            <button class="btn btn-sm btn-secondary" (click)="clearSelection()">✕ Clear</button>
          }
        </div>

        @if (!selectedFixture) {
          <!-- Manual Entry Form -->
          <form (ngSubmit)="getPrediction()">
            <div class="form-group">
              <label class="form-label">Home Team</label>
              <input type="text" class="form-input" [(ngModel)]="homeTeam" name="homeTeam" placeholder="e.g., Arsenal" required>
            </div>
            <div class="form-group">
              <label class="form-label">Away Team</label>
              <input type="text" class="form-input" [(ngModel)]="awayTeam" name="awayTeam" placeholder="e.g., Chelsea" required>
            </div>
            <div class="form-group">
              <label class="form-label">Competition</label>
              <select class="form-select" [(ngModel)]="competition" name="competition">
                <option value="Premier League">Premier League</option>
                <option value="La Liga">La Liga</option>
                <option value="Serie A">Serie A</option>
                <option value="Bundesliga">Bundesliga</option>
                <option value="Ligue 1">Ligue 1</option>
                <option value="Champions League">Champions League</option>
              </select>
            </div>
            <div class="odds-grid">
              <div class="form-group">
                <label class="form-label">Home Odds</label>
                <input type="number" step="0.01" class="form-input" [(ngModel)]="homeOdds" name="homeOdds" placeholder="2.10">
              </div>
              <div class="form-group">
                <label class="form-label">Draw Odds</label>
                <input type="number" step="0.01" class="form-input" [(ngModel)]="drawOdds" name="drawOdds" placeholder="3.40">
              </div>
              <div class="form-group">
                <label class="form-label">Away Odds</label>
                <input type="number" step="0.01" class="form-input" [(ngModel)]="awayOdds" name="awayOdds" placeholder="3.60">
              </div>
            </div>
            <button type="submit" class="btn btn-primary btn-lg" [disabled]="loading" style="width: 100%;">
              {{ loading ? 'Analyzing...' : 'Get Prediction' }}
            </button>
          </form>
        } @else {
          <!-- Selected Fixture Prediction -->
          @if (!prediction && !loading) {
            <div class="selected-match">
              <h4>{{ selectedFixture.home_team }} vs {{ selectedFixture.away_team }}</h4>
              <p class="match-time">{{ formatMatchTime(selectedFixture.commence_time) }}</p>
              <button class="btn btn-primary btn-lg" (click)="getPredictionForFixture()" style="width: 100%;">
                Get AI Prediction
              </button>
            </div>
          } @else if (loading) {
            <div class="loading-container">
              <div class="spinner"></div>
              <p>Analyzing match...</p>
            </div>
          } @else if (prediction) {
            <div class="prediction-result">
              <div class="recommendation-box" [ngClass]="getRecommendationClass()">
                <div class="rec-label">Recommendation</div>
                <div class="rec-value">{{ prediction.recommendation }}</div>
                <div class="rec-outcome">{{ prediction.outcome }}</div>
              </div>

              <div class="prob-section">
                <h4>Win Probabilities</h4>
                <div class="prob-item">
                  <span>Home Win</span>
                  <div class="prob-bar-container">
                    <div class="prob-bar" [style.width.%]="prediction.homeProb * 100"></div>
                  </div>
                  <span class="prob-value">{{ prediction.homeProb * 100 | number:'1.1-1' }}%</span>
                </div>
                <div class="prob-item">
                  <span>Draw</span>
                  <div class="prob-bar-container">
                    <div class="prob-bar draw" [style.width.%]="prediction.drawProb * 100"></div>
                  </div>
                  <span class="prob-value">{{ prediction.drawProb * 100 | number:'1.1-1' }}%</span>
                </div>
                <div class="prob-item">
                  <span>Away Win</span>
                  <div class="prob-bar-container">
                    <div class="prob-bar away" [style.width.%]="prediction.awayProb * 100"></div>
                  </div>
                  <span class="prob-value">{{ prediction.awayProb * 100 | number:'1.1-1' }}%</span>
                </div>
              </div>

              <div class="metrics-grid">
                <div class="metric">
                  <div class="metric-value">{{ prediction.confidence * 100 | number:'1.0-0' }}%</div>
                  <div class="metric-label">Confidence</div>
                </div>
                <div class="metric">
                  <div class="metric-value" [class.text-success]="prediction.expectedValue > 0">
                    {{ prediction.expectedValue | number:'1.1-1' }}%
                  </div>
                  <div class="metric-label">Expected Value</div>
                </div>
                <div class="metric">
                  <div class="metric-value">{{ prediction.stakePercentage || 0 | number:'1.2-2' }}%</div>
                  <div class="metric-label">Suggested Stake</div>
                </div>
              </div>

              <button class="btn btn-secondary mt-3" (click)="clearPrediction()" style="width: 100%;">
                New Prediction
              </button>
            </div>
          }
        }
      </div>
    </div>
  `,
  styles: [`
    .header-actions { display: flex; gap: 1rem; align-items: center; }
    .quota-banner {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.75rem 1rem;
      background: rgba(59, 130, 246, 0.1);
      border: 1px solid var(--info);
      border-radius: var(--radius-sm);
      margin-bottom: 1.5rem;
      font-size: 0.875rem;
      .quota-remaining { font-weight: 600; color: var(--info); }
    }
    .fixtures-list { max-height: 600px; overflow-y: auto; }
    .fixture-card {
      padding: 1rem;
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      margin-bottom: 0.75rem;
      cursor: pointer;
      transition: all 0.2s;
      &:hover { border-color: var(--primary); background: var(--bg-card-hover); }
      &.selected { border-color: var(--primary); background: rgba(99, 102, 241, 0.1); }
    }
    .fixture-time { font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.5rem; }
    .fixture-teams {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-bottom: 0.75rem;
      .team { font-weight: 600; font-size: 0.9rem; }
      .vs { color: var(--text-muted); font-size: 0.75rem; }
    }
    .fixture-odds {
      display: flex;
      gap: 0.75rem;
      font-size: 0.8rem;
      .odd { padding: 0.25rem 0.5rem; background: var(--bg); border-radius: 4px; }
      .no-odds { color: var(--text-muted); font-style: italic; }
    }
    .bookmaker-count { margin-top: 0.5rem; font-size: 0.7rem; color: var(--text-muted); }
    .selected-match {
      text-align: center;
      padding: 2rem 1rem;
      h4 { font-size: 1.25rem; margin-bottom: 0.5rem; }
      .match-time { color: var(--text-muted); margin-bottom: 1.5rem; }
    }
    .odds-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
    .recommendation-box {
      text-align: center;
      padding: 1.5rem;
      border-radius: var(--radius);
      margin-bottom: 1.5rem;
      &.strong { background: rgba(16, 185, 129, 0.15); border: 1px solid var(--success); }
      &.value { background: rgba(99, 102, 241, 0.15); border: 1px solid var(--primary); }
      &.none { background: rgba(245, 158, 11, 0.15); border: 1px solid var(--warning); }
      .rec-label { font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; }
      .rec-value { font-size: 1.5rem; font-weight: 700; margin: 0.5rem 0; }
      .rec-outcome { font-size: 0.875rem; color: var(--text-muted); }
    }
    .prob-section {
      margin-bottom: 1.5rem;
      h4 { font-size: 0.875rem; margin-bottom: 1rem; color: var(--text-muted); }
      .prob-item {
        display: grid;
        grid-template-columns: 80px 1fr 50px;
        align-items: center;
        gap: 1rem;
        margin-bottom: 0.75rem;
        font-size: 0.875rem;
      }
      .prob-bar-container { height: 8px; background: var(--bg); border-radius: 4px; overflow: hidden; }
      .prob-bar {
        height: 100%;
        background: var(--success);
        border-radius: 4px;
        &.draw { background: var(--warning); }
        &.away { background: var(--danger); }
      }
      .prob-value { text-align: right; font-weight: 500; }
    }
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1rem;
      text-align: center;
      .metric {
        padding: 1rem;
        background: var(--bg);
        border-radius: var(--radius-sm);
      }
      .metric-value { font-size: 1.25rem; font-weight: 700; }
      .metric-label { font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem; }
    }
  `]
})
export class PredictionsComponent implements OnInit, OnDestroy {
  homeTeam = '';
  awayTeam = '';
  competition = 'Premier League';
  homeOdds: number | null = null;
  drawOdds: number | null = null;
  awayOdds: number | null = null;
  loading = false;
  prediction: Prediction | null = null;

  // New properties for live fixtures
  fixtures: Fixture[] = [];
  selectedFixture: Fixture | null = null;
  loadingFixtures = false;
  selectedSport = 'soccer_epl';
  quota: any = null;
  private refreshSubscription?: Subscription;

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.loadFixtures();
    this.loadQuota();

    // Auto-refresh fixtures every 5 minutes
    this.refreshSubscription = interval(300000).pipe(
      switchMap(() => this.api.getUpcomingFixtures(this.selectedSport, 7))
    ).subscribe({
      next: (data) => {
        this.fixtures = data.fixtures || [];
      }
    });
  }

  ngOnDestroy() {
    this.refreshSubscription?.unsubscribe();
  }

  loadFixtures() {
    this.loadingFixtures = true;
    this.api.getUpcomingFixtures(this.selectedSport, 7).subscribe({
      next: (data) => {
        this.fixtures = data.fixtures || [];
        this.loadingFixtures = false;
      },
      error: () => {
        this.loadingFixtures = false;
      }
    });
  }

  loadQuota() {
    this.api.getApiQuota().subscribe({
      next: (data) => {
        this.quota = data;
      },
      error: () => {}
    });
  }

  selectFixture(fixture: Fixture) {
    this.selectedFixture = fixture;
    this.prediction = null;
  }

  clearSelection() {
    this.selectedFixture = null;
    this.prediction = null;
  }

  clearPrediction() {
    this.prediction = null;
  }

  getPrediction() {
    if (!this.homeTeam || !this.awayTeam) return;

    this.loading = true;
    this.api.predictMatch(this.homeTeam, this.awayTeam, {
      homeOdds: this.homeOdds || undefined,
      drawOdds: this.drawOdds || undefined,
      awayOdds: this.awayOdds || undefined,
      competition: this.competition
    }).subscribe({
      next: pred => {
        this.prediction = pred;
        this.loading = false;
      },
      error: () => this.loading = false
    });
  }

  getPredictionForFixture() {
    if (!this.selectedFixture) return;

    this.loading = true;
    this.api.predictMatch(
      this.selectedFixture.home_team,
      this.selectedFixture.away_team,
      {
        homeOdds: this.selectedFixture.home_odds,
        drawOdds: this.selectedFixture.draw_odds,
        awayOdds: this.selectedFixture.away_odds,
        competition: this.mapSportToCompetition(this.selectedSport)
      }
    ).subscribe({
      next: pred => {
        this.prediction = pred;
        this.loading = false;
        this.loadQuota(); // Update quota after prediction
      },
      error: () => this.loading = false
    });
  }

  formatMatchTime(timeStr: string): string {
    if (!timeStr) return 'TBD';

    try {
      const date = new Date(timeStr);
      const now = new Date();
      const diffMs = date.getTime() - now.getTime();
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

      if (diffDays === 0) {
        if (diffHours === 0) {
          const diffMins = Math.floor(diffMs / (1000 * 60));
          return `In ${diffMins} minutes`;
        }
        return `Today at ${date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}`;
      } else if (diffDays === 1) {
        return `Tomorrow at ${date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}`;
      } else if (diffDays < 7) {
        return `${date.toLocaleDateString('en-US', { weekday: 'short' })} at ${date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}`;
      }

      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return timeStr;
    }
  }

  mapSportToCompetition(sport: string): string {
    const map: { [key: string]: string } = {
      'soccer_epl': 'Premier League',
      'soccer_spain_la_liga': 'La Liga',
      'soccer_germany_bundesliga': 'Bundesliga',
      'soccer_italy_serie_a': 'Serie A',
      'soccer_france_ligue_one': 'Ligue 1'
    };
    return map[sport] || 'Premier League';
  }

  getRecommendationClass(): string {
    if (!this.prediction?.recommendation) return 'none';
    if (this.prediction.recommendation.includes('Strong')) return 'strong';
    if (this.prediction.recommendation.includes('Value')) return 'value';
    return 'none';
  }
}
