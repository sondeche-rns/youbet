import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { AlgorithmWeights } from '../../models/betting.models';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page-header">
      <h1 class="page-title">Settings</h1>
      <p class="page-subtitle">Configure algorithm weights and parameters</p>
    </div>

    <div class="card">
      <div class="card-header">
        <h3 class="card-title">Algorithm Weights</h3>
        <span class="total-weight" [class.valid]="isValidTotal()" [class.invalid]="!isValidTotal()">
          Total: {{ getTotalWeight() | number:'1.2-2' }}
        </span>
      </div>

      @if (loading) {
        <div class="loading-container"><div class="spinner"></div><p>Loading weights...</p></div>
      } @else {
        <div class="weights-grid">
          @for (weight of weightItems; track weight.key) {
            <div class="weight-item">
              <div class="weight-header">
                <span class="weight-label">{{ weight.label }}</span>
                <span class="weight-value">{{ (weights[weight.key] || 0) * 100 | number:'1.0-0' }}%</span>
              </div>
              <input type="range" class="weight-slider" min="0" max="0.5" step="0.01"
                     [ngModel]="weights[weight.key]" (ngModelChange)="updateWeight(weight.key, $event)">
              <p class="weight-description">{{ weight.description }}</p>
            </div>
          }
        </div>

        <div class="actions mt-3">
          <button class="btn btn-secondary" (click)="resetWeights()">Reset to Default</button>
          <button class="btn btn-primary" [disabled]="!isValidTotal() || saving" (click)="saveWeights()">
            {{ saving ? 'Saving...' : 'Save Changes' }}
          </button>
        </div>

        @if (saveMessage) {
          <div class="save-message mt-2" [class.success]="saveSuccess" [class.error]="!saveSuccess">
            {{ saveMessage }}
          </div>
        }
      }
    </div>
  `,
  styles: [`
    .total-weight { font-size: 0.875rem; padding: 0.25rem 0.75rem; border-radius: 9999px;
      &.valid { background: rgba(16, 185, 129, 0.15); color: var(--success); }
      &.invalid { background: rgba(239, 68, 68, 0.15); color: var(--danger); }
    }
    .weights-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem; }
    .weight-item { padding: 1rem; background: var(--bg); border-radius: var(--radius-sm);
      .weight-header { display: flex; justify-content: space-between; margin-bottom: 0.5rem; }
      .weight-label { font-weight: 500; font-size: 0.875rem; }
      .weight-value { font-weight: 600; color: var(--primary); }
      .weight-slider { width: 100%; accent-color: var(--primary); }
      .weight-description { font-size: 0.75rem; color: var(--text-muted); margin-top: 0.5rem; }
    }
    .actions { display: flex; justify-content: flex-end; gap: 1rem; }
    .save-message { text-align: right; font-size: 0.875rem;
      &.success { color: var(--success); }
      &.error { color: var(--danger); }
    }
  `]
})
export class SettingsComponent implements OnInit {
  weights: AlgorithmWeights = {
    expectedGoals: 0, advancedStats: 0, teamStrength: 0, tacticalMatchup: 0,
    currentForm: 0, playerImpact: 0, restAndFatigue: 0, motivation: 0,
    homeAdvantage: 0, externalFactors: 0
  };
  loading = true;
  saving = false;
  saveMessage = '';
  saveSuccess = false;

  weightItems: Array<{ key: keyof AlgorithmWeights; label: string; description: string }> = [
    { key: 'expectedGoals', label: 'Expected Goals (xG)', description: 'Weight for xG differential analysis' },
    { key: 'advancedStats', label: 'Advanced Stats', description: 'PPDA, shot quality, possession metrics' },
    { key: 'teamStrength', label: 'Team Strength', description: 'Elo ratings and relative strength' },
    { key: 'tacticalMatchup', label: 'Tactical Matchup', description: 'Formation and style compatibility' },
    { key: 'currentForm', label: 'Current Form', description: 'Recent performance patterns' },
    { key: 'playerImpact', label: 'Player Impact', description: 'Key player availability and value' },
    { key: 'restAndFatigue', label: 'Rest & Fatigue', description: 'Days since last match impact' },
    { key: 'motivation', label: 'Motivation', description: 'Title races, derbies, cup finals' },
    { key: 'homeAdvantage', label: 'Home Advantage', description: 'Venue-specific advantage' },
    { key: 'externalFactors', label: 'External Factors', description: 'Weather, travel, suspensions' }
  ];

  defaultWeights: AlgorithmWeights = {
    expectedGoals: 0.20, advancedStats: 0.15, teamStrength: 0.12, tacticalMatchup: 0.12,
    currentForm: 0.10, playerImpact: 0.10, restAndFatigue: 0.08, motivation: 0.06,
    homeAdvantage: 0.05, externalFactors: 0.02
  };

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.api.getAlgorithmWeights().subscribe({
      next: w => { this.weights = w; this.loading = false; },
      error: () => { this.weights = { ...this.defaultWeights }; this.loading = false; }
    });
  }

  updateWeight(key: keyof AlgorithmWeights, value: number) {
    this.weights[key] = value;
    this.saveMessage = '';
  }
  getTotalWeight(): number { return Object.values(this.weights).reduce((a, b) => a + b, 0); }
  isValidTotal(): boolean { return Math.abs(this.getTotalWeight() - 1.0) < 0.01; }
  resetWeights() { this.weights = { ...this.defaultWeights }; this.saveMessage = ''; }

  saveWeights() {
    this.saving = true;
    this.api.updateAlgorithmWeights(this.weights).subscribe({
      next: () => { this.saveMessage = 'Weights saved successfully!'; this.saveSuccess = true; this.saving = false; },
      error: () => { this.saveMessage = 'Failed to save weights'; this.saveSuccess = false; this.saving = false; }
    });
  }
}
