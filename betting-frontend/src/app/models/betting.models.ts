// Match and Prediction Models

export interface Match {
  id: string;
  homeTeam: string;
  awayTeam: string;
  competition: string;
  kickoff: string;
  homeOdds: number;
  drawOdds: number;
  awayOdds: number;
  prediction?: Prediction;
}

export interface Prediction {
  outcome: string;
  homeProb: number;
  drawProb: number;
  awayProb: number;
  confidence: number;
  expectedValue: number;
  recommendation: string;
  stakePercentage?: number;
  kellyStake?: number;
  factors?: PredictionFactors;
}

export interface PredictionFactors {
  expectedGoals: FactorScore;
  advancedStats: FactorScore;
  teamStrength: FactorScore;
  tacticalMatchup: FactorScore;
  currentForm: FactorScore;
  playerImpact: FactorScore;
  restAndFatigue: FactorScore;
  motivation: FactorScore;
  homeAdvantage: FactorScore;
  externalFactors: FactorScore;
}

export interface FactorScore {
  score: number;
  [key: string]: any;
}

// Dashboard Models

export interface DashboardStats {
  overallAccuracy: number;
  roi: number;
  totalPredictions: number;
  winStreak: number;
  currentBankroll: number;
  totalPnl: number;
}

export interface RecentResult {
  date: string;
  match: string;
  prediction: string;
  result: string;
  confidence: number;
  pnl: number;
  won: boolean;
}

// Backtest Models

export interface BacktestConfig {
  sport: string;
  season: string;
  initialBankroll: number;
  kellyFraction: number;
}

export interface BacktestResults {
  overall: {
    totalMatches: number;
    correctPredictions: number;
    overallAccuracy: number;
    initialBankroll: number;
    finalBankroll: number;
    totalPnl: number;
    roi: number;
    maxDrawdown: number;
    sharpeRatio: number;
  };
  betting: {
    betsPlaced: number;
    betsWon: number;
    winRate: number;
    avgStake: number;
    avgOdds: number;
  };
  accuracyByType: {
    [key: string]: {
      count: number;
      correct: number;
      accuracy: number;
    };
  };
  accuracyByConfidence: {
    [key: string]: {
      count: number;
      correct: number;
      accuracy: number;
    };
  };
  calibration: CalibrationData;
  equityCurve: number[];
  timestamp: string;
}

export interface CalibrationData {
  homeWin: { [key: string]: CalibrationBucket };
  draw: { [key: string]: CalibrationBucket };
  awayWin: { [key: string]: CalibrationBucket };
}

export interface CalibrationBucket {
  count: number;
  expected: number;
  actual: number;
  error: number;
}

// Data Collection Models

export interface DataCollectionStatus {
  running: boolean;
  progress: number;
  currentStep: string;
  totalSteps: number;
  completed: boolean;
  results?: {
    totalMatches: number;
    dateRange: string;
    totalTeams: number;
  };
  error?: string;
}

export interface HistoricalDataSummary {
  exists: boolean;
  totalMatches?: number;
  dateRange?: {
    start: string;
    end: string;
  };
  seasons?: string[];
  teams?: number;
  columns?: string[];
  sample?: any[];
}

// Configuration Models

export interface AlgorithmWeights {
  expectedGoals: number;
  advancedStats: number;
  teamStrength: number;
  tacticalMatchup: number;
  currentForm: number;
  playerImpact: number;
  restAndFatigue: number;
  motivation: number;
  homeAdvantage: number;
  externalFactors: number;
}

// Performance Models

export interface PerformanceSummary {
  accuracy: number;
  roi: number;
  profitFactor: number;
  sharpeRatio: number;
  maxDrawdown: number;
  winRate: number;
}

export interface MonthlyPerformance {
  month: string;
  accuracy: number;
  roi: number;
  profit: number;
}
