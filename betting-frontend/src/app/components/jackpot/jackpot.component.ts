import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';

interface JackpotData {
  provider: string;
  type: string;
  matches_count: number;
  prize_amount?: string;
  fetched_at: string;
  url: string;
  matches: JackpotMatch[];
  is_sample_data?: boolean;
}

interface JackpotMatch {
  match_number: number;
  home_team: string;
  away_team: string;
  kickoff?: string;
  competition?: string;
}

interface JackpotAnalysis {
  jackpot_id: string;
  provider: string;
  type: string;
  prize_amount?: string;
  total_matches: number;
  analyzed_at: string;
  predictions: MatchPrediction[];
  high_confidence_count: number;
  low_confidence_count: number;
  average_confidence: number;
  recommended_combinations: RecommendedCombination[];
}

interface MatchPrediction {
  match_number: number;
  home_team: string;
  away_team: string;
  prediction: string;
  confidence: number;
  home_prob: number;
  draw_prob: number;
  away_prob: number;
  recommendation: string;
}

interface RecommendedCombination {
  strategy: string;
  description: string;
  predicted_accuracy?: number;
}

interface PerformanceStats {
  total_jackpots: number;
  average_accuracy: number;
  best_accuracy: number;
  worst_accuracy: number;
  by_provider: { [key: string]: { count: number; avg_accuracy: number } };
}

