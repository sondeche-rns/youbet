import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { DataCollectionStatus, HistoricalDataSummary } from '../../models/betting.models';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-data-collection',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page-header">
      <h1 class="page-title">Data Collection</h1>
      <p class="page-subtitle">Collect and manage historical match data</p>
    </div>

    <div class="grid-2 gap-3">
      <!-- Collection Panel -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Collect New Data</h3>
        </div>
        <form (ngSubmit)="startCollection()">
          <div class="form-group">
            <label class="form-label">Sport</label>
            <select class="form-select" [(ngModel)]="sport" name="sport">
              <option value="football">Football</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Seasons</label>
            <div class="seasons-checkboxes">
              @for (s of availableSeasons; track s.value) {
                <label class="checkbox-label">
                  <input type="checkbox" [checked]="selectedSeasons.includes(s.value)"
                         (change)="toggleSeason(s.value)">
                  {{ s.label }}
                </label>
              }
            </div>
          </div>
          <button type="submit" class="btn btn-primary btn-lg" [disabled]="status?.running" style="width: 100%;">
            {{ status?.running ? 'Collecting...' : 'Start Collection' }}
          </button>
        </form>

        @if (status?.running || status?.completed) {
          <div class="progress-section mt-3">
            <div class="progress-header">
              <span>{{ status?.currentStep }}</span>
              <span>{{ status?.progress }}%</span>
            </div>
            <div class="progress">
              <div class="progress-bar" [style.width.%]="status?.progress"></div>
            </div>
            @if (status?.completed && status?.results) {
              <div class="completion-message mt-2">
                <span class="badge badge-success">Complete!</span>
                <span>{{ status?.results?.totalMatches }} matches collected</span>
              </div>
            }
          </div>
        }
      </div>

      <!-- Current Data Summary -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Current Dataset</h3>
          <button class="btn btn-sm btn-secondary" (click)="loadDataSummary()">Refresh</button>
        </div>
        @if (!dataSummary?.exists) {
          <div class="empty-state">
            <div class="empty-icon">📊</div>
            <p class="empty-description">No historical data available. Start a collection to gather data.</p>
          </div>
        } @else {
          <div class="data-summary">
            <div class="summary-grid">
              <div class="summary-item">
                <div class="summary-value">{{ dataSummary?.totalMatches }}</div>
                <div class="summary-label">Total Matches</div>
              </div>
              <div class="summary-item">
                <div class="summary-value">{{ dataSummary?.teams }}</div>
                <div class="summary-label">Teams</div>
              </div>
            </div>
            <div class="data-details">
              <div class="detail-row">
                <span>Date Range</span>
                <span>{{ dataSummary?.dateRange?.start }} - {{ dataSummary?.dateRange?.end }}</span>
              </div>
              <div class="detail-row">
                <span>Seasons</span>
                <span>{{ dataSummary?.seasons?.join(', ') }}</span>
              </div>
              <div class="detail-row">
                <span>Features</span>
                <span>{{ dataSummary?.columns?.length }} columns</span>
              </div>
            </div>
          </div>
        }
      </div>
    </div>
  `,
  styles: [`
    .seasons-checkboxes { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.5rem; }
    .checkbox-label { display: flex; align-items: center; gap: 0.5rem; font-size: 0.875rem; cursor: pointer;
      input { accent-color: var(--primary); }
    }
    .progress-section { .progress-header { display: flex; justify-content: space-between; font-size: 0.875rem; margin-bottom: 0.5rem; } }
    .completion-message { display: flex; align-items: center; gap: 0.5rem; font-size: 0.875rem; color: var(--success); }
    .summary-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-bottom: 1rem;
      .summary-item { text-align: center; padding: 1rem; background: var(--bg); border-radius: var(--radius-sm); }
      .summary-value { font-size: 2rem; font-weight: 700; color: var(--primary); }
      .summary-label { font-size: 0.75rem; color: var(--text-muted); }
    }
    .data-details { .detail-row { display: flex; justify-content: space-between; padding: 0.5rem 0; font-size: 0.875rem; border-bottom: 1px solid var(--border);
        span:first-child { color: var(--text-muted); }
      }
    }
  `]
})
export class DataCollectionComponent implements OnInit, OnDestroy {
  sport = 'football';
  selectedSeasons = ['2324', '2223', '2122'];
  availableSeasons = [
    { value: '2324', label: '2023-24' }, { value: '2223', label: '2022-23' },
    { value: '2122', label: '2021-22' }, { value: '2021', label: '2020-21' },
    { value: '1920', label: '2019-20' }
  ];
  status: DataCollectionStatus | null = null;
  dataSummary: HistoricalDataSummary | null = null;
  private pollSub?: Subscription;

  constructor(private api: ApiService) {}

  ngOnInit() { this.loadDataSummary(); this.api.getDataCollectionStatus().subscribe(s => this.status = s); }
  ngOnDestroy() { this.pollSub?.unsubscribe(); }

  toggleSeason(season: string) {
    const idx = this.selectedSeasons.indexOf(season);
    if (idx >= 0) this.selectedSeasons.splice(idx, 1);
    else this.selectedSeasons.push(season);
  }

  startCollection() {
    this.api.startDataCollection(this.sport, this.selectedSeasons).subscribe(() => {
      this.pollSub = this.api.pollDataCollectionStatus().subscribe(s => {
        this.status = s;
        if (s.completed) this.loadDataSummary();
      });
    });
  }

  loadDataSummary() { this.api.getHistoricalData().subscribe(d => this.dataSummary = d); }
}
