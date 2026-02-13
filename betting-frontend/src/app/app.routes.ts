import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    redirectTo: 'dashboard',
    pathMatch: 'full'
  },
  {
    path: 'dashboard',
    loadComponent: () => import('./components/dashboard/dashboard.component')
      .then(m => m.DashboardComponent)
  },
  {
    path: 'predictions',
    loadComponent: () => import('./components/predictions/predictions.component')
      .then(m => m.PredictionsComponent)
  },
  {
    path: 'jackpot',
    loadComponent: () => import('./components/jackpot/jackpot.component')
      .then(m => m.JackpotComponent)
  },
  {
    path: 'backtest',
    loadComponent: () => import('./components/backtest/backtest.component')
      .then(m => m.BacktestComponent)
  },
  {
    path: 'data',
    loadComponent: () => import('./components/data-collection/data-collection.component')
      .then(m => m.DataCollectionComponent)
  },
  {
    path: 'settings',
    loadComponent: () => import('./components/settings/settings.component')
      .then(m => m.SettingsComponent)
  },
  {
    path: '**',
    redirectTo: 'dashboard'
  }
];