@Component({
  selector: 'app-jackpot',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page-header">
      <h1 class="page-title">🎰 Jackpot Predictions</h1>
      <p class="page-subtitle">AI predictions for SportPesa & Betika jackpots (KSh 100M+)</p>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button class="tab" [class.active]="activeTab === 'fetch'" (click)="activeTab = 'fetch'">
        📡 Fetch Jackpots
      </button>
      <button class="tab" [class.active]="activeTab === 'analyze'" (click)="activeTab = 'analyze'">
        🤖 Predictions
      </button>
      <button class="tab" [class.active]="activeTab === 'results'" (click)="activeTab = 'results'">
        📝 Record Results
      </button>
      <button class="tab" [class.active]="activeTab === 'performance'" (click)="activeTab = 'performance'">
        📊 Performance
      </button>
    </div>

    <!-- Tab Content -->
    <div class="tab-content">

      <!-- Fetch Jackpots Tab -->
      @if (activeTab === 'fetch') {
        <div class="fetch-section">
          <div class="card">
            <div class="card-header">
              <h3 class="card-title">Fetch Current Jackpots</h3>
            </div>
            <div class="card-body">
              <p class="mb-3">Select betting providers to fetch current jackpots:</p>

              <div class="provider-checkboxes mb-3">
                <label class="checkbox-label">
                  <input type="checkbox" [(ngModel)]="providers.sportpesa">
                  <span>SportPesa (Mega & Midweek)</span>
                </label>
                <label class="checkbox-label">
                  <input type="checkbox" [(ngModel)]="providers.betika">
                  <span>Betika</span>
                </label>
              </div>

              <button class="btn btn-primary" (click)="fetchJackpots()" [disabled]="fetching">
                @if (fetching) {
                  <span>⏳ Fetching...</span>
                } @else {
                  <span>📡 Fetch Jackpots</span>
                }
              </button>
            </div>
          </div>

          <!-- Warnings for sample data -->
          @if (usingTestData && fetchWarnings.length > 0) {
            <div class="card warning-card mt-3">
              <div class="card-body">
                <div class="warning-header">
                  <span class="warning-icon">⚠️</span>
                  <strong>Using Sample Data</strong>
                </div>
                <p class="warning-message">
                  The betting sites use JavaScript rendering, so live data couldn't be extracted.
                  Sample jackpot data is being used for testing purposes.
                </p>
                <ul class="warning-list">
                  @for (warning of fetchWarnings; track warning) {
                    <li>{{ warning }}</li>
                  }
                </ul>
                <div class="warning-note">
                  <strong>Note:</strong> To extract real jackpot data, you'll need to use a headless browser like Selenium
                  or manually input the jackpot matches. The predictions will still work with sample data for testing.
                </div>
              </div>
            </div>
          }

          <!-- Fetched Jackpots -->
          @if (fetchedJackpots.length > 0) {
            <div class="jackpots-grid mt-3">
              @for (jp of fetchedJackpots; track jp.provider + jp.type) {
                <div class="card jackpot-card" (click)="selectJackpot(jp)" [class.sample-data]="jp.is_sample_data">
                  @if (jp.is_sample_data) {
                    <div class="sample-badge">Test Data</div>
                  }
                  <div class="jackpot-header">
                    <div>
                      <h4 class="jackpot-provider">{{ jp.provider }}</h4>
                      <p class="jackpot-type">{{ jp.type }}</p>
                    </div>
                    @if (jp.prize_amount) {
                      <div class="prize-badge">{{ jp.prize_amount }}</div>
                    }
                  </div>
                  <div class="jackpot-stats">
                    <div class="stat">
                      <span class="stat-value">{{ jp.matches_count }}</span>
                      <span class="stat-label">Matches</span>
                    </div>
                    <div class="stat">
                      <span class="stat-value">{{ jp.matches.length }}</span>
                      <span class="stat-label">Fetched</span>
                    </div>
                  </div>
                  @if (selectedJackpot === jp) {
                    <button class="btn btn-sm btn-success mt-2" (click)="analyzeJackpot(jp); $event.stopPropagation()">
                      🤖 Analyze This
                    </button>
                  }
                </div>
              }
            </div>
          }
        </div>
      }

      <!-- Predictions Tab -->
      @if (activeTab === 'analyze') {
        <div class="analyze-section">
          @if (!currentAnalysis) {
            <div class="empty-state">
              <div class="empty-icon">🎯</div>
              <p class="empty-description">No predictions yet. Fetch and analyze a jackpot first.</p>
              <button class="btn btn-primary" (click)="activeTab = 'fetch'">
                Fetch Jackpots
              </button>
            </div>
          } @else {
            <!-- Analysis Header -->
            <div class="card mb-3">
              <div class="analysis-header">
                <div>
                  <h3>{{ currentAnalysis.provider }} - {{ currentAnalysis.type }}</h3>
                  @if (currentAnalysis.prize_amount) {
                    <p class="prize-text">💰 {{ currentAnalysis.prize_amount }}</p>
                  }
                </div>
                <div class="analysis-stats">
                  <div class="stat-box">
                    <div class="stat-value">{{ currentAnalysis.average_confidence * 100 | number:'1.1-1' }}%</div>
                    <div class="stat-label">Avg Confidence</div>
                  </div>
                  <div class="stat-box">
                    <div class="stat-value">{{ currentAnalysis.high_confidence_count }}</div>
                    <div class="stat-label">High Confidence</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Recommended Strategies -->
            <div class="card mb-3">
              <div class="card-header">
                <h3 class="card-title">💡 Recommended Strategies</h3>
              </div>
              <div class="strategies-list">
                @for (combo of currentAnalysis.recommended_combinations; track combo.strategy) {
                  <div class="strategy-item">
                    <div class="strategy-name">{{ combo.strategy }}</div>
                    <div class="strategy-desc">{{ combo.description }}</div>
                    @if (combo.predicted_accuracy) {
                      <div class="strategy-accuracy">{{ combo.predicted_accuracy * 100 | number:'1.1-1' }}% expected accuracy</div>
                    }
                  </div>
                }
              </div>
            </div>

            <!-- Match Predictions -->
            <div class="card">
              <div class="card-header">
                <h3 class="card-title">Match-by-Match Predictions</h3>
              </div>
              @if (!currentAnalysis.predictions || currentAnalysis.predictions.length === 0) {
                <div class="empty-state">
                  <div class="empty-icon">⚠️</div>
                  <p class="empty-title">No Predictions Generated</p>
                  <p class="empty-description">
                    The web scraper couldn't extract match data from the betting site.
                    This usually happens when:
                  </p>
                  <ul class="empty-list">
                    <li>The jackpot hasn't been released yet</li>
                    <li>The website HTML structure has changed</li>
                    <li>The scraper selectors need updating</li>
                  </ul>
                  <p class="empty-hint">Check the backend console for detailed error messages.</p>
                </div>
              } @else {
                <div class="predictions-list">
                  @for (pred of currentAnalysis.predictions; track pred.match_number) {
                    <div class="prediction-item" [class.high-confidence]="pred.confidence > 0.75">
                      <div class="match-info">
                        <span class="match-number">{{ pred.match_number }}</span>
                        <div class="teams">
                          <span class="team">{{ pred.home_team }}</span>
                          <span class="vs">vs</span>
                          <span class="team">{{ pred.away_team }}</span>
                        </div>
                      </div>
                      <div class="prediction-details">
                        <div class="predicted-outcome">
                          <span class="outcome-badge" [class]="'outcome-' + pred.prediction.toLowerCase()">
                            {{ pred.prediction }}
                          </span>
                          <span class="confidence-badge" [class.high]="pred.confidence > 0.75">
                            {{ pred.confidence * 100 | number:'1.0-0' }}%
                          </span>
                        </div>
                        <div class="probabilities">
                          <span class="prob">H: {{ pred.home_prob * 100 | number:'1.0-0' }}%</span>
                          <span class="prob">D: {{ pred.draw_prob * 100 | number:'1.0-0' }}%</span>
                          <span class="prob">A: {{ pred.away_prob * 100 | number:'1.0-0' }}%</span>
                        </div>
                      </div>
                    </div>
                  }
                </div>
              }
            </div>
          }
        </div>
      }

      <!-- Record Results Tab -->
      @if (activeTab === 'results') {
        <div class="results-section">
          <div class="card">
            <div class="card-header">
              <h3 class="card-title">Record Actual Results</h3>
            </div>
            <div class="card-body">
              @if (!currentAnalysis) {
                <p class="text-muted">Analyze a jackpot first to record results.</p>
              } @else {
                <p class="mb-3">Enter the actual results for {{ currentAnalysis.provider }} - {{ currentAnalysis.type }}</p>

                <div class="results-form">
                  @for (pred of currentAnalysis.predictions; track pred.match_number) {
                    <div class="result-row">
                      <span class="match-num">{{ pred.match_number }}.</span>
                      <span class="match-teams">{{ pred.home_team }} vs {{ pred.away_team }}</span>
                      <select class="result-select" [(ngModel)]="matchResults[pred.match_number]">
                        <option value="">Select result...</option>
                        <option value="Home">Home Win</option>
                        <option value="Draw">Draw</option>
                        <option value="Away">Away Win</option>
                      </select>
                      <span class="predicted">Predicted: {{ pred.prediction }}</span>
                    </div>
                  }
                </div>

                <button class="btn btn-success mt-3" (click)="submitResults()" [disabled]="!allResultsEntered()">
                  📝 Submit Results
                </button>
              }
            </div>
          </div>
        </div>
      }

      <!-- Performance Tab -->
      @if (activeTab === 'performance') {
        <div class="performance-section">
          @if (!performanceStats) {
            <div class="empty-state">
              <div class="empty-icon">📊</div>
              <p class="empty-description">No performance data yet. Record some results first.</p>
            </div>
          } @else {
            <div class="stats-grid mb-3">
              <div class="stat-card">
                <div class="stat-value">{{ performanceStats.total_jackpots }}</div>
                <div class="stat-label">Total Jackpots</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">{{ performanceStats.average_accuracy * 100 | number:'1.1-1' }}%</div>
                <div class="stat-label">Avg Accuracy</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">{{ performanceStats.best_accuracy * 100 | number:'1.1-1' }}%</div>
                <div class="stat-label">Best Performance</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">{{ performanceStats.worst_accuracy * 100 | number:'1.1-1' }}%</div>
                <div class="stat-label">Worst Performance</div>
              </div>
            </div>

            <div class="card">
              <div class="card-header">
                <h3 class="card-title">Performance by Provider</h3>
              </div>
              <div class="provider-stats">
                @for (provider of getProviderKeys(); track provider) {
                  <div class="provider-stat-item">
                    <div class="provider-name">{{ provider }}</div>
                    <div class="provider-metrics">
                      <span class="metric">{{ performanceStats.by_provider[provider].count }} jackpots</span>
                      <span class="metric">{{ performanceStats.by_provider[provider].avg_accuracy * 100 | number:'1.1-1' }}% accuracy</span>
                    </div>
                  </div>
                }
              </div>
            </div>
          }
        </div>
      }

    </div>
  `,
  styles: [`
    .tabs {
      display: flex;
      gap: 0.5rem;
      border-bottom: 2px solid var(--border);
      margin-bottom: 2rem;
    }

    .tab {
      background: none;
      border: none;
      padding: 0.75rem 1.5rem;
      color: var(--text-muted);
      cursor: pointer;
      border-bottom: 2px solid transparent;
      margin-bottom: -2px;
      transition: all 0.2s;
      font-size: 0.9rem;
      font-weight: 500;

      &:hover {
        color: var(--text);
        background: var(--bg-card-hover);
      }

      &.active {
        color: var(--primary);
        border-bottom-color: var(--primary);
      }
    }

    .provider-checkboxes {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .checkbox-label {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      cursor: pointer;

      input[type="checkbox"] {
        width: 18px;
        height: 18px;
        cursor: pointer;
      }
    }

    .jackpots-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 1rem;
    }

    .jackpot-card {
      cursor: pointer;
      transition: all 0.2s;

      &:hover {
        border-color: var(--primary);
        transform: translateY(-2px);
      }
    }

    .jackpot-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 1rem;
    }

    .jackpot-provider {
      font-size: 1.1rem;
      font-weight: 600;
      margin: 0;
      color: var(--text);
    }

    .jackpot-type {
      font-size: 0.85rem;
      color: var(--text-muted);
      margin: 0.25rem 0 0 0;
    }

    .prize-badge {
      background: linear-gradient(135deg, #f59e0b, #d97706);
      color: white;
      padding: 0.25rem 0.75rem;
      border-radius: var(--radius-sm);
      font-size: 0.75rem;
      font-weight: 600;
    }

    .sample-badge {
      position: absolute;
      top: 0.5rem;
      right: 0.5rem;
      background: #fbbf24;
      color: #78350f;
      padding: 0.25rem 0.5rem;
      border-radius: var(--radius-sm);
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .jackpot-card {
      position: relative;

      &.sample-data {
        border-color: #fbbf24;
        background: linear-gradient(to bottom, rgba(251, 191, 36, 0.05), transparent);
      }
    }

    .warning-card {
      border-left: 4px solid #fbbf24;
      background: rgba(251, 191, 36, 0.05);

      .warning-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        color: #92400e;
        margin-bottom: 0.75rem;
        font-size: 1rem;
      }

      .warning-icon {
        font-size: 1.25rem;
      }

      .warning-message {
        color: var(--text);
        margin-bottom: 0.75rem;
        line-height: 1.5;
      }

      .warning-list {
        list-style: disc;
        padding-left: 1.5rem;
        margin-bottom: 0.75rem;
        color: var(--text-muted);

        li {
          margin: 0.25rem 0;
        }
      }

      .warning-note {
        background: rgba(0, 0, 0, 0.1);
        padding: 0.75rem;
        border-radius: var(--radius-sm);
        font-size: 0.9rem;
        color: var(--text);

        strong {
          color: #92400e;
        }
      }
    }

    .jackpot-stats {
      display: flex;
      gap: 2rem;
    }

    .stat {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }

    .stat-value {
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--primary);
    }

    .stat-label {
      font-size: 0.75rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .analysis-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1.5rem;

      h3 {
        margin: 0;
        font-size: 1.25rem;
      }

      .prize-text {
        margin: 0.5rem 0 0 0;
        color: #f59e0b;
        font-weight: 600;
      }
    }

    .analysis-stats {
      display: flex;
      gap: 2rem;
    }

    .stat-box {
      text-align: center;

      .stat-value {
        font-size: 2rem;
        font-weight: 700;
        color: var(--primary);
        display: block;
      }

      .stat-label {
        font-size: 0.75rem;
        color: var(--text-muted);
        text-transform: uppercase;
      }
    }

    .strategies-list {
      padding: 1rem;
    }

    .strategy-item {
      padding: 1rem;
      background: var(--bg);
      border-radius: var(--radius-sm);
      margin-bottom: 0.75rem;

      &:last-child {
        margin-bottom: 0;
      }
    }

    .strategy-name {
      font-weight: 600;
      color: var(--primary);
      margin-bottom: 0.25rem;
    }

    .strategy-desc {
      color: var(--text-muted);
      font-size: 0.9rem;
      margin-bottom: 0.25rem;
    }

    .strategy-accuracy {
      font-size: 0.85rem;
      color: var(--success);
      font-weight: 500;
    }

    .predictions-list {
      padding: 1rem;
    }

    .prediction-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem;
      border-bottom: 1px solid var(--border);
      transition: background 0.2s;

      &:hover {
        background: var(--bg-card-hover);
      }

      &.high-confidence {
        background: rgba(16, 185, 129, 0.05);
        border-left: 3px solid var(--success);
      }

      &:last-child {
        border-bottom: none;
      }
    }

    .match-info {
      display: flex;
      align-items: center;
      gap: 1rem;
      flex: 1;
    }

    .match-number {
      background: var(--bg);
      padding: 0.25rem 0.75rem;
      border-radius: var(--radius-sm);
      font-weight: 600;
      color: var(--text-muted);
      min-width: 40px;
      text-align: center;
    }

    .teams {
      display: flex;
      align-items: center;
      gap: 0.5rem;

      .team {
        font-weight: 500;
      }

      .vs {
        color: var(--text-muted);
        font-size: 0.85rem;
      }
    }

    .prediction-details {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 0.5rem;
    }

    .predicted-outcome {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .outcome-badge {
      padding: 0.25rem 0.75rem;
      border-radius: var(--radius-sm);
      font-weight: 600;
      font-size: 0.85rem;

      &.outcome-home {
        background: rgba(59, 130, 246, 0.1);
        color: #3b82f6;
      }

      &.outcome-draw {
        background: rgba(107, 114, 128, 0.1);
        color: #6b7280;
      }

      &.outcome-away {
        background: rgba(239, 68, 68, 0.1);
        color: #ef4444;
      }
    }

    .confidence-badge {
      padding: 0.25rem 0.5rem;
      border-radius: var(--radius-sm);
      font-size: 0.75rem;
      background: var(--bg);
      color: var(--text-muted);

      &.high {
        background: rgba(16, 185, 129, 0.1);
        color: var(--success);
        font-weight: 600;
      }
    }

    .probabilities {
      display: flex;
      gap: 0.75rem;
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    .results-form {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .result-row {
      display: grid;
      grid-template-columns: 40px 2fr 1fr 1fr;
      gap: 1rem;
      align-items: center;
      padding: 0.75rem;
      background: var(--bg);
      border-radius: var(--radius-sm);
    }

    .match-num {
      font-weight: 600;
      color: var(--text-muted);
    }

    .match-teams {
      font-weight: 500;
    }

    .result-select {
      padding: 0.5rem;
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      background: var(--bg-card);
      color: var(--text);
    }

    .predicted {
      font-size: 0.85rem;
      color: var(--text-muted);
    }

    .provider-stats {
      padding: 1rem;
    }

    .provider-stat-item {
      padding: 1rem;
      background: var(--bg);
      border-radius: var(--radius-sm);
      margin-bottom: 0.75rem;
      display: flex;
      justify-content: space-between;
      align-items: center;

      &:last-child {
        margin-bottom: 0;
      }
    }

    .provider-name {
      font-weight: 600;
      font-size: 1.1rem;
    }

    .provider-metrics {
      display: flex;
      gap: 2rem;
      font-size: 0.9rem;
      color: var(--text-muted);
    }

    .metric {
      display: flex;
      align-items: center;
    }

    .empty-title {
      font-size: 1.1rem;
      font-weight: 600;
      color: var(--text);
      margin: 0.5rem 0;
    }

    .empty-list {
      text-align: left;
      margin: 1rem 0;
      padding-left: 2rem;
      color: var(--text-muted);

      li {
        margin: 0.5rem 0;
      }
    }

    .empty-hint {
      font-size: 0.9rem;
      color: var(--text-muted);
      font-style: italic;
      margin-top: 1rem;
    }
  `]
})
export class JackpotComponent implements OnInit {
  activeTab: 'fetch' | 'analyze' | 'results' | 'performance' = 'fetch';

  providers = {
    sportpesa: true,
    betika: true
  };

  fetching = false;
  fetchedJackpots: JackpotData[] = [];
  selectedJackpot: JackpotData | null = null;
  currentAnalysis: JackpotAnalysis | null = null;
  matchResults: { [key: number]: string } = {};
  performanceStats: PerformanceStats | null = null;
  fetchWarnings: string[] = [];
  usingTestData = false;

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.loadPerformanceStats();
  }

  async fetchJackpots() {
    this.fetching = true;
    this.fetchWarnings = [];
    this.usingTestData = false;
    const selectedProviders: string[] = [];

    if (this.providers.sportpesa) selectedProviders.push('sportpesa');
    if (this.providers.betika) selectedProviders.push('betika');

    try {
      const response: any = await this.api.fetchJackpots(selectedProviders).toPromise();
      this.fetchedJackpots = response.jackpots || [];

      // Check for warnings
      if (response.warnings && response.warnings.length > 0) {
        this.fetchWarnings = response.warnings;
        this.usingTestData = true;
        console.warn('Using sample data:', response.warnings);
      }

      console.log('Fetched jackpots:', this.fetchedJackpots);
      console.log('Warnings:', this.fetchWarnings);
    } catch (error) {
      console.error('Error fetching jackpots:', error);
      alert('Failed to fetch jackpots. Check console for details.');
    } finally {
      this.fetching = false;
    }
  }

  selectJackpot(jp: JackpotData) {
    this.selectedJackpot = jp;
  }

  async analyzeJackpot(jp: JackpotData) {
    try {
      console.log('Sending jackpot data for analysis:', jp);
      const response: any = await this.api.analyzeJackpot(jp).toPromise();
      console.log('Full API response:', response);
      this.currentAnalysis = response.analysis;
      console.log('Analysis complete:', this.currentAnalysis);
      console.log('Predictions count:', this.currentAnalysis?.predictions?.length);
      console.log('First prediction:', this.currentAnalysis?.predictions?.[0]);
      this.activeTab = 'analyze';

      if (!this.currentAnalysis?.predictions || this.currentAnalysis.predictions.length === 0) {
        alert('Analysis completed but no predictions were generated. This usually means the web scraper could not extract match data. Check the backend console for details.');
      }
    } catch (error) {
      console.error('Error analyzing jackpot:', error);
      alert('Failed to analyze jackpot. Check console for details.');
    }
  }

  allResultsEntered(): boolean {
    if (!this.currentAnalysis) return false;
    return this.currentAnalysis.predictions.every(
      pred => this.matchResults[pred.match_number]
    );
  }

  async submitResults() {
    if (!this.currentAnalysis || !this.allResultsEntered()) return;

    const results = this.currentAnalysis.predictions.map(pred => ({
      match_number: pred.match_number,
      actual_result: this.matchResults[pred.match_number]
    }));

    try {
      await this.api.recordJackpotResults(this.currentAnalysis.jackpot_id, results).toPromise();
      alert('Results recorded successfully!');
      this.matchResults = {};
      this.loadPerformanceStats();
      this.activeTab = 'performance';
    } catch (error) {
      console.error('Error recording results:', error);
      alert('Failed to record results. Check console for details.');
    }
  }

  async loadPerformanceStats() {
    try {
      const response: any = await this.api.getJackpotPerformance().toPromise();
      this.performanceStats = response.stats;
    } catch (error) {
      console.error('Error loading performance stats:', error);
    }
  }

  getProviderKeys(): string[] {
    return this.performanceStats ? Object.keys(this.performanceStats.by_provider) : [];
  }
}
