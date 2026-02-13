"""
Data Sources Manager
Handles configuration and management of multiple data sources
"""

import json
from pathlib import Path
from typing import Dict, List, Optional


class DataSourcesManager:
    """
    Manages data source configurations and provides easy access to:
    - Available leagues
    - Available seasons
    - Data source settings
    - URL patterns
    """

    def __init__(self, config_path: str = './config/data_sources.json'):
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load configuration from JSON file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            return json.load(f)

    def get_enabled_sources(self) -> List[Dict]:
        """Get all enabled data sources"""
        return [s for s in self.config['sources'] if s.get('enabled', False)]

    def get_source_by_id(self, source_id: str) -> Optional[Dict]:
        """Get a specific data source by ID"""
        for source in self.config['sources']:
            if source['id'] == source_id:
                return source
        return None

    def get_available_leagues(self, source_id: str = 'football-data-uk') -> List[Dict]:
        """Get available leagues for a data source"""
        source = self.get_source_by_id(source_id)
        if source and 'leagues' in source:
            return source['leagues']
        return []

    def get_available_seasons(self, source_id: str = 'football-data-uk') -> List[Dict]:
        """Get available seasons for a data source"""
        source = self.get_source_by_id(source_id)
        if source and 'seasons' in source:
            return source['seasons']
        return []

    def get_default_config(self) -> Dict:
        """Get default configuration"""
        return self.config.get('default_config', {})

    def get_url_pattern(self, source_id: str) -> Optional[str]:
        """Get URL pattern for a data source"""
        source = self.get_source_by_id(source_id)
        if source:
            return source.get('url_pattern')
        return None

    def get_column_mapping(self, source_id: str) -> Dict:
        """Get column mapping for a data source"""
        source = self.get_source_by_id(source_id)
        if source and 'column_mapping' in source:
            return source['column_mapping']
        return {}

    def get_leagues_by_country(self, country: str,
                               source_id: str = 'football-data-uk') -> List[Dict]:
        """Get leagues filtered by country"""
        leagues = self.get_available_leagues(source_id)
        return [l for l in leagues if l.get('country', '').lower() == country.lower()]

    def get_top_tier_leagues(self, source_id: str = 'football-data-uk') -> List[Dict]:
        """Get only top tier (tier 1) leagues"""
        leagues = self.get_available_leagues(source_id)
        return [l for l in leagues if l.get('tier') == 1]

    def get_recent_seasons(self, count: int = 5,
                          source_id: str = 'football-data-uk') -> List[Dict]:
        """Get the most recent N seasons"""
        seasons = self.get_available_seasons(source_id)
        return seasons[:count]

    def format_url(self, source_id: str, season: str, league: str) -> Optional[str]:
        """
        Format a URL for data fetching

        Args:
            source_id: Data source identifier
            season: Season code (e.g., '2324')
            league: League code (e.g., 'E0')

        Returns:
            Formatted URL or None
        """
        source = self.get_source_by_id(source_id)
        if not source:
            return None

        url_pattern = source.get('url_pattern')
        base_url = source.get('base_url')

        if not url_pattern or not base_url:
            return None

        return url_pattern.format(
            base_url=base_url,
            season=season,
            league=league
        )

    def get_source_metadata(self, source_id: str) -> Dict:
        """Get metadata about a data source"""
        source = self.get_source_by_id(source_id)
        if not source:
            return {}

        return {
            'id': source.get('id'),
            'name': source.get('name'),
            'description': source.get('description'),
            'type': source.get('type'),
            'enabled': source.get('enabled', False),
            'requires_api_key': source.get('requires_api_key', False),
            'sports': source.get('sports', [])
        }

    def get_all_sources_metadata(self) -> List[Dict]:
        """Get metadata for all data sources"""
        return [self.get_source_metadata(s['id']) for s in self.config['sources']]

    def save_config(self):
        """Save current configuration back to file"""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

    def enable_source(self, source_id: str):
        """Enable a data source"""
        source = self.get_source_by_id(source_id)
        if source:
            source['enabled'] = True
            self.save_config()

    def disable_source(self, source_id: str):
        """Disable a data source"""
        source = self.get_source_by_id(source_id)
        if source:
            source['enabled'] = False
            self.save_config()
