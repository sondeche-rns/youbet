import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError, interval, switchMap, takeWhile, tap } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

import {
  Match,
  Prediction,
  DashboardStats,
  RecentResult,
  BacktestConfig,
  BacktestResults,
  DataCollectionStatus,
  HistoricalDataSummary,
  AlgorithmWeights,
  PerformanceSummary,
  MonthlyPerformance
} from '../models/betting.models';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = '/api';

  constructor(private http: HttpClient) {}

  // ============================================================================
  // DASHBOARD ENDPOINTS
  // ============================================================================

  getDashboardStats(): Observable<DashboardStats> {
    return this.http.get<any>(`${this.baseUrl}/dashboard/stats`).pipe(
      map(response => ({
        overallAccuracy: response.overall_accuracy,
        roi: response.roi,
        totalPredictions: response.total_predictions,
        winStreak: response.win_streak,
        currentBankroll: response.current_bankroll,
        totalPnl: response.total_pnl
      })),
      catchError(this.handleError)
    );
  }

  getUpcomingMatches(): Observable<Match[]> {
    return this.http.get<any[]>(`${this.baseUrl}/dashboard/upcoming`).pipe(
      map(matches => matches.map(m => ({
        id: m.id,
        homeTeam: m.homeTeam,  // Backend sends camelCase
        awayTeam: m.awayTeam,  // Backend sends camelCase
        competition: m.competition,
        kickoff: m.kickoff,
        homeOdds: m.home_odds,
        drawOdds: m.draw_odds,
        awayOdds: m.away_odds,
        prediction: m.prediction ? {
          outcome: m.prediction.outcome,
          homeProb: m.prediction.homeProb,  // Backend sends camelCase
          drawProb: m.prediction.drawProb,  // Backend sends camelCase
          awayProb: m.prediction.awayProb,  // Backend sends camelCase
          confidence: m.prediction.confidence,
          expectedValue: m.prediction.expectedValue,  // Backend sends camelCase
          recommendation: m.prediction.recommendation
        } : undefined
      }))),
      catchError(this.handleError)
    );
  }

  getRecentResults(): Observable<RecentResult[]> {
    return this.http.get<any[]>(`${this.baseUrl}/dashboard/recent`).pipe(
      map(results => results.map(r => ({
        date: r.date,
        match: r.match,
        prediction: r.prediction,
        result: r.result,
        confidence: r.confidence,
        pnl: r.pnl,
        won: r.won
      }))),
      catchError(this.handleError)
    );
  }

  // ============================================================================
  // PREDICTION ENDPOINTS
  // ============================================================================

  predictMatch(homeTeam: string, awayTeam: string, options?: {
    homeOdds?: number;
    drawOdds?: number;
    awayOdds?: number;
    competition?: string;
  }): Observable<Prediction> {
    return this.http.post<any>(`${this.baseUrl}/predict`, {
      home_team: homeTeam,
      away_team: awayTeam,
      home_odds: options?.homeOdds,
      draw_odds: options?.drawOdds,
      away_odds: options?.awayOdds,
      competition: options?.competition || 'Premier League'
    }).pipe(
      map(response => ({
        outcome: response.recommendation?.outcome,
        homeProb: response.homeWinProb,
        drawProb: response.drawProb,
        awayProb: response.awayWinProb,
        confidence: response.confidence,
        expectedValue: response.recommendation?.expectedValue || 0,
        recommendation: response.recommendation?.recommendation,
        stakePercentage: response.recommendation?.stakePercentage,
        kellyStake: response.recommendation?.kellyStake,
        factors: response.factors
      })),
      catchError(this.handleError)
    );
  }

  // ============================================================================
  // DATA COLLECTION ENDPOINTS
  // ============================================================================

  startDataCollection(sport: string = 'football', seasons: string[] = ['2324', '2223', '2122']): Observable<any> {
    return this.http.post(`${this.baseUrl}/data/collect`, { sport, seasons }).pipe(
      catchError(this.handleError)
    );
  }

  getDataCollectionStatus(): Observable<DataCollectionStatus> {
    return this.http.get<any>(`${this.baseUrl}/data/status`).pipe(
      map(response => ({
        running: response.running,
        progress: response.progress,
        currentStep: response.current_step,
        totalSteps: response.total_steps,
        completed: response.completed,
        results: response.results,
        error: response.error
      })),
      catchError(this.handleError)
    );
  }

  pollDataCollectionStatus(): Observable<DataCollectionStatus> {
    return interval(2000).pipe(
      switchMap(() => this.getDataCollectionStatus()),
      takeWhile(status => status.running, true)
    );
  }

  getHistoricalData(): Observable<HistoricalDataSummary> {
    return this.http.get<any>(`${this.baseUrl}/data/historical`).pipe(
      map(response => ({
        exists: response.exists,
        totalMatches: response.total_matches,
        dateRange: response.date_range,
        seasons: response.seasons,
        teams: response.teams,
        columns: response.columns,
        sample: response.sample
      })),
      catchError(this.handleError)
    );
  }

  // ============================================================================
  // BACKTEST ENDPOINTS
  // ============================================================================

  runBacktest(config: BacktestConfig): Observable<BacktestResults> {
    return this.http.post<any>(`${this.baseUrl}/backtest/run`, {
      sport: config.sport,
      season: config.season,
      initial_bankroll: config.initialBankroll,
      kelly_fraction: config.kellyFraction
    }).pipe(
      map(response => this.mapBacktestResults(response.results)),
      catchError(this.handleError)
    );
  }

  getBacktestResults(): Observable<BacktestResults> {
    return this.http.get<any>(`${this.baseUrl}/backtest/results`).pipe(
      map(response => this.mapBacktestResults(response)),
      catchError(this.handleError)
    );
  }

  exportBacktestResults(): Observable<Blob> {
    return this.http.get(`${this.baseUrl}/backtest/export`, {
      responseType: 'blob'
    }).pipe(
      catchError(this.handleError)
    );
  }

  private mapBacktestResults(response: any): BacktestResults {
    return {
      overall: {
        totalMatches: response.overall?.total_matches || 0,
        correctPredictions: response.overall?.correct_predictions || 0,
        overallAccuracy: response.overall?.overall_accuracy || 0,
        initialBankroll: response.overall?.initial_bankroll || 1000,
        finalBankroll: response.overall?.final_bankroll || 0,
        totalPnl: response.overall?.total_pnl || 0,
        roi: response.overall?.roi || 0,
        maxDrawdown: response.overall?.max_drawdown || 0,
        sharpeRatio: response.overall?.sharpe_ratio || 0
      },
      betting: {
        betsPlaced: response.betting?.bets_placed || 0,
        betsWon: response.betting?.bets_won || 0,
        winRate: response.betting?.win_rate || 0,
        avgStake: response.betting?.avg_stake || 0,
        avgOdds: response.betting?.avg_odds || 0
      },
      accuracyByType: response.accuracy_by_type || {},
      accuracyByConfidence: response.accuracy_by_confidence || {},
      calibration: response.calibration || { homeWin: {}, draw: {}, awayWin: {} },
      equityCurve: response.equity_curve || [],
      timestamp: response.timestamp || new Date().toISOString()
    };
  }

  // ============================================================================
  // PERFORMANCE ENDPOINTS
  // ============================================================================

  getPerformanceSummary(): Observable<PerformanceSummary> {
    return this.http.get<any>(`${this.baseUrl}/performance/summary`).pipe(
      map(response => ({
        accuracy: response.accuracy,
        roi: response.roi,
        profitFactor: response.profit_factor,
        sharpeRatio: response.sharpe_ratio,
        maxDrawdown: response.max_drawdown,
        winRate: response.win_rate
      })),
      catchError(this.handleError)
    );
  }

  getMonthlyPerformance(): Observable<MonthlyPerformance[]> {
    return this.http.get<any[]>(`${this.baseUrl}/performance/monthly`).pipe(
      catchError(this.handleError)
    );
  }

  // ============================================================================
  // CONFIGURATION ENDPOINTS
  // ============================================================================

  getAlgorithmWeights(): Observable<AlgorithmWeights> {
    return this.http.get<AlgorithmWeights>(`${this.baseUrl}/config/weights`).pipe(
      catchError(this.handleError)
    );
  }

  updateAlgorithmWeights(weights: AlgorithmWeights): Observable<any> {
    return this.http.post(`${this.baseUrl}/config/weights`, weights).pipe(
      catchError(this.handleError)
    );
  }

  // ============================================================================
  // LIVE FIXTURES ENDPOINTS
  // ============================================================================

  getUpcomingFixtures(sport: string = 'soccer_epl', days: number = 7): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/fixtures/upcoming`, {
      params: { sport, days: days.toString() }
    }).pipe(
      catchError(this.handleError)
    );
  }

  getCurrentSeasonMatches(league: string = 'E0'): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/fixtures/current-season`, {
      params: { league }
    }).pipe(
      catchError(this.handleError)
    );
  }

  getLiveOdds(homeTeam: string, awayTeam: string, sport: string = 'soccer_epl'): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/fixtures/live-odds`, {
      home_team: homeTeam,
      away_team: awayTeam,
      sport
    }).pipe(
      catchError(this.handleError)
    );
  }

  getAvailableSports(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/fixtures/available-sports`).pipe(
      catchError(this.handleError)
    );
  }

  getApiQuota(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/fixtures/quota`).pipe(
      catchError(this.handleError)
    );
  }

  // ============================================================================
  // JACKPOT ENDPOINTS
  // ============================================================================

  fetchJackpots(providers: string[]): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/jackpots/fetch`, {
      providers
    }).pipe(
      catchError(this.handleError)
    );
  }

  analyzeJackpot(jackpotData: any): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/jackpots/analyze`, jackpotData).pipe(
      catchError(this.handleError)
    );
  }

  recordJackpotResults(jackpotId: string, results: any[]): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/jackpots/results`, {
      jackpot_id: jackpotId,
      results
    }).pipe(
      catchError(this.handleError)
    );
  }

  getJackpotHistory(provider?: string, type?: string): Observable<any> {
    let params: any = {};
    if (provider) params.provider = provider;
    if (type) params.type = type;

    return this.http.get<any>(`${this.baseUrl}/jackpots/history`, { params }).pipe(
      catchError(this.handleError)
    );
  }

  getJackpotPerformance(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/jackpots/performance`).pipe(
      catchError(this.handleError)
    );
  }

  // ============================================================================
  // ERROR HANDLING
  // ============================================================================

  private handleError(error: HttpErrorResponse): Observable<never> {
    let errorMessage = 'An unknown error occurred';

    if (error.error instanceof ErrorEvent) {
      // Client-side error
      errorMessage = `Error: ${error.error.message}`;
    } else {
      // Server-side error
      errorMessage = error.error?.error || `Server error: ${error.status}`;
    }

    console.error('API Error:', errorMessage);
    return throwError(() => new Error(errorMessage));
  }
}
