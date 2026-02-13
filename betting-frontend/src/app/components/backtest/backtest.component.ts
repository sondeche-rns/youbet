import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { BacktestResults } from '../../models/betting.models';

@Component({
  selector: 'app-backtest',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page-header">
      <h1 class="page-title">Backtesting Lab</h1>
      <p class="page-subtitle">Test your algorithm against historical data</p>
    </div>

    <div class="grid-2 gap-3 mb-4">
      <!-- Config Panel -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Configuration</h3>
        </div>
        <form (ngSubmit)="runBacktest()">
          <div class="form-group">
            <label class="form-label">Sport</label>
            <select class="form-select" [(ngModel)]="config.sport" name="sport">
              <option value="football">Football</option>
              <option value="basketball">Basketball</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Season</label>
            <select class="form-select" [(ngModel)]="config.season" name="season">
              <option value="All Seasons">All Seasons</option>
              <option value="2023-24">2023-24</option>
              <option value="2022-23">2022-23</option>
              <option value="2021-22">2021-22</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Initial Bankroll</label>
            <input type="number" class="form-input" [(ngModel)]="config.initialBankroll" name="bankroll">
          </div>
          <div class="form-group">
            <label class="form-label">Kelly Fraction</label>
            <select class="form-select" [(ngModel)]="config.kellyFraction" name="kelly">
              <option [value]="0.25">Quarter Kelly (0.25)</option>
              <option [value]="0.5">Half Kelly (0.5)</option>
              <option [value]="1.0">Full Kelly (1.0)</option>
            </select>
          </div>
          <button type="submit" class="btn btn-primary btn-lg" [disabled]="running" style="width: 100%;">
            {{ running ? 'Running...' : 'Run Backtest' }}
          </button>
        </form>
      </div>

      <!-- Results Summary -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Results Summary</h3>
          @if (results) {
            <button class="btn btn-sm btn-secondary" (click)="exportResults()">Export CSV</button>
          }
        </div>
        @if (!results) {
          <div class="empty-state">
            <div class="empty-icon">📈</div>
            <p class="empty-description">Run a backtest to see results</p>
          </div>
        } @else {
          <div class="results-summary">
            <div class="summary-grid">
              <div class="summary-item">
                <div class="summary-value">{{ results.overall.overallAccuracy | number:'1.1-1' }}%</div>
                <div class="summary-label">Accuracy</div>
              </div>
              <div class="summary-item">
                <div class="summary-value" [class.text-success]="results.overall.roi > 0" [class.text-danger]="results.overall.roi < 0">
                  {{ results.overall.roi | number:'1.1-1' }}%
                </div>
                <div class="summary-label">ROI</div>
              </div>
              <div class="summary-item">
                <div class="summary-value">{{ results.overall.finalBankroll | number:'1.2-2' }}</div>
                <div class="summary-label">Final Bankroll</div>
              </div>
              <div class="summary-item">
                <div class="summary-value text-danger">{{ results.overall.maxDrawdown | number:'1.1-1' }}%</div>
                <div class="summary-label">Max Drawdown</div>
              </div>
            </div>
            <div class="divider"></div>
            <div class="betting-stats">
              <div class="stat-row">
                <span>Total Matches</span><span>{{ results.overall.totalMatches }}</span>
              </div>
              <div class="stat-row">
                <span>Bets Placed</span><span>{{ results.betting.betsPlaced }}</span>
              </div>
              <div class="stat-row">
                <span>Win Rate</span><span>{{ results.betting.winRate | number:'1.1-1' }}%</span>
              </div>
              <div class="stat-row">
                <span>Sharpe Ratio</span><span>{{ results.overall.sharpeRatio | number:'1.2-2' }}</span>
              </div>
            </div>
          </div>
        }
      </div>
    </div>

    <!-- Accuracy Breakdown -->
    @if (results) {
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Accuracy by Prediction Type</h3>
        </div>
        <div class="accuracy-grid">
          @for (item of getAccuracyByType(); track item.type) {
            <div class="accuracy-card">
              <div class="acc-type">{{ item.type }}</div>
              <div class="acc-value">{{ item.accuracy | number:'1.1-1' }}%</div>
              <div class="acc-count">{{ item.correct }}/{{ item.count }} correct</div>
            </div>
          }
        </div>
      </div>
    }
  `,
  styles: [`
    .summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1rem;
      .summary-item { text-align: center; padding: 1rem; background: var(--bg); border-radius: var(--radius-sm); }
      .summary-value { font-size: 1.5rem; font-weight: 700; }
      .summary-label { font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem; }
    }
    .divider { height: 1px; background: var(--border); margin: 1rem 0; }
    .betting-stats { .stat-row { display: flex; justify-content: space-between; padding: 0.5rem 0; font-size: 0.875rem;
        span:first-child { color: var(--text-muted); }
        span:last-child { font-weight: 500; }
      }
    }
    .accuracy-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem;
      .accuracy-card { text-align: center; padding: 1.5rem; background: var(--bg); border-radius: var(--radius-sm);
        .acc-type { font-size: 0.875rem; color: var(--text-muted); margin-bottom: 0.5rem; }
        .acc-value { font-size: 2rem; font-weight: 700; color: var(--primary); }
        .acc-count { font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem; }
      }
    }
  `]
})
export class BacktestComponent implements OnInit {
  config = { sport: 'football', season: 'All Seasons', initialBankroll: 1000, kellyFraction: 0.25 };
  running = false;
  results: BacktestResults | null = null;

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.api.getBacktestResults().subscribe({ next: r => this.results = r, error: () => {} });
  }

  runBacktest() {
    this.running = true;
    this.api.runBacktest(this.config).subscribe({
      next: r => { this.results = r; this.running = false; },
      error: () => this.running = false
    });
  }

  exportResults() {
    this.api.exportBacktestResults().subscribe(blob => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = 'backtest_results.csv'; a.click();
    });
  }

  getAccuracyByType(): Array<{type: string, count: number, correct: number, accuracy: number}> {
    if (!this.results?.accuracyByType) return [];
    return Object.entries(this.results.accuracyByType).map(([type, data]) => ({ type, ...data }));
  }
}
