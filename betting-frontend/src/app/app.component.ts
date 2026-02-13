import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';

interface NavItem {
  path: string;
  label: string;
  icon: string;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="app-container">
      <!-- Sidebar -->
      <aside class="sidebar">
        <div class="logo">
          <h1>BetAnalytics</h1>
          <p>Sports Prediction Platform</p>
        </div>

        <nav class="nav-section">
          <span class="nav-title">Main</span>
          @for (item of mainNavItems; track item.path) {
            <a [routerLink]="item.path"
               routerLinkActive="active"
               class="nav-item">
              <span class="nav-icon">{{ item.icon }}</span>
              <span>{{ item.label }}</span>
            </a>
          }
        </nav>

        <nav class="nav-section">
          <span class="nav-title">Tools</span>
          @for (item of toolsNavItems; track item.path) {
            <a [routerLink]="item.path"
               routerLinkActive="active"
               class="nav-item">
              <span class="nav-icon">{{ item.icon }}</span>
              <span>{{ item.label }}</span>
            </a>
          }
        </nav>

        <div class="sidebar-footer">
          <div class="status-indicator">
            <span class="status-dot"></span>
            <span>Backend Connected</span>
          </div>
        </div>
      </aside>

      <!-- Main Content -->
      <main class="main-content">
        <router-outlet></router-outlet>
      </main>
    </div>
  `,
  styles: [`
    .app-container {
      display: flex;
      min-height: 100vh;
      background: var(--bg);
    }

    .sidebar {
      background: var(--bg-card);
      border-right: 1px solid var(--border);
      padding: 1.5rem 0;
      display: flex;
      flex-direction: column;
      position: fixed;
      left: 0;
      top: 0;
      width: 280px;
      height: 100vh;
      overflow-y: auto;
      z-index: 50;
    }

    .logo {
      padding: 0 1.5rem 1.5rem;
      border-bottom: 1px solid var(--border);
      margin-bottom: 1.5rem;
    }

    .logo h1 {
      font-size: 1.5rem;
      background: linear-gradient(135deg, var(--primary), var(--secondary));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      font-weight: 700;
      margin: 0;
    }

    .logo p {
      font-size: 0.75rem;
      color: var(--text-muted);
      margin-top: 0.25rem;
    }

    .nav-section {
      margin-bottom: 1.5rem;
    }

    .nav-title {
      display: block;
      padding: 0 1.5rem;
      font-size: 0.7rem;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: var(--text-muted);
      font-weight: 600;
      margin-bottom: 0.5rem;
    }

    .nav-item {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.75rem 1.5rem;
      color: var(--text-muted);
      text-decoration: none;
      transition: all 0.2s;
      border-left: 3px solid transparent;
      cursor: pointer;
    }

    .nav-item:hover {
      background: rgba(99, 102, 241, 0.1);
      color: var(--text);
    }

    .nav-item.active {
      background: rgba(99, 102, 241, 0.15);
      color: var(--primary);
      border-left-color: var(--primary);
    }

    .nav-icon {
      font-size: 1.25rem;
      width: 1.5rem;
      text-align: center;
    }

    .sidebar-footer {
      margin-top: auto;
      padding: 1rem 1.5rem;
      border-top: 1px solid var(--border);
    }

    .status-indicator {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--success);
      animation: pulse 2s infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }

    .main-content {
      flex: 1;
      margin-left: 280px;
      padding: 2rem 2.5rem;
      min-height: 100vh;
      width: calc(100% - 280px);
      box-sizing: border-box;
    }

    @media (max-width: 1024px) {
      .sidebar {
        transform: translateX(-100%);
        transition: transform 0.3s ease;
      }

      .sidebar.open {
        transform: translateX(0);
      }

      .main-content {
        margin-left: 0;
        width: 100%;
        padding: 1.5rem;
      }
    }

    @media (max-width: 640px) {
      .main-content {
        padding: 1rem;
      }
    }
  `]
})
export class AppComponent {
  mainNavItems: NavItem[] = [
    { path: '/dashboard', label: 'Dashboard', icon: '📊' },
    { path: '/predictions', label: 'Predictions', icon: '🎯' },
    { path: '/jackpot', label: 'Jackpot', icon: '🎰' },
    { path: '/backtest', label: 'Backtesting', icon: '📈' }
  ];

  toolsNavItems: NavItem[] = [
    { path: '/data', label: 'Data Collection', icon: '📥' },
    { path: '/settings', label: 'Settings', icon: '⚙️' }
  ];
}
