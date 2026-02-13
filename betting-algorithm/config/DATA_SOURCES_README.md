# Data Sources Configuration

This file allows you to easily configure and customize multiple data sources for the betting platform.

## Configuration File

**Location**: `config/data_sources.json`

## Structure

The configuration file contains:

### 1. **Sources Array**
A list of all available data sources with their settings.

### 2. **Default Configuration**
Default settings used across all data sources.

## Data Source Types

### Type: `csv`
Direct CSV file downloads from URLs
- Example: football-data.co.uk
- No API key required
- Simple and reliable

### Type: `api`
REST API endpoints requiring authentication
- Example: API-Football, The Odds API
- Requires API key
- Usually has rate limits

### Type: `scraper`
Web scraping (future implementation)
- Example: FBref
- No API key required
- Requires careful rate limiting

### Type: `file`
Local file imports
- Import your own CSV files
- Full control over data

## How to Add a New Data Source

### Example: Adding a new CSV source

```json
{
  "id": "my-custom-source",
  "name": "My Custom Data Source",
  "enabled": true,
  "type": "csv",
  "description": "Description of the data source",
  "base_url": "https://example.com/data",
  "url_pattern": "{base_url}/{season}/{league}.csv",
  "rate_limit_seconds": 1.0,
  "timeout_seconds": 30,
  "sports": ["football"],
  "leagues": [
    {
      "code": "LEAGUE1",
      "name": "My League",
      "country": "Country",
      "tier": 1
    }
  ],
  "seasons": [
    {
      "code": "2324",
      "label": "2023-24",
      "start_year": 2023,
      "end_year": 2024
    }
  ],
  "column_mapping": {
    "SourceHomeTeam": "home_team",
    "SourceAwayTeam": "away_team"
  }
}
```

### Example: Adding an API source

```json
{
  "id": "my-api-source",
  "name": "My API Source",
  "enabled": false,
  "type": "api",
  "description": "API-based data source",
  "base_url": "https://api.example.com",
  "requires_api_key": true,
  "api_key_env": "MY_API_KEY",
  "rate_limit": {
    "requests_per_minute": 60,
    "requests_per_day": 1000
  },
  "endpoints": {
    "matches": "/matches",
    "odds": "/odds"
  }
}
```

## Enabling/Disabling Sources

Set `"enabled": true` or `"enabled": false` for each source.

**Enabled sources** will be:
- Available in the UI
- Used for data collection
- Listed in API responses

**Disabled sources** will be:
- Hidden from the UI
- Skipped during collection
- Still visible in configuration for easy re-enabling

## League Configuration

Each league has:

```json
{
  "code": "E0",           // Short code used in URLs
  "name": "Premier League", // Display name
  "country": "England",    // Country name
  "tier": 1               // League tier (1 = top division)
}
```

### Filtering Leagues

You can filter by:
- **Country**: All leagues from a specific country
- **Tier**: Only top-tier leagues (tier 1)
- **Custom**: Create your own filters

## Season Configuration

Each season has:

```json
{
  "code": "2324",        // Short code for file/API calls
  "label": "2023-24",    // Display label
  "start_year": 2023,    // Start year
  "end_year": 2024       // End year
}
```

## Column Mapping

Maps source column names to standardized internal names:

```json
"column_mapping": {
  "HomeTeam": "home_team",    // Map "HomeTeam" to "home_team"
  "AwayTeam": "away_team",
  "FTHG": "home_goals",
  "FTAG": "away_goals"
}
```

### Required Columns

The platform requires these standardized columns:
- `home_team` - Home team name
- `away_team` - Away team name
- `home_goals` - Home team goals
- `away_goals` - Away team goals
- `Date` - Match date

### Optional Columns

- `home_odds` - Home win odds
- `draw_odds` - Draw odds
- `away_odds` - Away win odds
- `competition` - Competition/league name
- `season` - Season identifier

## Using API Keys

### Method 1: Environment Variables (Recommended)

Set in your `.env` file:
```
API_FOOTBALL_KEY=your_key_here
ODDS_API_KEY=your_key_here
```

### Method 2: Configuration File

You can also set them directly in the config (less secure):
```json
{
  "api_key": "your_key_here"
}
```

## Default Configuration

```json
"default_config": {
  "default_sport": "football",
  "default_leagues": ["E0"],           // Premier League
  "default_seasons": ["2324", "2223", "2122"],
  "enable_caching": true,
  "cache_directory": "./data/cache",
  "retry_attempts": 3,
  "retry_delay_seconds": 2
}
```

### Settings Explained

- **default_sport**: Sport to use when not specified
- **default_leagues**: Leagues to collect by default
- **default_seasons**: Seasons to collect by default
- **enable_caching**: Cache API responses
- **retry_attempts**: Number of retries on failure
- **retry_delay_seconds**: Wait time between retries

## API Usage

### Get All Data Sources
```bash
GET /api/data/sources
```

Returns all configured data sources and metadata.

### Get Available Leagues
```bash
GET /api/data/leagues?source=football-data-uk
```

Returns leagues for a specific source.

### Get Available Seasons
```bash
GET /api/data/seasons?source=football-data-uk
```

Returns seasons for a specific source.

## Python Usage

```python
from src.data_sources_manager import DataSourcesManager

manager = DataSourcesManager()

# Get all enabled sources
sources = manager.get_enabled_sources()

# Get leagues
leagues = manager.get_available_leagues('football-data-uk')

# Get top tier leagues only
top_leagues = manager.get_top_tier_leagues()

# Get recent seasons
recent = manager.get_recent_seasons(count=3)

# Format URL
url = manager.format_url('football-data-uk', '2324', 'E0')
# Returns: https://www.football-data.co.uk/mmz4281/2324/E0.csv
```

## Best Practices

### 1. **Start with Free Sources**
- Use football-data.co.uk (free, no key required)
- Add paid APIs only when needed

### 2. **Respect Rate Limits**
- Set appropriate `rate_limit_seconds`
- Don't overwhelm servers
- Use caching when possible

### 3. **Test New Sources**
- Start with `enabled: false`
- Test with one season/league first
- Enable fully once confirmed working

### 4. **Keep API Keys Secure**
- Use environment variables
- Never commit keys to git
- Add `.env` to `.gitignore`

### 5. **Document Custom Sources**
- Add clear descriptions
- Document any special requirements
- Include contact/support info

## Troubleshooting

### "Source not found"
- Check the `id` field matches exactly
- Verify source is `enabled: true`

### "No data collected"
- Verify the URL pattern is correct
- Check season/league codes are valid
- Test the URL manually in a browser

### "API key error"
- Verify env variable name matches `api_key_env`
- Check `.env` file is loaded correctly
- Ensure API key is valid

### "Rate limit exceeded"
- Increase `rate_limit_seconds`
- Reduce number of concurrent requests
- Consider upgrading API tier

## Contributing

To add support for a new data source:

1. Add configuration to `data_sources.json`
2. Update `HistoricalDataCollector` if needed
3. Test with small dataset first
4. Document in this README
5. Submit pull request

## Support

For issues or questions:
- Check the main HISTORICAL_DATA_GUIDE.md
- Review error messages in backend console
- Test URLs manually to verify format
- Check rate limits and quotas
